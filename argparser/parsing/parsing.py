import json
import re
import typing
from pathlib import Path
from typing import Any

from .. import formatter, utils
from ..classes import ArgumentGroup, GroupConfig, GroupLookup, argument
from ..headers.definitions import IArgument, IArgumentGroup, IGroupConfig
from ..headers.exceptions import ParsingError
from ..headers.types_c import CONSTANTS, MatchArgRegex

type _ArgList = list[IArgumentGroup | IArgument[Any] | str]
type _ArgTuple = tuple[IArgument[Any] | None, *tuple[str, ...]]
type _PArgTuple = tuple[IArgument[Any], *tuple[str, ...]]

__all__ = ["resolve", "add_group", "set_root_group"]


def _matches(arg: str) -> tuple[str, MatchArgRegex] | None:
    regex_list: list[MatchArgRegex] = [
        MatchArgRegex.MATCH_PARSER,
        MatchArgRegex.MATCH_ALIAS,
        MatchArgRegex.MATCH_NAME,
        MatchArgRegex.MATCH_ALIASES,
    ]

    for regex in regex_list:
        if match := re.match(regex, arg):
            return match.group(), regex

    return None


class _GetConfArg:
    def __init__(self, current_group: IArgumentGroup, conf_arg: IArgument[Any]) -> None:
        self.__conf_arg = conf_arg
        self.__current_group = current_group

    def get_arg_by_name(self, name: str) -> IArgument[Any]:
        return self.__conf_arg

    @property
    def current_group(self) -> IArgumentGroup:
        return self.__current_group


def _partition_args(
    argv: list[str],
    help_arg: IArgument[Any],
    config_arg: IArgument[Any],
) -> _ArgList:
    group_lookup = GroupLookup()

    current_arg_group: IArgumentGroup | _GetConfArg = group_lookup.get_root_group()
    arg_list: _ArgList = [current_arg_group]

    no_args: int = len(argv)
    index: int = 0
    while index < no_args:
        arg_str = argv[index]
        arg_obj_name, match_type = _matches(arg=arg_str) or ("", None)

        if isinstance(current_arg_group, _GetConfArg):
            current_arg_group = current_arg_group.current_group

        if arg_obj_name in CONSTANTS.HELP:
            formatter.print_help(
                group_lookup.get_root_group(),
                current_arg_group,
                group_lookup,
                help_arg,
                config_arg,
            )
            exit(0)
        elif (
            arg_obj_name in CONSTANTS.CONFIG
            and current_arg_group is group_lookup.get_root_group()
        ):
            current_arg_group = _GetConfArg(current_arg_group, config_arg)

        index += 1

        if match_type is None:
            arg_list.append(arg_str)

        elif match_type == MatchArgRegex.MATCH_PARSER:
            if (arg_group := group_lookup.get_group(arg_obj_name)) is None:
                raise ParsingError(f"{arg_obj_name} not a group name")
            current_arg_group = arg_group
            arg_list.append(current_arg_group)
        elif match_type == MatchArgRegex.MATCH_ALIAS:
            arg_obj = current_arg_group.get_arg_by_name(arg_obj_name)
            arg_list.append(arg_obj)

            if arg_obj.is_flag:
                continue

            min_consumes = arg_obj.consumes[0]
            arg_list.extend(argv[index : index + min_consumes])
            index += min_consumes
        elif match_type == MatchArgRegex.MATCH_NAME:
            arg_obj = current_arg_group.get_arg_by_name(arg_obj_name)
            arg_list.append(arg_obj)

            if arg_obj.is_flag:
                continue

            if arg_obj_name != arg_str:
                arg_list.append(arg_str[len(arg_obj_name) :])
                continue

            min_consumes = arg_obj.consumes[0]
            arg_list.extend(argv[index : index + min_consumes])
            index += min_consumes
        elif match_type == MatchArgRegex.MATCH_ALIASES:
            for char in arg_obj_name[1:]:
                arg_list.append(current_arg_group.get_arg_by_name(f"-{char}"))

    return arg_list


