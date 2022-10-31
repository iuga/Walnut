import typing as t

from walnut.errors import StepExcecutionError
from walnut.messages import Message, SequenceMessage
from walnut.steps.core import Step


class StorageStep(Step):
    """
    Google Cloud Storage is a durable and highly available object storage service.
    Google Cloud Storage is almost infinitely scalable and guarantees consistency:
    when a write succeeds, the latest copy of the object will be returned to any GET, globally.
    """

    templated: t.Sequence[str] = tuple({"project_id"} | set(Step.templated))

    def __init__(self, project_id: str = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.project_id = project_id
        try:
            from google.cloud import storage

            self.client = storage.Client()
        except ImportError as err:
            raise StepExcecutionError(
                f"Missing dependency. Plese execute pip install google-cloud-storage: {err}"
            )

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

    templated: t.Sequence[str] = tuple(
        {"bucket_name", "prefix", "delimiter"} | set(StorageStep.templated)
    )

    def __init__(
        self, bucket_name: str, prefix: str = None, delimiter: str = None, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.bucket_name = bucket_name
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
