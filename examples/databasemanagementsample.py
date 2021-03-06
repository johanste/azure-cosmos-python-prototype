import os

from azure.cosmos import CosmosClient, HTTPFailure

AUTH_URL = os.environ.get("ACCOUNT_HOST")
AUTH_KEY = os.environ.get("ACCOUNT_KEY")
TEST_DB_NAME = "johanste-testdb"


class DatabaseManagement:
    @staticmethod
    def find_database(client, id):
        print("1. Query for database")
        databases = list(
            client.list_databases(
                query=dict(
                    query="SELECT * FROM r WHERE r.id=@id",
                    parameters=[dict(name="@id", value=id)],
                )
            )
        )
        if databases:
            print(f"Database with id {id} was found")
        else:
            print(f"Database with id {id} was not found")

    @staticmethod
    def create_database(client, id):
        print("2. Create database")
        try:
            database = client.create_database(id, fail_if_exists=True)
            print(f"A database with id {id} created")
        except HTTPFailure as e:
            if e.status_code == 409:
                print(f"A database with id {id} already exists")
            else:
                raise

    @staticmethod
    def read_database(client, id):
        print("3. Get a database by id")
        database = client.get_database(id)

    @staticmethod
    def list_databases(client):
        print("4. Listing all databases on an account")
        databases = client.list_databases()
        for database in databases:
            print(database.id)

    @staticmethod
    def delete_database(client, id):
        print("5. Delete database")
        try:
            client.delete_database(id)
        except HTTPFailure as e:
            if e.status_code == 404:
                print(f"A database with id {id} does not exist")
            else:
                raise


client = CosmosClient(AUTH_URL, AUTH_KEY)
DatabaseManagement.find_database(client, TEST_DB_NAME)
DatabaseManagement.create_database(client, TEST_DB_NAME)
DatabaseManagement.read_database(client, TEST_DB_NAME)
DatabaseManagement.list_databases(client)
DatabaseManagement.delete_database(client, TEST_DB_NAME)