def _parse_args(arg_list: _ArgList) -> list[IArgumentGroup]:
    arg_group_list: list[tuple[IArgumentGroup, list[_ArgTuple]]] = []

    current_arg_obj_list: list[_ArgTuple] = []
    current_arg_obj: IArgument[Any] | None = None
    arg_str: list[str] = []

    for arg in arg_list:
        if isinstance(arg, ArgumentGroup):
            current_arg_obj_list.append((current_arg_obj, *arg_str))
            current_arg_obj = None
            arg_str.clear()

            current_arg_obj_list = []
            arg_group_list.append((arg, current_arg_obj_list))
        elif isinstance(arg, argument):
            current_arg_obj_list.append((current_arg_obj, *arg_str))

            current_arg_obj = arg
            arg_str.clear()
        elif isinstance(arg, str):
            arg_str.append(arg)

    current_arg_obj_list.append((current_arg_obj, *arg_str))
    del arg_str

    for a_group_obj, arg_tup_list in arg_group_list:
        if not arg_tup_list[0][0] is None:
            continue

        arg_str_tuple = arg_tup_list.pop(0)[1:]

        if not arg_str_tuple:
            continue

        index: int = 0
        for p_arg in a_group_obj.positional_args:
            if p_arg.consumes[1] == "+":
                arg_tup_list.append((p_arg, *arg_str_tuple[index:]))
                break

            to = p_arg.consumes[1]
            arg_tup_list.append((p_arg, *arg_str_tuple[index : index + to]))
            index += to

            if index >= len(arg_str_tuple):
                break

    for a_group_obj, arg_tup_list in arg_group_list:
        a_group_obj.set_args(*typing.cast(list[_PArgTuple], arg_tup_list))

    return [i[0] for i in arg_group_list]


def _new_arg_group(
    argument_group: type,
    group_config: IGroupConfig | None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> IArgumentGroup:
    config: IGroupConfig | None = group_config
    arg_list: list[IArgument[Any]] = []

    for v in argument_group.__dict__.values():
        if isinstance(v, argument):
            arg_list.append(v)  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(v, GroupConfig):
            config = v

    if config and not config.name:
        config.name = argument_group.__name__.lower()
    elif not config:
        config = GroupConfig(
            name=argument_group.__name__.lower(),
            required=False,
        )

    return ArgumentGroup(
        config=config,
        arguments=arg_list,
        group_parent=argument_group,
        parent_init_args=args,
        parent_init_kwargs=kwargs,
    )


def add_group(
    argument_group: type,
    /,
    group_config: IGroupConfig | None = None,
    *,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
) -> None:
    arg_group = _new_arg_group(
        argument_group=argument_group,
        group_config=group_config,
        args=args,
        kwargs=kwargs or {},
    )

    GroupLookup().add_group(arg_group)


def set_root_group(
    argument_group: type,
    /,
    prog: str | None = None,
    group_config: IGroupConfig | None = None,
    *,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
) -> None:
    arg_group = _new_arg_group(
        argument_group=argument_group,
        group_config=group_config,
        args=args,
        kwargs=kwargs or {},
    )

    GroupLookup().set_root_group(arg_group, prog)


def _read_config_dict(d: dict[str, Any]) -> list[str]:
    output: list[str] = []

    for k, v in d.items():
        if isinstance(v, list):
            output.append(f"--{k}")
            output.extend(map(str, v))  # pyright: ignore[reportUnknownArgumentType]
        elif isinstance(v, dict):
            output.append(f":{k}")
            output.extend(
                _read_config_dict(v)  # pyright: ignore[reportUnknownArgumentType]
            )
        elif v is None:
            output.append(f"--{k}")
        else:
            output.extend((f"--{k}", str(v)))

    return output


def _read_config(path: Path) -> list[str]:
    with open(path, "r") as stream:
        contents = json.loads(stream.read())

    return _read_config_dict(contents)


def resolve() -> None:
    def _help() -> None:
        """Display this help message and exit"""

    help_arg = argument("-h", names="help", default=False)(_help)
    config_arg = argument(
        "-c",
        names="config",
        default=None,
        re_set="r",
        d_type=Path,
        kwargs={"config_name": "config", "config_ext": ".json"},
    )(utils.config_func)

    import sys

    arg_list = _partition_args(sys.argv[1:], help_arg, config_arg)
    a_group_list = _parse_args(arg_list)
    for i in a_group_list:
        i.resolve(False)
        i.clear()

    conf_path = config_arg.__get__(None, None.__class__)()

    if not conf_path:
        return None

    arg_list = _partition_args(_read_config(conf_path), help_arg, config_arg)
    a_group_list = _parse_args(arg_list)

    for i in a_group_list:
        i.resolve(True)
        i.clear()
