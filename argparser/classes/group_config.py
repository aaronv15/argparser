import re

from ..headers.definitions import IGroupConfig
from ..headers.exceptions import ArgumentError
from ..headers.types_c import MatchArgRegex

__all__ = ["GroupConfig"]


class GroupConfig(IGroupConfig):
    def __init__(
        self,
        name: str | None = None,
        required: bool = False,
        usage_example: str | None = None,
    ) -> None:
        self.__name = self.__validate_name(name)
        self.__required = required
        self.__usage_example = usage_example

    def __validate_name(self, name: str | None) -> str | None:
        if not name:
            return None

        name = name.strip()

        if not re.match(MatchArgRegex.VALIDATE_PARSER, name):
            raise ArgumentError(
                f"Legality check ({MatchArgRegex.VALIDATE_PARSER.value}) failed for parser name {name!r}"
            )

        processed_name = name.lstrip(":")

        return f":{processed_name}"

    @property
    def required(self) -> bool:
        return self.__required

    @required.setter
    def required(self, required: bool) -> None:
        self.__required = required

    @property
    def name(self) -> str | None:
        return self.__name

    @name.setter
    def name(self, name: str) -> None:
        self.__name = self.__validate_name(name)

    @property
    def usage_example(self) -> str | None:
        return self.__usage_example
