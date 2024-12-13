import sys
from pathlib import Path

# isort: off
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.joinpath("argparser")))
# isort: on

from argparser import GroupConfig, argument, parsing, types


class Foo:
    config = GroupConfig(name="root")

    @argument(position=0)
    def string(cls, string: str) -> str:
        return string

    @argument()
    def foo(self, num: int) -> bool:
        """return if num is gt 10"""
        return num > 10

    @argument(required=True)
    def bar(self, num: int) -> bool:
        return num > 10

    @argument.flag("a", kwargs={"inc": types.mut_wrap(0)}, re_set="t")
    def arg_a(self, *, inc: types.mut_wrap[int]) -> int:
        inc.o += 1
        return inc.o

    @argument.flag("b")
    def arg_b(self) -> bool:
        return True


class Other:
    _conf = GroupConfig(usage_example="If you can't work this out, go fuck yourself")

    @argument.flag("n")
    def not_headless(self) -> bool:
        return True

    @argument("b", position=0)
    def browser_location(self, path: Path) -> Path:
        """Location of browser"""
        return path

    @argument()
    def hi(self, num: int, name: str) -> tuple[int, str]:
        return num, name


parsing.set_root_group(Foo)
parsing.add_group(Other)
parsing.resolve()

print(f"{Other.hi()=}")
print(f"{Foo.string()=}")
print(f"{Foo.bar()=}")
print(f"{Foo.foo()=}")
print(f"{Foo.arg_a()=}")
print(f"{Foo.arg_b()=}")
