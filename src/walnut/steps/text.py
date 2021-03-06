import re
import typing as t

from walnut import Step
from walnut.errors import StepExcecutionError
from walnut.messages import Message, SequenceMessage, ValueMessage


class TextToCaseStep(Step):
    """
    Convert a string to case.
    """

    def process(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        v = inputs.get_value()
        if isinstance(inputs, SequenceMessage):
            return SequenceMessage([self.to_case(str(s)) for s in v if isinstance(s, str)])
        if isinstance(inputs, ValueMessage) and isinstance(v, str):
            return ValueMessage(self.to_case(str(v)))
        raise StepExcecutionError(
            f"{self.__class__.__name__} is expecting a string or sequence of strings"
        )

    def to_case(self, s: str) -> str:
        raise NotImplementedError("TextToCaseStep should not be called directly")


class TextToLowerStep(TextToCaseStep):
    """
    Convert a string to lower case.
    """

    def to_case(self, s: str) -> str:
        return s.lower()


class TextToUpperStep(TextToCaseStep):
    """
    Convert a string to upper case.
    """

    def to_case(self, s: str) -> str:
        return s.upper()


class TextPatternStep(Step):
    """
    Apply a pattern function to a text or sequence of text
    """

    def __init__(self, pattern: str, fixed=False, **kwargs) -> None:
        """
        :param pattern is the pattern to look for. The default interpretation is a regular expression.
        """
        super().__init__(**kwargs)
        self.fixed = fixed
        self.pattern = pattern if self.fixed else re.compile(pattern)

    def execute(self, inputs: Message, store: t.Dict[t.Any, t.Any]) -> Message:
        v = inputs.get_value()
        # self.print("v", v)
        # self.print("p", self.pattern)
        if isinstance(inputs, ValueMessage):
            return ValueMessage(
                self.apply_value_fixed(v) if self.fixed else self.apply_value_pattern(v)
            )
        elif isinstance(inputs, SequenceMessage):
            return SequenceMessage(
                self.apply_sequence_fixed(v) if self.fixed else self.apply_sequence_pattern(v)
            )
        else:
            raise StepExcecutionError("TextStep is expecting a string or sequence of strings")

    def apply_value_fixed(self, v: t.Any) -> t.Any:
        raise NotImplementedError()

    def apply_value_pattern(self, v: t.Any) -> t.Any:
        raise NotImplementedError()

    def apply_sequence_fixed(self, v: t.Any) -> t.Any:
        raise NotImplementedError()

    def apply_sequence_pattern(self, v: t.Any) -> t.Any:
        raise NotImplementedError()


class TextSubsetStep(TextPatternStep):
    """
    Keep strings matching a pattern.
    """

    def apply_value_fixed(self, v: t.Any) -> t.Any:
        return v if isinstance(v, str) and self.pattern == v else None

    def apply_value_pattern(self, v: t.Any) -> t.Any:
        return v if isinstance(v, str) and self.pattern.search(v) else None

    def apply_sequence_fixed(self, v: t.Any) -> t.Any:
        return [s for s in v if isinstance(s, str) and s == v]

    def apply_sequence_pattern(self, v: t.Any) -> t.Any:
        return [s for s in v if isinstance(s, str) and self.pattern.search(s)]


class TextSplitStep(TextPatternStep):
    """
    Split up a string into pieces.
    """

    def apply_value_fixed(self, v: t.Any) -> t.Any:
        return str(v).split(sep=self.pattern)

    def apply_value_pattern(self, v: t.Any) -> t.Any:
        return self.pattern.split(str(v))

    def apply_sequence_fixed(self, v: t.Any) -> t.Any:
        return [str(s).split(sep=self.pattern) for s in v]

    def apply_sequence_pattern(self, v: t.Any) -> t.Any:
        return [self.pattern.split(str(s)) for s in v]


class TextJoinStep(TextPatternStep):
    """
    Join multiple strings/texts into a single string/text.
    """

    def apply_value_fixed(self, v: t.Any) -> t.Any:
        return self.apply_sequence_fixed(v)

    def apply_value_pattern(self, v: t.Any) -> t.Any:
        return self.apply_sequence_fixed(v)

    def apply_sequence_fixed(self, v: t.Any) -> t.Any:
        return self.pattern.join(v)

    def apply_sequence_pattern(self, v: t.Any) -> t.Any:
        return self.apply_sequence_fixed(v)


class TextCountStep(TextPatternStep):
    """
    Count the number of matches in a string.
    """

    def apply_value_fixed(self, v: t.Any) -> t.Any:
        return 1 if self.pattern == v else 0

    def apply_value_pattern(self, v: t.Any) -> t.Any:
        return len(self.pattern.findall(v))

    def apply_sequence_fixed(self, v: t.Any) -> t.Any:
        return [1 if s == self.pattern else 0 for s in v]

    def apply_sequence_pattern(self, v: t.Any) -> t.Any:
        return [len(self.pattern.findall(s)) for s in v]


class TextReplaceStep(TextPatternStep):
    """
    Replace matched patterns in a string.
    """

    def __init__(self, pattern: str, replacement: str, fixed=False, **kwargs) -> None:
        super().__init__(pattern, fixed=fixed, **kwargs)
        self.replacement = replacement

    def apply_value_fixed(self, v: t.Any) -> t.Any:
        return str(v).replace(self.pattern, self.replacement)

    def apply_value_pattern(self, v: t.Any) -> t.Any:
        return self.pattern.sub(self.replacement, v)

    def apply_sequence_fixed(self, v: t.Any) -> t.Any:
        return [str(s).replace(self.pattern, self.replacement) for s in v]

    def apply_sequence_pattern(self, v: t.Any) -> t.Any:
        return [self.pattern.sub(self.replacement, s) for s in v]
