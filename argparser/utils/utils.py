import inspect
from pathlib import Path
from typing import Any, Callable

from argparser.headers.types_c import FuncSignature, FuncType, Parameter, null

__all__ = ["read_function_signature", "config_func"]


def config_func(path: Path | None = None) -> Path | None:
    """Path to a config file that contains additional args.
    If '-c' is specified but no path is given, the directory of the script
    entry point will be searched for a config.yaml file."""

    if path is None:
        import sys

        if (p := Path(sys.argv[0]).parent.joinpath("config.yaml")).exists():
            return p
        raise FileNotFoundError(f"File {p} not found")
    return path.resolve(strict=True)


def read_function_signature(func: Callable[..., Any]) -> FuncSignature:
    min_params: int = 0
    max_params: int = 0
    param_data: list[Parameter] = []

    func_type: FuncType
    function_parameters = list(inspect.signature(func).parameters.values())

    if not function_parameters:
        func_type = FuncType.STATIC_METHOD
    elif function_parameters[0].name == "self":
        func_type = FuncType.INSTANCE_METHOD
    elif function_parameters[0].name == "cls":
        func_type = FuncType.CLASS_METHOD
    else:
        func_type = FuncType.STATIC_METHOD

    accepts_star: bool = False
    for param in function_parameters[func_type != FuncType.STATIC_METHOD :]:
        if param.kind == param.VAR_KEYWORD or param.kind == param.KEYWORD_ONLY:
            continue

        accepts_star = param.kind == param.VAR_POSITIONAL
        no_default = param.default == param.empty

        min_params += no_default * (not accepts_star)
        max_params += 1

        param_data.append(
            Parameter(
                annotation=param.annotation,
                default=null if no_default else param.default,
                accepts_star=accepts_star,
            )
        )

        if accepts_star:
            break

    d_type: Callable[[str], Any] | None = None
    constraints: list[str] | Callable[[str], bool] | None = None
    for param in function_parameters:
        if not param.kind == param.KEYWORD_ONLY or param.default == param.empty:
            continue

        if param.name == "d_type":
            d_type = param.default
        elif param.name == "constraints":
            constraints = param.default

    func_sig = FuncSignature(
        min_params=min_params,
        max_params="+" if accepts_star else max_params,
        parameters=param_data,
        d_type=d_type,
        constraints=constraints,
        func_type=func_type,
    )

    return func_sig
