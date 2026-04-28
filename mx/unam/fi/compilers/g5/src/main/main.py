from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from lexer import read_source, tokenize
from parser_ll1 import (
    build_grammar,
    build_ll1_table,
    compute_first,
    compute_follow,
    format_first_follow,
    format_parsing_table,
    format_trace,
    parse,
    run_semantic_analysis,
)
from tree_renderer import render_error, render_tree

W = 60


def _c(code: str, text: str) -> str:
    tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    return f"\033[{code}m{text}\033[0m" if tty else text


def bold(t: str) -> str: return _c("1", t)
def green(t: str) -> str: return _c("32", t)
def red(t: str) -> str: return _c("31", t)


def sep() -> None:
    print("─" * W)


def ok(msg: str) -> None:
    print(f"  {green('[OK]')}   {bold(msg)}")


def err(msg: str) -> None:
    print(f"  {red('[ERR]')}  {bold(msg)}")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="LL(1) parser and SDT pipeline")
    parser.add_argument("input", nargs="?", default="input.txt", help="Input source file")
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory where traces and tree images are written",
    )
    args = parser.parse_args()

    os.system("cls" if os.name == "nt" else "clear")
    sep()
    print(f"  {bold('LL(1) Parser - SDT')}")
    sep()
    print()
    print(f"  File: {args.input}")
    print()

    source = read_source(args.input)
    tokens = tokenize(source)

    grammar = build_grammar()
    first = compute_first(grammar)
    follow = compute_follow(grammar, first)
    table = build_ll1_table(grammar, first, follow)
    parse_result = parse(tokens, grammar, table)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    write_text(output_dir / "first_follow.txt", format_first_follow(first, follow))
    write_text(output_dir / "parsing_table.txt", format_parsing_table(grammar, table))
    write_text(output_dir / "parse_trace.txt", format_trace(parse_result.trace))

    print(f"  {bold('PARSING')}")
    if not parse_result.success or parse_result.root is None:
        err("Parsing failed")
        if parse_result.error:
            print(f"       {parse_result.error}")
        print()
        for name in ("parse_tree.png", "verified_parse_tree.png", "abstract_tree.png"):
            render_error("Syntax Error", str(output_dir / name))
        sep()
        return

    ok("Parsing successful")
    print()

    render_tree(parse_result.root, str(output_dir / "parse_tree.png"))

    semantic_result = run_semantic_analysis(parse_result.root)
    render_tree(semantic_result.verified_root, str(output_dir / "verified_parse_tree.png"), include_annotations=True)

    print(f"  {bold('SEMANTIC ANALYSIS')}")
    if semantic_result.success:
        ok("SDT verified")
        render_tree(semantic_result.ast_root, str(output_dir / "abstract_tree.png"))
    else:
        err("SDT with errors")
        for error in semantic_result.errors:
            print(f"       - {error}")
        render_error("Semantic Error", str(output_dir / "abstract_tree.png"))

    print()
    print(f"  Artifacts at: {output_dir.resolve()}")
    print()
    sep()


if __name__ == "__main__":
    main()
