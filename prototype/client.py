from typing import Any, Iterable, Optional, Dict, cast, Union, Tuple


from azure.cosmos.cosmos_client import CosmosClient as _CosmosClient
from azure.cosmos.errors import HTTPFailure


class UsersManagementMixin:
    def create_user(self, user):
        pass

    def get_user(self, id):
        pass

    def list_users(self):
        pass

    def delete_user(self):
        pass


class ContainersManagementMixin:
    """
    Manage (create/list/query/get/delete) containers. 
    [Design note] Currently isolated into a mixin class to make it easier to move the functionality around
                  in the object model. 
    """

    def create_container(self, id, options=None, **kwargs) -> "Container":
        """
        Keyword arguments:
        partitionKey, indexingPolicy, defaultTtl, conflictResolutionPolicy
        """
        definition = dict(id=id)
        definition.update(kwargs)
        database = cast("Database", self)
        data = database._context.CreateContainer(
            database_link=database.database_link, collection=definition
        )
        return Container(database, data["id"])

    def get_container(self, id):
        containers = self.list_containers(
            query=dict(
                query="SELECT * FROM root r WHERE r.id = @container",
                parameters=[{"name": "@container", "value": id}],
            )
        )
        try:
            return next(containers)
        except StopIteration:
            raise ValueError()

    def list_containers(self, query=None) -> "Iterable[Container]":
        database = cast("Database", self)
        yield from [
            Container(database, container["id"])
            for container in database._context.ReadContainers(
                database_link=database.database_link
            )
        ]


class Client:
    """
    CosmosDB SQL Client. This is the main entry point to the Cosmos DB object model.
    """

    def __init__(self, url, key):
        self._context = _CosmosClient(url, dict(masterKey=key))

    def create_database(self, id: "str", fail_if_exists=False) -> "Database":
        """
        Create a new database
        :param str id: Id of the database to crate.
        :param bool fail_if_exists: If set to True and a database with the given `id` 
        already exists, fail raise a `HTTPFailure`/status code 409. If a database with
        the given id exists, and `fail_if_exists` is False, return the existing database.
        """
        try:
            result = self._context.CreateDatabase(database=dict(id=id))
            return Database(self, id=result["id"])
        except HTTPFailure as e:
            if fail_if_exists and e.status_code == 409:
                raise
        return self.get_database(id)

    def get_database(self, id: "str") -> "Database":
        """
        Return the existing databse with the id `id. 
        :param str id: Id of the new database.
        """
        return Database(client=self, id=id)

    def list_databases(self) -> "Iterable[Database]":
        """
        Return an iterable of all existing databases.
        """
        yield from [
            Database(self, database["id"]) for database in self._context.ReadDatabases()
        ]

    def delete_database(self, id: "str"):
        """
        Delete the database with the given id. Raises a HTTPError if 
        the delete fails. 
        :param str id: The database to delete. 
        """
        self._context.DeleteDatabase(database_link="dbs/" + id)

    def query_databases(self, query: "str") -> "Iterable[Database]": # TODO: Query should not just be a string
        """
        List databases matching the query `query`. 
        :param str query: Cosmos DB SQL query
        """
        yield from [
            Database(self, database["id"])
            for database in self._context.QueryDatabases(query)
        ]


class Database(ContainersManagementMixin, UsersManagementMixin):
    """
    Azure Cosmos DB SQL Database
    """
    def __init__(self, client: "Client", id: "str"):
        """
        :param Client client: Client from which this database was retreived. TODO: should we hide the client? Should it just be context?
        :param str id: Id of the database
        """
        self.client = client
        self._context = client._context
        self.id = id
        self.database_link = f"/dbs/{self.id}"


class Item(dict):
    def __init__(self, container: "Container", data: "Dict[str, Any]"):
        self.container = container # TODO: Item instances (locally) probably shouldn't be directly tied to a collection
        self._context = container._context
        self.update(data)


class Container:
    def __init__(self, database: "Database", id: "str"):
        self.database = database
        self._context = database._context
        self.id = id
        self.collection_link = f"{database.database_link}/colls/{self.id}"

    def set_container_properties(
        self,
        *,
        id=None,
        partition_key=None,
        indexing_policy=None,
        default_ttl=None,
        conflict_resolution_policy=None,
    ):
        """
        Update the properties of the container. Change will be persisted immediately. TODO: Should this be on the Database class?
        """
        parameters = {
            key: value
            for key, value in {
                "id": id or self.id,
                "partitionKey": partition_key,
                "indexingPolicy": indexing_policy,
                "defaultTtl": int(default_ttl),
                "conflictResolutionPolicy": conflict_resolution_policy,
            }.items()
            if value
            != None  # TODO: Questionable use - should use kwargs instead. Need to figure out best documentation for kwargs...
        }
        result = self._context.ReplaceContainer(
            self.collection_link, collection=parameters
        )

    @staticmethod
    def _document_link(item_or_link) -> "str":
        if type(item_or_link) is "str":
            return item_or_link
        else:
            return cast("str", cast("Item", item_or_link)["_self"])

    def get_item(self, id: "str", cls=Item) -> "Item":
        doc_link = f"{self.collection_link}/docs/{id}"
        result = self._context.ReadItem(document_link=doc_link)
        return cls(container=self, data=result)

    def list_items(self, options=None, cls=Item) -> "Iterable[Item]":
        options = options or {}
        items = self._context.ReadItems(
            collection_link=self.collection_link, feed_options=options
        )
        yield from [cls(self, item) for item in items]

    def query_items(self, query: "str", cls=Item):
        items = self._context.QueryItems(
            database_or_Container_link=self.collection_link, query=query
        )
        yield from [cls(self, item) for item in items]

    def replace_item(self, item: "Union[Item, str]", body: "Dict[str, Any]") -> "Item":
        item_link = Container._document_link(item)
        data = self._context.ReplaceItem(document_link=item_link, new_document=body)
        return Item(self, data)

    def upsert_item(self, body: "Dict[str, Any]") -> "Item":
        result = self._context.UpsertItem(
            database_or_Container_link=self.collection_link, document=body
        )
        return Item(self, result)

    def create_item(self, body: "Dict[str,str]") -> "Item":
        result = self._context.CreateItem(
            database_or_Container_link=self.collection_link, document=body
        )
        return Item(self, result)

    def delete_item(self, item: "Item"):
        document_link = Container._document_link(item)
        self._context.DeleteItem(document_link=document_link)
