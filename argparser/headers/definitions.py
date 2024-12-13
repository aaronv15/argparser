import typing

from .types_c import FuncType, callback, null

__all__ = ["IGroupConfig", "IArgument", "IArgumentGroup", "IGroupLookup"]


class IGroupConfig(typing.Protocol):
    def __init__(
        self,
        name: str | None = None,
        required: bool = False,
        usage_example: str | None = None,
    ) -> None: ...
    @property
    def required(self) -> bool: ...
    @required.setter
    def required(self, required: bool) -> None: ...
    @property
    def name(self) -> str | None: ...
    @name.setter
    def name(self, name: str) -> None: ...
    @property
    def usage_example(self) -> str | None: ...


class IArgument[T](typing.Protocol):
    def __init__(
        self,
        alias: str | None = None,
        position: int | None = None,
        names: typing.Sequence[str] | str | None = None,
        required: bool = False,
        default: T | typing.Callable[[], T] | null = null(),
        d_type: typing.Callable[[str], typing.Any] | None = None,
        constraints: list[str] | typing.Callable[[str], bool] | None = None,
        forward_kwargs: dict[str, typing.Any] | None = None,
        handle_re_def: typing.Literal["skip", "skip-config", "apply"] = "skip-config",
        resolution_order: int | None = None,
    ) -> None: ...
    def resolve(self) -> None: ...
    def parse(
        self, group_parent: typing.Any, args: list[str], from_config: bool
    ) -> None: ...
    @property
    def named(self) -> tuple[int | None, str | None, tuple[str, ...]]: ...
    @property
    def resolution_order(self) -> int | None: ...
    @property
    def sort_key(self) -> str: ...
    @property
    def is_flag(self) -> bool: ...
    @property
    def consumes(self) -> tuple[int, int | typing.Literal["+"]]: ...
    @property
    def parse_func_type(self) -> FuncType: ...

    def __get__[K](self, instance: K, owner: type[K]) -> callback[T]: ...
    def __call__[E](self, func: typing.Callable[..., E]) -> "IArgument[E]": ...

    def format(
        self, indent: int = 2, name_size: int = 40, spec_size: int = 40
    ) -> list[str]: ...


class IArgumentGroup(typing.Protocol):
    def __init__(
        self,
        config: IGroupConfig,
        arguments: list[IArgument[typing.Any]],
        group_parent: type,
        parent_init_args: tuple[typing.Any, ...],
        parent_init_kwargs: dict[str, typing.Any],
    ) -> None: ...

    def group_name_matches(self, name: str) -> bool: ...
    def get_arg_by_name(self, name: str) -> IArgument[typing.Any]: ...
    def set_args(
        self, *argument_tuple: tuple[IArgument[typing.Any], *tuple[str, ...]]
    ) -> None: ...
    def resolve(self) -> None: ...
    @property
    def positional_args(self) -> tuple[IArgument[typing.Any], ...]: ...
    @property
    def config(self) -> IGroupConfig: ...
    @property
    def ordered_arguments(self) -> list[IArgument[typing.Any]]: ...
    @property
    def doc(self) -> str: ...


class IGroupLookup(typing.Protocol):
    def __init__(self) -> None: ...
    def add_group(self, arg_group: IArgumentGroup) -> None: ...
    def get_group(self, p_name: str) -> IArgumentGroup | None: ...
    def set_root_group(self, arg_group: IArgumentGroup, prog: str | None) -> None: ...
    def get_root_group(self) -> IArgumentGroup: ...
    @property
    def prog(self) -> str: ...
    @property
    def groups(self) -> list[IArgumentGroup]: ...
