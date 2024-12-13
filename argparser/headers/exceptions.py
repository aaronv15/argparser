__all__ = ["ArgParserError", "ArgumentError", "ParsingError"]


class ArgParserError(Exception): ...


class ArgumentError(ArgParserError): ...


class ParsingError(ArgParserError): ...
