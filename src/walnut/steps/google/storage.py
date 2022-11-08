import typing as t

from walnut.errors import StepExcecutionError, StepValidationError
from walnut.messages import MappingMessage, Message, SequenceMessage, ValueMessage
from walnut.steps.core import Step


class StorageStep(Step):
    """
    Google Cloud Storage is a durable and highly available object storage service.
    Google Cloud Storage is almost infinitely scalable and guarantees consistency:
    when a write succeeds, the latest copy of the object will be returned to any GET, globally.
    """

    templated: t.Sequence[str] = tuple({"bucket_name", "project"} | set(Step.templated))
    project: t.Optional[str]
    bucket_name: t.Optional[str]

    def __init__(self, bucket_name: str = None, project: str = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.project = project
        self.bucket_name = bucket_name

        if self.bucket_name is None or self.bucket_name.strip() == "":
            raise StepValidationError("The bucket_name parameter is requried on all GCS Steps")
        if self.project is None or self.project.strip() == "":
            raise StepValidationError("The project parameter is requried on all GCS Steps")

        try:
            from google.cloud import storage

            self.client = storage.Client(project=project)
        except ImportError as err:
            raise StepValidationError(
                f"Missing dependency. Plese execute pip install google-cloud-storage: {err}"
            )
        except Exception as err:
            raise StepExcecutionError(f"Critical error on GCS StorageStep: {err}")

    def process(self, inputs: Message) -> Message:
        raise NotImplementedError("Please do not use StorageStep. Use a child class instead.")


class BucketListBlobsStep(StorageStep):
    """
    BucketListBlobsStep returns a list containing the blobs in the bucket. E.g:
    [{
        "name": "x/y/z/1.log",
        "creation": "2022-04-14 14:02:03.522000+00:00"
    }]
    """

    templated: t.Sequence[str] = tuple({"prefix", "delimiter"} | set(StorageStep.templated))

    def __init__(self, prefix: str = None, delimiter: str = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.prefix = prefix
        self.delimiter = delimiter

    def process(self, inputs: Message) -> SequenceMessage:
        b = self.client.bucket(self.bucket_name)
        if not b.exists():
            raise StepExcecutionError(f"gcs bucket '{self.bucket_name}' not found")
        return SequenceMessage(
            [
                {"name": blb.name, "creation": blb.time_created}
                for blb in list(
                    self.client.list_blobs(b, prefix=self.prefix, delimiter=self.delimiter)
                )
            ]
        )


class ReadBlobsStep(StorageStep):
    """
    A file-like object that reads from a blob from a GCS bucket.
    The input of the step is should be a valid filename in the bucket.
    If you need to read a list of files, concatenate with ForEachStep.
    ```
    ReadBlobsStep(project="my-project", bucket_name="my-bucket")
    ```
    """

    def process(self, inputs: Message) -> Message:
        if isinstance(inputs, (SequenceMessage, MappingMessage)):
            raise StepValidationError(
                "Mapping or Sequence Messages are not supported. "
                f"We are expecting a single file to read. Got: {inputs}"
            )
        blob = inputs.get_value()
        if not isinstance(blob, str) or len(blob.strip()) == 0:
            raise StepValidationError("The GCS filename on the inputs is empty")

        b = self.client.bucket(self.bucket_name).blob(blob)
        if not b.exists():
            raise StepExcecutionError(
                f"Blob '{self.project}/{self.bucket_name}/{blob}' does not exist"
            )
        try:
            content = b.download_as_text()
        except Exception as err:
            raise StepExcecutionError(
                f"Critical error reading the blob '{self.project}/{self.bucket_name}/{blob}': {err}"
            )
        return ValueMessage(content)
