import typing as t


class Message:
    """
    Message contains that that should be transmited on a pipeline.
    It could be inputs and outputs of the different Steps.
    """
    value: t.Optional[t.Any]

    def __init__(self, value: t.Optional[t.Any] = None) -> None:
        self.value = value

    def get_value(self) -> t.Optional[t.Any]:
        return self.value


class ValueMessage(Message):
    """
    ValueMessage contains a single native value. It could be an integer, float, string or boolean.
    """
    value: t.Optional[t.Union[int, float, str, bool]]

    def __init__(self, value: t.Optional[t.Union[int, float, str, bool]] = None) -> None:
        self.value = value

    def get_value(self) -> t.Optional[t.Union[int, float, str, bool]]:
        return self.value


class SequenceMessage(Message):
    """
    SequenceMessage contains an iterable sequence like a list.
    """
    value: t.Optional[t.Sequence]

    def __init__(self, value: t.Optional[t.Sequence] = None) -> None:
        self.value = value if value else []

    def get_value(self) -> t.Sequence:
        return self.value


class MappingMessage(Message):
    """
    MappingMessage contains a key-value variable, like a dictionary.
    """
    value: t.Optional[t.Mapping[t.Any, t.Any]]

    def __init__(self, value: t.Optional[t.Mapping[t.Any, t.Any]] = None) -> None:
        self.value = value if value else {}

    def get_value(self) -> t.Mapping[t.Any, t.Any]:
        return self.value
