import re
import shutil
import warnings
from typing import Any, Callable, Literal, Sequence

from .. import formatter, utils
from ..headers.definitions import IArgument
from ..headers.exceptions import ArgumentError, ParsingError
from ..headers.types_c import (
    FuncType,
    HandleReSet,
    MatchArgRegex,
    Parameter,
    callback,
    null,
)

__all__ = ["argument"]

type _HRD = Literal["t", "s", "r"]


class argument[T](IArgument[T]):
    @classmethod
    def flag(
        cls,
        alias: str | None = None,
        default: bool = False,
        re_set: HandleReSet = "s",
        kwargs: dict[str, Any] | None = None,
        resolution_order: int | None = None,
    ) -> "argument[bool]":
        """A helper method for creating a flag. This is just a wrapper around class the init method."""
        return argument(
            alias=alias,
            position=None,
            names=None,
            required=False,
            default=default,
            d_type=None,
            constraints=None,
            kwargs=kwargs,
            re_set=re_set,
            resolution_order=resolution_order,
        )

    def __init__(
        self,
        alias: str | None = None,
        position: int | None = None,
        names: Sequence[str] | str | None = None,
        required: bool = False,
        default: T | Callable[[], T] | null = null(),
        d_type: Callable[[str], Any] | None = None,
        constraints: list[str] | Callable[[str], bool] | None = None,
        kwargs: dict[str, Any] | None = None,
        re_set: HandleReSet = "rs",
        resolution_order: int | None = None,
    ) -> None:
        self.__names: list[str] = self.__validate_names(names)
        self.__alias: str | None = self.__validate_alias(alias)
        self.__position: int | None = position
        self.__required: bool = required
        self.__d_type: Callable[[str], Any] | None = d_type
        self.__constraints: list[str] | Callable[[str], bool] | None = constraints
        self.__kwargs: dict[str, Any] | None = kwargs
        self.__handle_re_set: tuple[_HRD, _HRD] = self.__parse_hrd(re_set)

        self.__default: T | Callable[[], T] | null = default
        self.__obj: T | null = null()

        self.__parse_function: Callable[..., T]
        self.__parse_function_type: FuncType

        self.__min_args: int
        self.__max_args: int | Literal["+"]
        self.__param_list: list[Parameter]

        self.__docstring: str | None = None
        self.__include_func_name: bool

        self.__resolved: bool = False
        self.__resolution_order: int | None = self.__parse_res_order(resolution_order)

    def __parse_hrd(self, hrd: HandleReSet) -> tuple[_HRD, _HRD]:
        match hrd:
            case "t" | "r" | "s":
                return hrd, hrd
            case _:
                return tuple(hrd)  # pyright: ignore[reportReturnType]

    def __warn_and_raise(self) -> None:
        if self.__required and self.is_flag:
            warnings.warn(
                f"{self.__names} is a flag but is required. This argument could be omitted"
            )

    def __parse_res_order(self, res_order: int | None) -> int | None:
        if res_order is None:
            return None

        return res_order if res_order < 0 else res_order + 1

    @property
    def named(self) -> tuple[int | None, str | None, tuple[str, ...]]:
        return self.__position, self.__alias, tuple(self.__names)

    def __validate_alias(self, alias: str | None) -> str | None:
        if not alias:
            return None

        alias = alias.strip()

        if not re.match(MatchArgRegex.VALIDATE_ALIAS, alias):
            raise ArgumentError(
                f"Legality check ({MatchArgRegex.VALIDATE_ALIAS.value}) failed for argument name {alias!r}"
            )

        return f"-" + alias.lstrip("-")

    def __validate_names(self, names: Sequence[str] | str | None) -> list[str]:
        self.__include_func_name = False

        if not names:
            return []

        if isinstance(names, str):
            names = [names]

        cleaned_names: list[str] = []
        for name in names:
            if name == "+":
                self.__include_func_name = True
                continue

            name = name.strip()

            if not re.match(MatchArgRegex.VALIDATE_NAME, name):
                raise ArgumentError(
                    f"Legality check ({MatchArgRegex.VALIDATE_NAME.value}) failed for argument name {name!r}"
                )

            cleaned_names.append(f"--" + name.lstrip("-"))

        return cleaned_names

    def resolve(self) -> None:
        if self.__required and not self.__resolved:
            raise ParsingError(
                f"Argument {self.__names} is required but was not specified"
            )

    def parse(self, group_parent: Any, args: list[str], from_config: bool) -> None:
        match self.__handle_re_set:
            case _ if not self.__resolved:
                pass
            case ("s", _) if not from_config:
                return None
            case (_, "s") if from_config:
                return None
            case ("r", _) if not from_config:
                raise ParsingError(f"Argument {self.__names} given multiple times")
            case (_, "r") if from_config:
                raise ParsingError(f"Argument {self.__names} given multiple times")
            case _:
                pass

        self.__obj = self.__parse_function(
            *((group_parent,) if group_parent else ()),
            *self.__validate_args(args),
            **(self.__kwargs or {}),
        )

        self.__resolved = True

    @property
    def resolution_order(self) -> int | None:
        return self.__resolution_order

    @property
    def sort_key(self) -> str:
        return self.__alias or sorted(self.__names)[0]

    @property
    def is_flag(self) -> bool:
        # I really hate that this is allowed. I feel like it should be processed like this:
        # > a = b = c = 3
        # > a == b == c -> (a == b) == c -> (3 == 3) == 3 -> True == 3 -> False
        # Why isn't this always false? I hate this. Why?
        return self.__min_args == self.__max_args == 0

    @property
    def consumes(self) -> tuple[int, int | Literal["+"]]:
        return self.__min_args, self.__max_args

    @property
    def parse_func_type(self) -> FuncType:
        return self.__parse_function_type

    def __validate_constraints(self, args: list[str]) -> None:
        failed_w_list: str = "Args {0} are not in constraints {1}"
        failed_w_func: str = "Args {0} returned False when passed to validator function"

        if isinstance(self.__constraints, list):
            is_valid: list[bool] = [arg in self.__constraints for arg in args]
            if all(is_valid):
                return None
            failed_args = [arg for valid, arg in zip(is_valid, args) if not valid]
            raise ValueError(
                failed_w_list.format(list(failed_args), self.__constraints)
            )
        elif callable(self.__constraints):
            is_valid: list[bool] = list(map(self.__constraints, args))
            if all(is_valid):
                return None
            failed_args = [arg for valid, arg in zip(is_valid, args) if not valid]
            raise ValueError(failed_w_func.format(list(failed_args)))

        num_params: int = len(self.__param_list)
        for c, arg in enumerate(args):
            param = self.__param_list[c * (c < num_params) or -1]
            if not param.constraints or arg in param.constraints:
                continue
            raise ValueError(f"Arg {arg!r} not in constraints {param.constraints}")

    def __validate_args(self, args: list[str]) -> list[Any]:
        self.__validate_constraints(args)

        num_params: int = len(self.__param_list)
        if self.__d_type:
            return list(map(self.__d_type, args))
        else:
            arg_list: list[Any] = []
            for c, arg in enumerate(args):

                param = self.__param_list[c if (c < num_params) else -1]
                if param.caster:
                    try:
                        arg_list.append(param.caster(arg))
                    except:
                        print(arg, param)
                        raise
                else:
                    arg_list.append(arg)
            return arg_list

    def __get_arg_callback(
        self,
    ) -> T | null:
        return self.__obj

    def __get__[K](self, instance: K, owner: type[K]) -> callback[T]:
        # test_obj_empty = self.__obj.obj if isinstance(self.__obj, Store) else self.__obj
        if isinstance(self.__obj, null):
            if callable(self.__default):
                self.__obj = (
                    self.__default()
                )  # pyright: ignore[reportAttributeAccessIssue]
            else:
                self.__obj = self.__default

        return callback(self.__parse_function.__name__, self.__get_arg_callback)

    def __call__[E](self, func: Callable[..., E]) -> "argument[E]":
        func_signature = utils.read_function_signature(func)
        doc = func.__doc__

        self.__parse_function_type = func_signature.func_type
        self.__min_args = func_signature.min_params
        self.__max_args = func_signature.max_params
        self.__param_list = func_signature.parameters
        self.__docstring = re.sub(r"\s{2,}", " ", doc.strip()) if doc else None

        if self.__d_type is None:
            self.__d_type = func_signature.d_type
        if self.__constraints is None:
            self.__constraints = func_signature.constraints

        if not self.__names or self.__include_func_name:

            self.__names.extend(
                self.__validate_names((func.__name__.replace("_", "-"),))
            )

        self.__parse_function = func  # pyright: ignore[reportAttributeAccessIssue]

        self.__warn_and_raise()

        return self  # pyright: ignore[reportReturnType]

    def __repr__(self) -> str:
        alias = f"alias={self.__alias!r}, " if self.__alias else ""
        names = f"named={self.__names}, " if self.__names else ""
        position = f"pos={self.__position}, " if self.__position is not None else ""
        default = f"default={self.__default}, "
        res_ord = (
            f"ord={self.__resolution_order}, "
            if self.__resolution_order is not None
            else ""
        )
        resolved = f"resolved={self.__resolved}, "
        nargs = f"nargs=({self.__min_args},{self.__max_args}), "
        obj = f"holds={self.__obj}"

        return f"{argument.__name__}({nargs}{alias}{names}{position}{res_ord}{resolved}{default}{obj})"

    def format(
        self, indent: int = 2, name_size: int = 40, spec_size: int = 40
    ) -> list[str]:
        about_fmt_width = 15

        terminal_width = shutil.get_terminal_size().columns

        name_indexes = (indent, indent + name_size)
        desc_indexes = (name_indexes[1] + indent, terminal_width - indent * 2)

        split_desc_list: list[str] = []
        help_output_list: list[str] = []

        default_str: str = ""
        const_str: str = ""
        choices_str: str = ""
        type_str: str = ""

        if self.__max_args == self.__min_args:
            nargs_str = f"{self.__max_args}"
        elif self.__max_args == "+":
            if self.__min_args == 0:
                nargs_str = "*"
            else:
                nargs_str = f"{self.__min_args}+"
        elif self.__min_args == 0 and self.__max_args == 1:
            nargs_str = "?"
        else:
            nargs_str = f"{self.__min_args}-{self.__max_args}"

        if not isinstance(self.__default, null) and not self.__required:
            if callable(self.__default):
                default_str = (
                    f" (default="
                    + (self.__default.__doc__ or f"{self.__default.__name__}()")
                    + ")"
                )
            else:
                default_str = f" (default={self.__default})"

        has_const: bool = False
        const_str = f" (const="
        for param in self.__param_list:
            if param.default == null:
                const_str += ","
                continue

            const_str += f"{param.default},"
            has_const = True
        const_str = f"{const_str[:-1]})" * has_const

        if callable(self.__constraints) and (doc := self.__constraints.__doc__):
            choices_str = f"{'constraints':<{about_fmt_width}}= " + re.sub(
                r"\s{2,}", " ", doc.strip()
            )
        elif isinstance(self.__constraints, list):
            choices_str = f"{'constraints':<{about_fmt_width}}= " + ",".join(
                self.__constraints
            )

        if self.__d_type is not None:
            type_str = f" (d_type={self.__d_type.__name__})"
        elif len(self.__param_list) > 0 and not choices_str:
            type_str = " (d_type="
            for param in self.__param_list:
                if param.caster is None:
                    type_str += f"{param.annotation},"
                else:
                    type_str += f"{param.caster.__name__},"
            type_str = type_str[:-1] + ")"

        generated_names: str = (
            " " * indent
            + (f"{self.__alias}, " if self.__alias else " " * 4)
            + ", ".join(self.__names)
        )

        generated_specs: str = (
            f"{'info':<{about_fmt_width-1}}"
            + ("*= " if self.__required else " = ")
            + f"n={nargs_str}"
            + (f",p={self.__position}" if self.__position is not None else "")
            + default_str
            + const_str
            + type_str
        )

        if len(generated_names) < name_indexes[1]:
            help_output_list.append(
                f"{generated_names:<{desc_indexes[0]-1}}" + generated_specs
            )
        else:
            help_output_list.append(generated_names)
            help_output_list.append(" " * (desc_indexes[0] - 1) + generated_specs)

        if choices_str:
            for line in formatter.split_by_width_w_add(
                choices_str, desc_indexes[1] - desc_indexes[0], about_fmt_width + 2
            ):
                help_output_list.append(" " * (desc_indexes[0] - 1) + line)

        if self.__docstring:
            split_desc_list = formatter.split_by_width_w_add(
                f"{'description':<{about_fmt_width}}= " + self.__docstring,
                desc_indexes[1] - desc_indexes[0],
                about_fmt_width + 2,
            )

        while split_desc_list:
            help_output_list.append(
                " " * (desc_indexes[0] - 1) + split_desc_list.pop(0)
            )

        if len(help_output_list) > 1:
            help_output_list.append("")

        # print(rows)
        return help_output_list
