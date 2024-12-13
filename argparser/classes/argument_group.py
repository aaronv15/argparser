import re
from typing import Any, Generator, Sequence

from argparser.headers.definitions import IArgument, IArgumentGroup, IGroupConfig
from argparser.headers.exceptions import ArgumentError
from argparser.headers.types_c import FuncType

type _PArgTuple = tuple[IArgument[Any], *tuple[str, ...]]

__all__ = ["ArgumentGroup"]


class ArgumentGroup(IArgumentGroup):
    def __init__(
        self,
        config: IGroupConfig,
        arguments: Sequence[IArgument[Any]],
        group_parent: type,
        parent_init_args: tuple[Any, ...],
        parent_init_kwargs: dict[str, Any],
    ) -> None:
        self.__config = config
        self.__arguments = arguments
        self.__group_parent = group_parent

        self.__parent_init_args = parent_init_args
        self.__parent_init_kwargs = parent_init_kwargs

        self.__mapped_args: dict[str | int, IArgument[Any]] = {}
        self.__mapped_positions: list[IArgument[Any]] = []
        self.__resolution_list: list[_PArgTuple] = []

        self.__group_parent_instance: object | None = None

        mapped_positions: list[tuple[int, IArgument[Any]]] = []

        for arg_obj in self.__arguments:
            position, alias, names = arg_obj.named
            self.__mapped_args.update(dict.fromkeys(names, arg_obj))
            if alias:
                self.__mapped_args[alias] = arg_obj
            if position is not None:
                mapped_positions.append((position, arg_obj))

        mapped_positions.sort(key=lambda x: x[0])

        err_str = f"\nraised by:\n\t{self.__group_parent}"

        raise_on_next: bool = False
        prev_pos: int = -1

        for pos, arg_obj in mapped_positions:
            if raise_on_next:
                raise ArgumentError(
                    f"A positional argument with a variable number of inputs must be the last positional "
                    + f"argument. (Was {pos-1} of {len(mapped_positions)-1})"
                    + err_str
                )

            if prev_pos + 1 != pos:
                raise ArgumentError(
                    "Positional args must start from 0 and increment in steps of 1."
                    + err_str
                )

            _min, _max = arg_obj.consumes
            if _min != _max:
                raise_on_next = True

            self.__mapped_positions.append(arg_obj)

    def __resolution_order(self) -> Generator[_PArgTuple, None, None]:
        # (-lt 0, -ge 0)
        int_res_order: tuple[list[_PArgTuple], list[_PArgTuple]] = ([], [])
        str_res_order: list[_PArgTuple] = []

        for arg_tuple in self.__resolution_list:
            if (ro := arg_tuple[0].resolution_order) is None:
                str_res_order.append(arg_tuple)
            elif ro < 0:
                int_res_order[0].append(arg_tuple)
            else:
                int_res_order[1].append(arg_tuple)

        int_res_order[0].sort(key=lambda x: x[0].resolution_order or 0)
        int_res_order[1].sort(key=lambda x: x[0].resolution_order or 0)
        str_res_order.sort(key=lambda x: x[0].sort_key)

        for i in int_res_order[1] + str_res_order + int_res_order[0]:
            yield i

    def resolve(self) -> None:
        for arg_obj, *arg_strs in self.__resolution_order():
            assert arg_obj is not None, "Should never be none. You fucked something up"

            match arg_obj.parse_func_type:
                case FuncType.STATIC_METHOD:
                    group_parent = None
                case FuncType.CLASS_METHOD:
                    group_parent = self.__group_parent
                case FuncType.INSTANCE_METHOD:
                    if not self.__group_parent_instance:
                        self.__group_parent_instance = self.__group_parent(
                            *self.__parent_init_args, **self.__parent_init_kwargs
                        )
                    group_parent = self.__group_parent_instance

            arg_obj.parse(group_parent, arg_strs, False)

        for arg in self.__arguments:
            arg.resolve()

    def get_arg_by_name(self, name: str) -> IArgument[Any]:
        if x := self.__mapped_args.get(name, None):
            return x

        raise KeyError(
            f"No argument with key {name!r} in argument group {self.__config.name!r}"
        )

    def group_name_matches(self, name: str) -> bool:
        return self.__config.name == name

    def set_args(self, *argument_tuple: _PArgTuple) -> None:
        self.__resolution_list.extend(argument_tuple)

    @property
    def config(self) -> IGroupConfig:
        return self.__config

    @property
    def positional_args(self) -> tuple[IArgument[Any], ...]:
        return tuple(self.__mapped_positions)

    @property
    def doc(self) -> str:
        if not (doc := self.__group_parent.__doc__):
            return ""

        return re.sub(r"\\\s+\\", " ", doc)

    @property
    def ordered_arguments(self) -> list[IArgument[Any]]:
        int_res_order: tuple[list[IArgument[Any]], list[IArgument[Any]]] = ([], [])
        str_res_order: list[IArgument[Any]] = []

        for arg in self.__arguments:
            if (ro := arg.resolution_order) is None:
                str_res_order.append(arg)
            elif ro < 0:
                int_res_order[0].append(arg)
            else:
                int_res_order[1].append(arg)

        int_res_order[0].sort(key=lambda x: x.resolution_order or 0)
        int_res_order[1].sort(key=lambda x: x.resolution_order or 0)
        str_res_order.sort(key=lambda x: x.sort_key)

        return int_res_order[1] + str_res_order + int_res_order[0]
