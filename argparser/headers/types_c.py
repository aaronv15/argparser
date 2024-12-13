import types
import typing
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum, unique
from typing import Any, Callable, Literal, NamedTuple

__all__ = [
    "null",
    "MatchArgRegex",
    "FuncType",
    "Parameter",
    "FuncSignature",
    "callback",
    "CONSTANTS",
]


class CONSTANTS:
    HELP = ("-h", "--help")
    CONFIG = ("-c", "--config")


class _null_meta(type):
    def __repr__(cls):
        return f"<class: {cls.__name__}>"


class null(metaclass=_null_meta):
    def __eq__(self, o: object) -> bool:
        return isinstance(o, null) or o is null

    def __repr__(self) -> str:
        return "<instance: null>"


class MatchArgRegex(StrEnum):
    VALIDATE_ALIAS = r"^-?[a-zA-Z]$"
    VALIDATE_NAME = r"^(--)?\w[\w\d-]*[\w\d]$"
    VALIDATE_PARSER = r"^:?\w[\w\d-]*[\w\d]$"

    MATCH_ALIAS = r"^-[a-zA-Z]$"
    MATCH_ALIASES = r"^-[a-zA-Z]+$"
    MATCH_NAME = r"^--\w[\w\d-]*[\w\d](?==|$)"
    MATCH_PARSER = r"^:\w[\w\d-]*[\w\d]$"


@unique
class FuncType(IntEnum):
    STATIC_METHOD = 0
    CLASS_METHOD = 1
    INSTANCE_METHOD = 2


@dataclass
class Parameter:
    annotation: Any
    default: Any
    accepts_star: bool = False
    constraints: tuple[Any] | None = field(init=False)
    caster: type | None = field(init=False)

    def __post_init__(self) -> None:
        self.constraints = None
        self.caster = None

        annotation_origin = typing.get_origin(self.annotation)

        if annotation_origin is Literal:
            self.constraints = typing.get_args(self.annotation)
        elif annotation_origin is types.UnionType:
            self.annotation = typing.get_args(self.annotation)
        else:
            self.caster = self.annotation


class FuncSignature(NamedTuple):
    min_params: int
    max_params: int | Literal["+"]
    parameters: list[Parameter]
    d_type: Callable[[str], Any] | None
    constraints: list[str] | Callable[[str], bool] | None
    func_type: FuncType


class callback[T]:
    def __init__(self, name: str, get_func: Callable[[], T | null]) -> None:
        self.__name = name
        self.__get_func = get_func

    def get(self) -> T | null:
        return self.__get_func()

    def __call__(self) -> T:
        result = self.__get_func()

        if isinstance(result, null):
            raise ValueError(f"{self.__name!r} is null")

        return result
