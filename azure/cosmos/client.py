"""
Cosmos client Pythonidae
"""
from typing import Any, Iterable, Optional, Dict, Union, Tuple, cast, overload


from azure.internal_cosmos.cosmos_client import CosmosClient as _CosmosClient
from azure.internal_cosmos.errors import HTTPFailure


class ClientContext(_CosmosClient):
    pass

class User:
    pass

class StoredProceduresMixin:
    def list_stored_procedures(self, query):
        pass

    def get_stored_procedure(self, id):
        pass

    def create_stored_procedure(self):
        pass

    def upsert_stored_procedure(self, trigger):
        pass

    def delete_stored_procedure(self):
        pass


class TriggersMixin:
    def list_triggers(self, query):
        pass

    def get_trigger(self, id):
        pass

    def create_trigger(self):
        pass

    def upsert_trigger(self, trigger):
        pass

    def delete_trigger(self):
        pass


class UserDefinedFunctionsMixin:
    def list_user_defined_functions(self, query):
        pass

    def get_user_defined_function(self, id):
        pass

    def create_user_defined_function(self):
        pass

    def upsert_user_defined_function(self, trigger):
        pass

    def delete_user_defined_function(self):
        pass


class Client:
    """
    CosmosDB SQL Client. This is the main entry point to the Cosmos DB object model.

    >>> import os
    >>> ACCOUNT_KEY = os.environ['ACCOUNT_KEY']
    >>> ACCOUNT_HOST = os.environ['ACCOUNT_HOST']
    >>> client = Client(url=ACCOUNT_HOST, key=ACCOUNT_KEY)
    ...
    """

    def __init__(self, url, key):
        self.client_context = ClientContext(url, dict(masterKey=key))

    def create_database(self, id: "str", fail_if_exists=False) -> "Database":
        """ Create a new database with the given name (id)

        :param id: Id (name) of the database to create.
        :param bool fail_if_exists: Fail if database already exists.
        :raises azure.cosmos.errors.HTTPFailure: If `fail_if_exists` is set to True and a database with the given id already exists

        :Example: Creating a new database

        >>> import os
        >>> ACCOUNT_KEY = os.environ['ACCOUNT_KEY']
        >>> ACCOUNT_HOST = os.environ['ACCOUNT_HOST']
        >>> client = Client(url=ACCOUNT_HOST, key=ACCOUNT_KEY)
        >>> database = client.create_database('nameofdatabase')        
        ...

        """
        try:
            result = self.client_context.CreateDatabase(database=dict(id=id))
            return DatabaseResponse(
                self.client_context, id=result["id"], properties=result
            )
        except HTTPFailure as e:
            if fail_if_exists and e.status_code == 409:
                raise
        return self.get_database(id)

    def get_database(self, id: "str") -> "Database":
        """
        Retreive the existing database with the id (name) `id`. 

        :param id: Id of the new database.
        :raise HTTPError: If the given database couldn't be retrieved.
        """
        properties = self.client_context.ReadDatabase(database_link=f"dbs/{id}")
        database = DatabaseResponse(self.client_context, id, properties)
        return database

    def get_database_properties(self, id: "str"):
        """ Get the database properties 

        :param id: Id (or name) of the database to retrieve properties for.
        """
        properties = self.client_context.ReadDatabase(id)
        return properties

    def list_databases(self, query: "Optional[str]" = None) -> "Iterable[Database]":
        """
        Return all databases matching the query, or all databases if query is not provided

        :param query: Cosmos DB SQL query. If omitted, all databases will be listed.
        """
        if query:
            yield from [
                DatabaseResponse(self.client_context, properties["id"], properties)
                for properties in self.client_context.QueryDatabases(query)
            ]
        else:
            yield from [
                DatabaseResponse(self.client_context, properties["id"], properties)
                for properties in self.client_context.ReadDatabases()
            ]

    def delete_database(self, id: "str"):
        """
        Delete the database with the given id.

        :param id: The id (name) of the database to delete. 
        :raise azure.cosmos.HTTPError: If the call to delete the database fails.
        """
        self.client_context.DeleteDatabase(database_link=f"dbs/{id}")


