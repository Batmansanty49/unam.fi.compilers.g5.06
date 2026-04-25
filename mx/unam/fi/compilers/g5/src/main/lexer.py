from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


KEYWORDS = {
    "auto",
    "break",
    "case",
    "char",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "float",
    "for",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "print",
    "printf",
    "register",
    "restrict",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while",
    "_Alignas",
    "_Alignof",
    "_Atomic",
    "_Bool",
    "_Complex",
    "_Generic",
    "_Noreturn",
    "_Static_assert",
    "_Thread_local",
}

OPERATORS = sorted(
    [
        "<<=",
        ">>=",
        "<<",
        ">>",
        "<=",
        ">=",
        "==",
        "!=",
        "&&",
        "||",
        "++",
        "--",
        "+=",
        "-=",
        "*=",
        "/=",
        "%=",
        "&=",
        "|=",
        "^=",
        "->",
        "=",
        "+",
        "-",
        "*",
        "/",
        "%",
        "<",
        ">",
        "!",
        "~",
        "&",
        "|",
        "^",
        "?",
        ":",
    ],
    key=len,
    reverse=True,
)

PUNCTUATION = [",", ";", "(", ")", "{", "}", "[", "]", "."]

OP_PATTERN = "|".join(re.escape(operator) for operator in OPERATORS)
PUNCT_PATTERN = "|".join(re.escape(symbol) for symbol in PUNCTUATION)


@dataclass(frozen=True)
class Token:
    kind: str
    lexeme: str
    line: int
    column: int

    @property
    def parser_terminal(self) -> str:
        if self.kind == "KEYWORD" and self.lexeme in {"int", "float", "char", "double"}:
            return self.lexeme
        if self.kind == "IDENTIFIER":
            return "identifier"
        if self.kind == "CONSTANT":
            return "constant"
        if self.kind in {"OPERATOR", "PUNCTUATION"} and self.lexeme in {
            "=",
            ";",
            "+",
            "-",
            "*",
            "/",
            "(",
            ")",
        }:
            return self.lexeme
        if self.kind == "EOF":
            return "$"
        raise ValueError(
            f"Token {self.lexeme!r} ({self.kind}) is not part of the parser grammar."
        )


TOKEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("COMMENT", re.compile(r"^(//[^\n]*|/\*[\s\S]*?\*/)")),
    ("WS", re.compile(r"^\s+")),
    ("STRING", re.compile(r'^"([^"\\]|\\.)*"')),
    ("CHAR", re.compile(r"^'([^'\\]|\\.)*'")),
    ("HEX", re.compile(r"^0[xX][0-9A-Fa-f]+")),
    ("FLOAT", re.compile(r"^(\d+\.\d*|\.\d+)([eE][+-]?\d+)?")),
    ("INT", re.compile(r"^\d+")),
    ("IDENT", re.compile(r"^[A-Za-z_][A-Za-z0-9_]*")),
    ("OP", re.compile(r"^(" + OP_PATTERN + r")")),
    ("PUNCT", re.compile(r"^(" + PUNCT_PATTERN + r")")),
    ("OTHER", re.compile(r"^.")),
]


def _advance_position(fragment: str, line: int, column: int) -> tuple[int, int]:
    for char in fragment:
        if char == "\n":
            line += 1
            column = 1
        else:
            column += 1
    return line, column


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    line = 1
    column = 1

    while index < len(source):
        fragment = source[index:]

        for name, pattern in TOKEN_PATTERNS:
            match = pattern.match(fragment)
            if match is None:
                continue

            lexeme = match.group(0)
            start_line, start_column = line, column
            index += len(lexeme)
            line, column = _advance_position(lexeme, line, column)

            if name in {"COMMENT", "WS"}:
                break
            if name in {"STRING", "CHAR"}:
                raise ValueError(
                    f"Literals are not supported by the parser grammar: {lexeme!r} "
                    f"at line {start_line}, column {start_column}."
                )
            if name in {"HEX", "FLOAT", "INT"}:
                tokens.append(Token("CONSTANT", lexeme, start_line, start_column))
                break
            if name == "IDENT":
                kind = "KEYWORD" if lexeme in KEYWORDS else "IDENTIFIER"
                tokens.append(Token(kind, lexeme, start_line, start_column))
                break
            if name == "OP":
                tokens.append(Token("OPERATOR", lexeme, start_line, start_column))
                break
            if name == "PUNCT":
                tokens.append(Token("PUNCTUATION", lexeme, start_line, start_column))
                break

            raise ValueError(
                f"Unexpected symbol {lexeme!r} at line {start_line}, column {start_column}."
            )

    tokens.append(Token("EOF", "$", line, column))
    return tokens


def classify_tokens(tokens: Iterable[Token]) -> list[str]:
    legacy_types: list[str] = []
    for token in tokens:
        if token.kind == "EOF":
            continue
        if token.kind == "KEYWORD":
            legacy_types.append("keyword")
        elif token.kind == "IDENTIFIER":
            legacy_types.append("identifier")
        elif token.kind == "CONSTANT":
            legacy_types.append("constant")
        elif token.kind == "OPERATOR":
            legacy_types.append("operator")
        elif token.kind == "PUNCTUATION":
            legacy_types.append("punctuation")
        else:
            legacy_types.append(token.kind.lower())
    return legacy_types


def read_source(path: str = "input.txt") -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def main() -> None:
    source = read_source()
    tokens = tokenize(source)
    legacy_types = classify_tokens(tokens)
    print(" ".join(legacy_types))
    print(f"Total of tokens: {len(legacy_types)}")
    print("\nDetailed tokens:")
    for token in tokens:
        if token.kind == "EOF":
            continue
        print(f"{token.kind:<12} {token.lexeme!r:<12} line={token.line} column={token.column}")


if __name__ == "__main__":
    main()
