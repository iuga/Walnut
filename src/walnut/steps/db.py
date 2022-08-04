import typing as t
from os.path import isfile

from walnut import Step
from walnut.errors import StepExcecutionError
from walnut.messages import Message, SequenceMessage
from walnut.resources import DatabaseResource


class DatabaseQueryStep(Step):
    """
    DatabaseQueryStep defines a family of Step to Query SQL and NoSQL databases.
    """

    def __init__(self, *, query: str, resource: str, **kwargs):
        super().__init__(**kwargs)
        self.resource = resource
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

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        client = self.get_resource(self.resource)
        if not isinstance(client, DatabaseResource):
            raise StepExcecutionError(
                f"resource '{self.resource}' should be of type DatabaseClient and not {client.__class__.__name__}"
            )
        print(self.query)
        return SequenceMessage(client.query(self.query))