class Database:
    """
    Azure Cosmos DB SQL Database
    """

    def __init__(self, client_context: "ClientContext", id: "str"):
        """
        :param ClientSession client_context: Client from which this database was retreived.
        :param str id: Id of the database
        """
        self.client_context = client_context
        self.id = id
        self.database_link = f"/dbs/{self.id}"

    def create_container(self, id, options=None, **kwargs) -> "ContainerResponse":
        """
        Create a new container with the given id (name). If a container with the given
        id (name) already exists, an HTTPError will be raised.

        :param str id: Id of container to create
        :raise HTTPError:

        Keyword arguments:
        partitionKey, indexingPolicy, defaultTtl, conflictResolutionPolicy
        """
        definition = dict(id=id)
        definition.update(kwargs)
        data = self.client_context.CreateContainer(
            database_link=self.database_link, collection=definition, options=options
        )
        return ContainerResponse(self.client_context, self, data["id"], properties=data)

    @overload
    def delete_container(self, container: "str"):
        ...

    @overload
    def delete_container(self, container: "Container"):
        ...

    def delete_container(self, container):
        """ Delete the container

        :param container: The container to delete. 
        """
        collection_link = getattr(
            container, "collection_link", f"{self.database_link}/colls/{container}"
        )
        properties = self.client_context.DeleteContainer(collection_link)

    def get_container(
        self, container_or_id: "Union[str, Container]"
    ) -> "ContainerResponse":
        collection_link = getattr(
            container_or_id,
            "collection_link",
            f"{self.database_link}/colls/{container_or_id}",
        )
        container = self.client_context.ReadContainer(collection_link)
        return ContainerResponse(
            self.client_context, self, container["id"], properties=container
        )

    def list_containers(self, query=None) -> "Iterable[ContainerResponse]":
        if query:
            yield from [
                ContainerResponse(self.client_context, self, container["id"], container)
                for container in self.client_context.ReadContainers(
                    database_link=self.database_link
                )
            ]
        else:
            yield from [
                ContainerResponse(self.client_context, self, container["id"], container)
                for container in self.client_context.ReadContainers(
                    database_link=self.database_link
                )
            ]

    def set_container_properties(
        self,
        container: "Union[str, Container]",
        *,
        partition_key=None,
        indexing_policy=None,
        default_ttl=None,
        conflict_resolution_policy=None,
    ):
        """
        Update the properties of the container. Change will be persisted immediately.
        """
        container_id = getattr(container, "id", container)
        parameters = {
            key: value
            for key, value in {
                "id": container_id,
                "partitionKey": partition_key,
                "indexingPolicy": indexing_policy,
                "defaultTtl": int(default_ttl),
                "conflictResolutionPolicy": conflict_resolution_policy,
            }.items()
            if value
            is not None  # TODO: Questionable use - should use kwargs instead. Need to figure out best documentation for kwargs...
        }
        collection_link = f"{self.database_link}/colls/{container_id}"
        self.client_context.ReplaceContainer(collection_link, collection=parameters)

    def get_container_properties(self, container) -> "Dict[str, Any]":
        """
        Get properties for of container. TODO: implement properly
        """
        collection_link = getattr(
            container, "collection_link", f"{self.database_link}/cols/{container}"
        )
        properties = self.client_context.ReadContainer(collection_link)
        return properties

    def get_user_link(self, id_or_user: "Union[User, str]") -> "str":
        user_link = getattr(id_or_user, 'user_link', f'{self.database_link}/users/{id_or_user}')
        return user_link

    def create_user(self, user, options=None):
        database = cast("Database", self)
        return database.client_context.CreateUser(database.database_link, user, options)

    def get_user(self, id):
        database = cast("Database", self)
        return database.client_context.ReadUser(self.get_user_link(id))

    def list_users(self, query=None):
        database = cast("Database", self)
        yield from [
            User(user)
            for user in database.client_context.ReadUsers(query)
        ]

    def delete_user(self, user):
        database = cast("Database", self)
        database.client_context.DeleteUser(self.get_user_link(id))


