from __future__ import annotations

import typing as t

from walnut.errors import StepExcecutionError


class Resource:
    """
    Resouce identifies a connectable external resource for the Recipe.
    All steps can access and use it, for example, sql, ftp, etc.
    """

    def __init__(self, **kwargs) -> None:
        pass


class Resources:
    """
    Resources is a central place to store and retrieve resources that can be used across Steps.
    E.g: Database Connections
    """

    resources: t.Dict[t.Text, Resource] = {}

    def __getitem__(self, name: str):
        """
        Lookup/Retrieve a resource given its name and raise StepExcecutionError if not found
        """
        if name not in self.resources:
            raise StepExcecutionError(
                f"Resource '{name}' not defined in Recipe. "
                "Please add it to the Recipe().bake(resources={...})."
                f"Available resources: {','.join(self.resources.keys())}"
            )
        return self.resources[name]

    def __setitem__(self, name: str, resource: Resource):
        """
        Insert a key/value pair into the storage.
        """
        if name in self.resources:
            raise StepExcecutionError(
                f"Resource '{name}' already exist in the defined resources."
                "Please choose a different name."
                f"Available resources: {','.join(self.resources.keys())}"
            )
        self.resources[name] = resource

    def __contains__(self, name: str):
        """
        Test for membership.
        """
        return name in self.resources

    def __delitem__(self, name: str):
        """
        Remove an resource from the list.
        """
        del self.resources[name]


class EmptyResource(Resource):
    """
    A Resource that just do nothing.
    """

    pass


class DatabaseResource(Resource):
    """
    DatabaseResource defines a family of concrete database resources.
    """

    resource_type = "db"
    resource_name = "<undefined>"
    conn_string = "<undefined>"
    conn = None

    def query(self, query: str) -> list[t.Dict[str, t.Any]]:
        """
        query will return rows represented as dictionaries mapping column names to values.
        """
        raise NotImplementedError("DatabaseClient is not implemented. Please use a child class.")

    def close(self) -> None:
        """
        close the connection
        """
        if self.conn:
            self.conn.close()

    def __str__(self) -> str:
        return f"{self.__class__.__name__} {self.resource_type}:{self.resource_name}:{self.conn_string}"


class MySQLResource(DatabaseResource):
    """
    MySQLResource implements a MySQL client using PyMySql.
    """

    resource_name = "mysql"

    def __init__(
        self,
        host: str = None,
        user: str = None,
        password: str = "",
        database: str = None,
        port: int = 3306,
        unix_socket: str = None,
        **kwargs,
    ):
        """
        Establish a connection to the MySQL database. Accepts several arguments:

        :param host: Host where the database server is located
        :param user: Username to log in as
        :param password: Password to use.
        :param database: Database to use, None to not use a particular one.
        :param port: MySQL port to use, default is usually OK. (default: 3306)
        :param unix_socket: Optionally, you can use a unix socket rather than TCP/IP.
        :param read_timeout: The timeout for reading from the connection in seconds (default: None - no timeout)
        :param write_timeout: The timeout for writing to the connection in seconds (default: None - no timeout)
        :param charset: Charset you want to use.
        :param sql_mode: Default SQL_MODE to use.
        :param connect_timeout: Timeout before throwing an exception when connecting. (default: 10, min: 1, max: 31536000)
        """
        try:
            from pymysql import connect, cursors

            self.conn = connect(
                host=host,
                user=user,
                password=password,
                database=database,
                unix_socket=unix_socket,
                cursorclass=cursors.DictCursor,
                **kwargs,
            )
            self.conn_string = f"{host}:{port}/{database}"
        except ImportError:
            raise StepExcecutionError("mysql client is required: pip install PyMySql")
        except Exception as err:
            raise StepExcecutionError(f"mysql client error: {err}")

    def query(self, query: str) -> list[t.Dict[str, t.Any]]:
        """
        query will return rows represented as dictionaries mapping column names to values.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()


class PostgreSQLResource(DatabaseResource):
    """
    PostgreSQLResource implements a PostgreSQL client using Psycopg2.
    """

    resource_name = "postgresql"

    def __init__(
        self,
        host: str = None,
        user: str = None,
        password: str = "",
        database: str = None,
        port: int = 5432,
        unix_socket: str = None,
        **kwargs,
    ) -> None:
        """
        Establish a connection to a PostgreSQL database. Accepts several arguments:

        :param host: Host where the database server is located
        :param user: Username to log in as
        :param password: Password to use.
        :param database: Database to use, None to not use a particular one.
        :param port: PostgreSQL port to use, default is usually OK. (default: 5432)
        :param unix_socket: Optionally, you can use a unix socket rather than TCP/IP.
        """
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            self.conn = psycopg2.connect(
                host=host if host else unix_socket,
                port=port,
                dbname=database,
                user=user,
                password=password,
                cursor_factory=RealDictCursor,
            )
            self.conn_string = f"{host or unix_socket}:{port}/{database}"
        except ImportError:
            raise StepExcecutionError("postgresql client is required: pip install psycopg2")
        except Exception as err:
            raise StepExcecutionError(f"postgresql client error: {err}")

    def query(self, query: str) -> list[t.Dict[str, t.Any]]:
        """
        query will return rows represented as dictionaries mapping column names to values.
        """
        with self.conn.cursor() as cursor:
            try:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            except Exception as err:
                if "no results to fetch" in str(err):
                    return []
                raise err


class ResourceFactory:
    """
    ResourceFactory creates all the available Resources
    """

    RESOURCES: t.Mapping[str, t.Type[Resource]] = {
        "postgresql": PostgreSQLResource,
        "mysql": MySQLResource,
    }

    @staticmethod
    def create(engine: str, **kwargs) -> Resource:
        cls = ResourceFactory.RESOURCES.get(engine, EmptyResource)
        return cls(**kwargs)
