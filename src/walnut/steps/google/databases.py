import typing as t

from walnut.errors import StepExcecutionError
from walnut.resources import DatabaseResource, ResourceFactory


class BigQueryResource(DatabaseResource):
    """
    BigQueryResource implements a BigQuery client using Google Cloud BigQuery client.
    """

    resource_name = "bigquery"

    def __init__(
        self,
        project: str = None,
        location: str = None,
        credentials: t.Any = None,
        client_options: t.Any = None,
        job_retry: int = 30,
        timeout: float = 30,
        **kwargs,
    ):
        """
        Establish a connection to the BigQuery database. Accepts several arguments:

        :param project: Project ID for the project which the client acts on behalf of.
            Will be passed when creating a dataset / job. If not passed,
            falls back to the default inferred from the environment.
        :param credentials: The OAuth2 Credentials to use for this client.
        :param location: Default location for jobs / datasets / tables.
        :param client_options: Client options used to set user options on the client.
            API Endpoint should be set through client_options.
        :param job_retry: number of seconds to retry failed jobs.
        :param timeout: The number of seconds to wait for the underlying HTTP transport before using ``retry``.
        """
        try:
            from google.cloud import bigquery

            self.retry = bigquery.DEFAULT_RETRY.with_deadline(job_retry)
            self.timeout = timeout
            self.client = bigquery.Client(
                project=project,
                location=location,
                credentials=credentials,
                client_options=client_options,
            )
            self.conn_string = f"{project}"
        except ImportError:
            raise StepExcecutionError(
                "bigquery client is required: pip install google-cloud-bigquery"
            )
        except Exception as err:
            raise StepExcecutionError(f"bigquery client error: {err}")

    def query(self, query: str) -> list[t.Dict[str, t.Any]]:
        """
        query will return rows represented as dictionaries mapping column names to values.
        """
        job = self.client.query(query, job_retry=self.retry, timeout=self.timeout)
        r = []
        for row in job.result():
            r.append({k: v for k, v in row.items()})
        return r


class SpannerResource(DatabaseResource):
    """
    SpannerResource implements a Cloud Spanner client using Google Cloud Spanner client.
    """

    resource_name = "spanner"
    timeout = 10

    def __init__(
        self,
        project: str = None,
        instance: str = None,
        database: str = None,
        location: str = None,
        credentials: t.Any = None,
        client_options: t.Any = None,
        job_retry: int = 30,
        timeout: float = 30,
        **kwargs,
    ):
        """
        Establish a connection to the spanner database. Accepts several arguments:

        :param project: Project ID for the project which the client acts on behalf of.
            Will be passed when creating a dataset / job. If not passed,
            falls back to the default inferred from the environment.
        :param instance: Spanner instance name.
        :param database: Spanner database name.
        :param credentials: The OAuth2 Credentials to use for this client.
        :param location: Default location for jobs / datasets / tables.
        :param client_options: Client options used to set user options on the client.
            API Endpoint should be set through client_options.
        :param job_retry: number of seconds to retry failed jobs.
        :param timeout: The number of seconds to wait for the underlying HTTP transport before using ``retry``.
        """
        try:
            from google.cloud import spanner

            if project is None or instance is None or database is None:
                raise StepExcecutionError("project, instance and database are required")

            self.conn_string = f"{project}"
            self.timeout = timeout
            spanner_client = spanner.Client(project=project)
            instance = spanner_client.instance(instance)
            self.client = instance.database(database)
        except ImportError:
            raise StepExcecutionError(
                "spanner client is required: pip install google-cloud-spanner"
            )
        except Exception as err:
            raise StepExcecutionError(f"spanner client error: {err}")

    def query(self, query: str) -> list[t.Dict[str, t.Any]]:
        """
        query will return rows represented as dictionaries mapping column names to values.
        """
        r = []
        with self.client.snapshot() as snapshot:
            results = snapshot.execute_sql(query, timeout=self.timeout)
            if not results:
                return r
            rows = []
            for row in results:
                rows.append(row)
            columns = [column.name for column in results.fields]
            for row in rows:
                r.append(dict(zip(columns, row)))
        return r


# TODO: Refactor this section. We should discover all plugins from the Recipe.Resources
ResourceFactory.register(SpannerResource)
ResourceFactory.register(BigQueryResource)