class DatabaseResponse(Database):
    def __init__(
        self, client_context: "ClientContext", id: "str", properties: "Dict[str, Any]"
    ):
        super().__init__(client_context, id)
        self.properties = properties


class Item(dict):
    def __init__(self, headers: "Dict[str, Any]", data: "Dict[str, Any]"):
        super().__init__()
        self.response_headers = headers
        self.update(data)


class Container(UserDefinedFunctionsMixin, TriggersMixin, StoredProceduresMixin):
    def __init__(
        self,
        client_context: "ClientContext",
        database: "Union[Database, str]",
        id: "str",
    ):
        self.client_context = client_context
        self.session_token = None
        self.id = id
        database_link = getattr(database, "database_link", f"dbs/{database}")
        self.collection_link = f"{database_link}/colls/{self.id}"

    @staticmethod
    def _document_link(item_or_link) -> "str":
        if isinstance(item_or_link, str):
            return item_or_link
        return cast("str", cast("Item", item_or_link)["_self"])

    def get_item(self, id: "str") -> "Item":
        """
        Get the item identified by `id`
        :param str id: Id of item to retreive
        :param callable metadata_handler: Optional method that will, if provided, receive an instance
        of `CosmosCallMetadata` representing metadata about the operation (RSU cost etc.)
        :returns: Item if present.
        """
        doc_link = f"{self.collection_link}/docs/{id}"
        result = self.client_context.ReadItem(document_link=doc_link)
        headers = self.client_context.last_response_headers
        self.session_token = headers.get("x-ms-session-token", self.session_token)
        return Item(headers=headers, data=result)

    def list_items(self, options=None) -> "Iterable[Item]":
        options = options or {}
        items = self.client_context.ReadItems(
            collection_link=self.collection_link, feed_options=options
        )
        headers = self.client_context.last_response_headers
        yield from [Item(headers=headers, data=item) for item in items]

    def query_items(
        self, query: "str", options=None, partition_key: "Optional[str]" = None
    ) -> "Iterable[Item]":
        items = self.client_context.QueryItems(
            database_or_Container_link=self.collection_link,
            query=query,
            options=options,
            partition_key=partition_key,
        )
        headers = self.client_context.last_response_headers
        yield from [Item(headers, item) for item in items]

    def replace_item(self, item: "Union[Item, str]", body: "Dict[str, Any]") -> "Item":
        item_link = Container._document_link(item)
        data = self.client_context.ReplaceItem(
            document_link=item_link, new_document=body
        )
        return Item(headers=self.client_context.last_response_headers, data=data)

    def upsert_item(self, body: "Dict[str, Any]") -> "Item":
        result = self.client_context.UpsertItem(
            database_or_Container_link=self.collection_link, document=body
        )
        return Item(headers=self.client_context.last_response_headers, data=result)

    def create_item(self, body: "Dict[str, Any]") -> "Item":
        result = self.client_context.CreateItem(
            database_or_Container_link=self.collection_link, document=body
        )
        return Item(headers=self.client_context.last_response_headers, data=result)

    def delete_item(self, item: "Item") -> "None":
        document_link = Container._document_link(item)
        self.client_context.DeleteItem(document_link=document_link)


class ContainerResponse(Container):
    def __init__(
        self,
        client_context: "ClientContext",
        database: "Union[Database, str]",
        id: "str",
        properties: "Dict[str, Any]",
    ):
        super().__init__(client_context, database, id)
        self.properties = properties