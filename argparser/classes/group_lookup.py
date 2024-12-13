import sys

from argparser.headers.definitions import IArgumentGroup

__all__ = ["GroupLookup"]


class GroupLookup:
    __gl: "GroupLookup | None" = None
    __initialised: bool = False

    def __new__(cls) -> "GroupLookup":
        if not GroupLookup.__gl:
            GroupLookup.__gl = super().__new__(cls)

        return GroupLookup.__gl

    def __init__(self) -> None:
        if GroupLookup.__initialised:
            return None

        GroupLookup.__initialised = True

        self.__groups: list[IArgumentGroup] = []
        self.__root_group: IArgumentGroup | None = None
        self.__prog: str

    def add_group(self, arg_group: IArgumentGroup) -> None:
        self.__groups.append(arg_group)

    def get_group(self, p_name: str) -> IArgumentGroup | None:
        for arg_group in self.__groups:
            if arg_group.group_name_matches(p_name):
                return arg_group

        return None

    def set_root_group(self, arg_group: IArgumentGroup, prog: str | None) -> None:
        self.__root_group = arg_group
        self.__prog = prog or sys.argv[0]

    def get_root_group(self) -> IArgumentGroup:
        if self.__root_group is None:
            raise NotImplementedError

        return self.__root_group

    @property
    def prog(self) -> str:
        return self.__prog

    @property
    def groups(self) -> list[IArgumentGroup]:
        return sorted(self.__groups, key=lambda x: x.config.name or "")
