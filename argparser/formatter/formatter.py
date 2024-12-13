import shutil
from typing import Any

from argparser.headers.definitions import IArgument, IArgumentGroup, IGroupLookup

__all__ = ["split_by_width", "split_by_width_w_add", "print_help"]


def split_by_width(description: str, max_size: int) -> list[str]:
    if len(description) <= max_size:
        return [description]

    split_desc: list[str] = []
    edible_description = description.strip()
    while not edible_description.isspace():
        if len(edible_description) <= max_size:
            split_desc.append(edible_description)
            break

        desc_chunk = edible_description[:max_size]

        if edible_description[max_size].isspace():
            split_desc.append(desc_chunk)
            edible_description = edible_description[max_size:].strip()
            continue

        put = False
        for c, i in zip(range(len(desc_chunk) - 1, -1, -1), desc_chunk[::-1]):
            if i.isspace():
                put = True
                split_desc.append(desc_chunk[:c].strip())
                edible_description = edible_description[c + 1 :]
                break
        if not put:
            split_desc.append(desc_chunk[:-1] + "-")
            edible_description = edible_description[len(desc_chunk) - 1 :]

    return split_desc


def split_by_width_w_add(description: str, max_size: int, add: int) -> list[str]:
    split_desc = split_by_width(description=description, max_size=max_size)

    output_list: list[str] = [split_desc[0]]

    while len(split_desc) > 1:
        split_desc = split_by_width(
            description=" ".join(map(str.strip, split_desc[1:])),
            max_size=max_size - add,
        )
        output_list.append(" " * add + split_desc[0])
    return output_list


def format_group_contents(
    arg_group: IArgumentGroup, indent: int = 2, name_size: int = 40, spec_size: int = 40
) -> list[list[str]]:
    return [
        arg.format(indent=indent, name_size=name_size, spec_size=spec_size)
        for arg in arg_group.ordered_arguments
    ]


def format_groups(
    arg_group: IArgumentGroup,
    prog: str,
    is_root: bool,
    groups_details: list[tuple[str, str]],
    indent: int = 2,
    name_size: int = 40,
) -> list[str]:
    terminal_width = shutil.get_terminal_size().columns

    name_indexes = (indent, indent + name_size)
    desc_indexes = (
        name_indexes[1] + indent,
        terminal_width - indent * 2,
    )

    help_output_list: list[str] = []
    split_desc_list: list[str] = []

    generated_usage = "Usage:" + " " * indent + prog + " [OPTIONS,...]"

    if not is_root:
        generated_usage += f" {arg_group.config.name} [OPTIONS, ...]"
    elif len(groups_details) > 1:
        generated_usage += " [:GROUPNAME,...]"

    help_output_list.append(generated_usage)

    split_desc_list = split_by_width(arg_group.doc, desc_indexes[1] - desc_indexes[0])

    while split_desc_list:
        help_output_list.append(" " * (desc_indexes[0] - 1) + split_desc_list.pop(0))

    help_output_list.append("")

    if not is_root:
        help_output_list.append("Options:")
        help_output_list.append("")
        return help_output_list

    more_subparser_info = (
        " " * indent
        + f"For more information on a specific group run > '{prog} "
        + "[{0}] [-h,--help]'".format(",".join([i[0] for i in groups_details]))
    )

    help_output_list.append(f"Groups:")
    help_output_list.append(more_subparser_info)
    help_output_list.append("")
    for name, doc in groups_details:
        split_desc_list = split_by_width(doc, desc_indexes[1] - desc_indexes[0])

        help_output_list.append(f"{name:<{desc_indexes[0]-1}}" + split_desc_list.pop(0))

        while split_desc_list:
            help_output_list.append(
                " " * (desc_indexes[0] - 1) + split_desc_list.pop(0)
            )

    help_output_list.append("")
    help_output_list.append("Options:")
    help_output_list.append("")
    return help_output_list


def print_help(
    root_group: IArgumentGroup,
    current_group: IArgumentGroup,
    group_lookup: IGroupLookup,
    help_arg: IArgument[Any],
) -> None:
    # def config_func(path: Path | None = None) -> None:
    #     """Path to a config file that contains additional args.
    #     If '-c' is specified but no path is given, the directory of the script
    #     entry point will be searched for a config.txt file."""
    # help_arg = argument("h", names="help")(_help)
    # config_arg = argument(alias="c", names="config")(config_func)

    indent: int = 2

    empty_last_line: bool = False

    is_root = current_group is root_group
    if is_root:
        groups_details: list[tuple[str, str]] = [
            (i.config.name or "", i.doc) for i in group_lookup.groups
        ]
    else:
        groups_details = []

    print(
        "\n".join(
            format_groups(
                current_group,
                group_lookup.prog,
                is_root,
                groups_details,
                indent=indent,
            )
        )
    )
    for member_help_list in format_group_contents(current_group, indent=indent):
        print("\n".join(member_help_list))
        empty_last_line = not member_help_list[-1]

    print("\n" * (not empty_last_line))
    print("\n".join(help_arg.format(indent=indent)))

    if usage_example := current_group.config.usage_example:
        print("Example Usage:\n")

        usage_example = usage_example.rstrip()
        usage_example = usage_example.replace("${indent}", " " * indent)
        usage_example = usage_example.replace(
            "${root}", group_lookup.prog + " [OPTIONS,...]"
        )

        print(usage_example, end="\n\n")

    exit(0)
