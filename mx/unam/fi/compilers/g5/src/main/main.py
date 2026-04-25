from __future__ import annotations

import argparse
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
from tree_renderer import render_tree


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

    if not parse_result.success or parse_result.root is None:
        print("Parsing error...")
        if parse_result.error:
            print(parse_result.error)
        return

    render_tree(parse_result.root, str(output_dir / "parse_tree.png"))

    semantic_result = run_semantic_analysis(parse_result.root)
    render_tree(semantic_result.verified_root, str(output_dir / "verified_parse_tree.png"), include_annotations=True)
    render_tree(semantic_result.ast_root, str(output_dir / "abstract_tree.png"))

    print("Parsing Success!")
    if semantic_result.success:
        print("SDT Verified!")
    else:
        print("SDT error...")
        for error in semantic_result.errors:
            print(f"- {error}")

    print(f"Artifacts written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
