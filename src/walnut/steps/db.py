import typing as t
from os.path import isfile

from walnut import Step
from walnut.errors import StepExcecutionError
from walnut.messages import Message, SequenceMessage


class DatabaseClient():
    """
    DatabaseClient defines a family of concrete database clients.
    """
    def query(self, query: str) -> list[t.Dict[str, t.Any]]:
        raise NotImplementedError("DatabaseClient is not implemented. Please use a child class.")


class DatabaseQueryStep(Step):
    """
    DatabaseQueryStep defines a family of Step to Query SQL and NoSQL databases.
    """
    def __init__(self, *, client: DatabaseClient, query: str, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.query = self.load_sql_file(query) if query.endswith(".sql") else query

    def load_sql_file(self, filename: str) -> str:
        """
        Load the SQL contained in the file and return the content as string.
        """
        sql = ""
        if not isfile(filename):
            raise StepExcecutionError(f"sql file {filename} does not exist")
        with open(filename, "r") as fp:
            sql = fp.read()
        return sql


class MySQLQueryStep(DatabaseQueryStep):
    """
    MySQLQueryStep returns all query result rows represented as dictionaries mapping column names to values.
    """

    def __init__(self, *, client: DatabaseClient, query: str, **kwargs):
        super().__init__(client=client, query=query, **kwargs)

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        return SequenceMessage(self.client.query(self.query))


class MySQLClient(DatabaseClient):
    """
    MySQLClient implements a MySQL client using PyMySql.
    """

    def __init__(self, host: str = None, user: str = None, password: str = "", database: str = None, port: int = 3306, unix_socket: str = None, **kwargs) -> None:
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
                **kwargs
            )
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

    def close(self):
        """
        close the connection
        """
        self.conn.close()
