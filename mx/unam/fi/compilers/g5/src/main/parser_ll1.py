from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexer import Token


EPSILON = "ε"


@dataclass(frozen=True)
class Production:
    index: int
    lhs: str
    rhs: tuple[str, ...]

    def __str__(self) -> str:
        body = " ".join(self.rhs) if self.rhs else EPSILON
        return f"{self.lhs} -> {body}"


@dataclass
class Grammar:
    start_symbol: str
    productions: list[Production]
    terminals: set[str]
    non_terminals: set[str]
    by_lhs: dict[str, list[Production]]


@dataclass
class TreeNode:
    symbol: str
    lexeme: str | None = None
    token: Token | None = None
    children: list["TreeNode"] = field(default_factory=list)
    annotations: dict[str, Any] = field(default_factory=dict)

    def label(self, include_annotations: bool = False) -> str:
        base = self.symbol if self.lexeme is None else f"{self.symbol}\n{self.lexeme}"
        if not include_annotations or not self.annotations:
            return base
        annotation_parts: list[str] = []
        if "status" in self.annotations:
            annotation_parts.append(self.annotations["status"])
        if "type" in self.annotations and self.annotations["type"]:
            annotation_parts.append(f"type={self.annotations['type']}")
        if "message" in self.annotations and self.annotations["message"]:
            annotation_parts.append(self.annotations["message"])
        if annotation_parts:
            return base + "\n" + "\n".join(annotation_parts)
        return base


@dataclass
class ParseTraceStep:
    step: int
    stack: list[str]
    remaining_input: list[str]
    action: str


@dataclass
class ParseResult:
    success: bool
    root: TreeNode | None
    trace: list[ParseTraceStep]
    error: str | None = None


@dataclass
class SemanticResult:
    success: bool
    verified_root: TreeNode
    ast_root: TreeNode
    symbol_table: dict[str, dict[str, Any]]
    errors: list[str]


def build_grammar() -> Grammar:
    productions = [
        Production(1, "S", ("DECLARATION",)),
        Production(2, "DECLARATION", ("TYPE", "identifier", "DECLARATION_PRIME")),
        Production(3, "DECLARATION_PRIME", ("=", "EXPRESSION", ";")),
        Production(4, "DECLARATION_PRIME", (";",)),
        Production(5, "TYPE", ("int",)),
        Production(6, "TYPE", ("float",)),
        Production(7, "TYPE", ("char",)),
        Production(8, "TYPE", ("double",)),
        Production(9, "EXPRESSION", ("TERM", "EXPRESSION_PRIME")),
        Production(10, "EXPRESSION_PRIME", ("+", "TERM", "EXPRESSION_PRIME")),
        Production(11, "EXPRESSION_PRIME", ("-", "TERM", "EXPRESSION_PRIME")),
        Production(12, "EXPRESSION_PRIME", (EPSILON,)),
        Production(13, "TERM", ("FACTOR", "TERM_PRIME")),
        Production(14, "TERM_PRIME", ("*", "FACTOR", "TERM_PRIME")),
        Production(15, "TERM_PRIME", ("/", "FACTOR", "TERM_PRIME")),
        Production(16, "TERM_PRIME", (EPSILON,)),
        Production(17, "FACTOR", ("identifier",)),
        Production(18, "FACTOR", ("constant",)),
        Production(19, "FACTOR", ("(", "EXPRESSION", ")")),
    ]
    non_terminals = {production.lhs for production in productions}
    terminals = {
        "int",
        "float",
        "char",
        "double",
        "identifier",
        "constant",
        "=",
        ";",
        "+",
        "-",
        "*",
        "/",
        "(",
        ")",
        "$",
    }
    by_lhs: dict[str, list[Production]] = {}
    for production in productions:
        by_lhs.setdefault(production.lhs, []).append(production)
    return Grammar("S", productions, terminals, non_terminals, by_lhs)


def compute_first(grammar: Grammar) -> dict[str, set[str]]:
    first: dict[str, set[str]] = {symbol: set() for symbol in grammar.non_terminals}

    changed = True
    while changed:
        changed = False
        for production in grammar.productions:
            lhs_first = first[production.lhs]
            rhs_first = first_of_sequence(production.rhs, first, grammar)
            before = len(lhs_first)
            lhs_first.update(rhs_first)
            changed = changed or len(lhs_first) != before
    return first


def first_of_sequence(
    symbols: tuple[str, ...] | list[str],
    first: dict[str, set[str]],
    grammar: Grammar,
) -> set[str]:
    if not symbols:
        return {EPSILON}

    result: set[str] = set()
    for symbol in symbols:
        if symbol == EPSILON:
            result.add(EPSILON)
            return result
        if symbol in grammar.terminals:
            result.add(symbol)
            return result

        symbol_first = first[symbol]
        result.update(symbol_first - {EPSILON})
        if EPSILON not in symbol_first:
            return result

    result.add(EPSILON)
    return result


def compute_follow(grammar: Grammar, first: dict[str, set[str]]) -> dict[str, set[str]]:
    follow: dict[str, set[str]] = {symbol: set() for symbol in grammar.non_terminals}
    follow[grammar.start_symbol].add("$")

    changed = True
    while changed:
        changed = False
        for production in grammar.productions:
            rhs = production.rhs
            for index, symbol in enumerate(rhs):
                if symbol not in grammar.non_terminals:
                    continue

                trailer = first_of_sequence(rhs[index + 1 :], first, grammar)
                before = len(follow[symbol])
                follow[symbol].update(trailer - {EPSILON})
                if EPSILON in trailer or index == len(rhs) - 1:
                    follow[symbol].update(follow[production.lhs])
                changed = changed or len(follow[symbol]) != before
    return follow


def build_ll1_table(
    grammar: Grammar,
    first: dict[str, set[str]],
    follow: dict[str, set[str]],
) -> dict[tuple[str, str], Production]:
    table: dict[tuple[str, str], Production] = {}
    for production in grammar.productions:
        rhs_first = first_of_sequence(production.rhs, first, grammar)
        for terminal in rhs_first - {EPSILON}:
            key = (production.lhs, terminal)
            if key in table:
                raise ValueError(f"LL(1) conflict in parsing table for {key}.")
            table[key] = production
        if EPSILON in rhs_first:
            for terminal in follow[production.lhs]:
                key = (production.lhs, terminal)
                if key in table:
                    raise ValueError(f"LL(1) conflict in parsing table for {key}.")
                table[key] = production
    return table


def parse(tokens: list[Token], grammar: Grammar, table: dict[tuple[str, str], Production]) -> ParseResult:
    root = TreeNode(grammar.start_symbol)
    stack: list[tuple[str, TreeNode]] = [("$", TreeNode("$")), (grammar.start_symbol, root)]
    trace: list[ParseTraceStep] = []
    step = 1
    index = 0

    while stack:
        symbol, node = stack.pop()
        lookahead = tokens[index].parser_terminal
        remaining = [token.parser_terminal for token in tokens[index:]]

        if symbol == "$":
            if lookahead == "$":
                trace.append(ParseTraceStep(step, [item[0] for item in stack] + ["$"], remaining, "accept"))
                return ParseResult(True, root, trace)
            error = f"Expected end of input but found {tokens[index].lexeme!r}."
            trace.append(ParseTraceStep(step, [item[0] for item in stack] + ["$"], remaining, error))
            return ParseResult(False, root, trace, error)

        if symbol in grammar.terminals:
            if symbol == lookahead:
                token = tokens[index]
                node.lexeme = token.lexeme
                node.token = token
                trace.append(
                    ParseTraceStep(
                        step,
                        [item[0] for item in stack] + [symbol],
                        remaining,
                        f"match {symbol}",
                    )
                )
                index += 1
            else:
                actual = tokens[index]
                error = (
                    f"Syntax error: expected {symbol!r}, found {actual.lexeme!r} "
                    f"at line {actual.line}, column {actual.column}."
                )
                trace.append(ParseTraceStep(step, [item[0] for item in stack] + [symbol], remaining, error))
                return ParseResult(False, root, trace, error)
            step += 1
            continue

        production = table.get((symbol, lookahead))
        if production is None:
            actual = tokens[index]
            error = (
                f"No production for {symbol} with lookahead {lookahead!r} "
                f"({actual.lexeme!r} at line {actual.line}, column {actual.column})."
            )
            trace.append(ParseTraceStep(step, [item[0] for item in stack] + [symbol], remaining, error))
            return ParseResult(False, root, trace, error)

        children: list[TreeNode] = []
        for rhs_symbol in production.rhs:
            child = TreeNode(rhs_symbol)
            children.append(child)
        node.children = children

        for rhs_symbol, child in reversed(list(zip(production.rhs, children))):
            if rhs_symbol == EPSILON:
                child.annotations["status"] = "epsilon"
                continue
            stack.append((rhs_symbol, child))

        trace.append(
            ParseTraceStep(
                step,
                [item[0] for item in stack],
                remaining,
                f"apply {production}",
            )
        )
        step += 1

    error = "Parser stack exhausted unexpectedly."
    return ParseResult(False, root, trace, error)


def annotate_parse_tree(node: TreeNode) -> TreeNode:
    cloned = TreeNode(node.symbol, node.lexeme, node.token, annotations=dict(node.annotations))
    cloned.children = [annotate_parse_tree(child) for child in node.children]
    return cloned


def run_semantic_analysis(parse_root: TreeNode) -> SemanticResult:
    verified_root = annotate_parse_tree(parse_root)
    symbol_table: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    ast_root = _analyze_start(verified_root, symbol_table, errors)
    return SemanticResult(not errors, verified_root, ast_root, symbol_table, errors)


def _mark(node: TreeNode, status: str, inferred_type: str | None = None, message: str | None = None) -> None:
    node.annotations["status"] = status
    if inferred_type:
        node.annotations["type"] = inferred_type
    if message:
        node.annotations["message"] = message


def _analyze_start(
    node: TreeNode,
    symbol_table: dict[str, dict[str, Any]],
    errors: list[str],
) -> TreeNode:
    declaration = node.children[0]
    ast_root = _analyze_declaration(declaration, symbol_table, errors)
    _mark(node, "ok" if not errors else "error")
    return ast_root


def _analyze_declaration(
    node: TreeNode,
    symbol_table: dict[str, dict[str, Any]],
    errors: list[str],
) -> TreeNode:
    type_node = node.children[0]
    identifier_node = node.children[1]
    suffix_node = node.children[2]

    declared_type = _analyze_type(type_node)
    name = identifier_node.lexeme or ""
    _mark(identifier_node, "ok", message=f"name={name}")

    initializer_ast: TreeNode | None = None
    initialized = False

    if len(suffix_node.children) == 3:
        expression_node = suffix_node.children[1]
        expr_type, initializer_ast = _analyze_expression(expression_node, symbol_table, errors)
        if expr_type is None:
            _mark(suffix_node, "error", message="invalid initializer")
        elif not _is_assignment_compatible(declared_type, expr_type):
            message = f"cannot assign {expr_type} to {declared_type}"
            errors.append(message)
            _mark(suffix_node, "error", message=message)
        else:
            initialized = True
            _mark(suffix_node, "ok", inferred_type=expr_type)
    else:
        _mark(suffix_node, "ok", message="declaration without initializer")

    if name in symbol_table:
        message = f"redeclaration of identifier {name}"
        errors.append(message)
        _mark(node, "error", declared_type, message)
    else:
        symbol_table[name] = {"declared_type": declared_type, "initialized": initialized}
        _mark(node, "ok" if not errors else "error", declared_type)

    ast_children = [
        TreeNode(declared_type),
        TreeNode(name),
    ]
    if initializer_ast is not None:
        ast_children.append(initializer_ast)
    return TreeNode("=", children=ast_children)


def _analyze_type(node: TreeNode) -> str:
    type_leaf = node.children[0]
    declared_type = type_leaf.lexeme or type_leaf.symbol
    _mark(type_leaf, "ok", declared_type)
    _mark(node, "ok", declared_type)
    return declared_type


def _analyze_expression(
    node: TreeNode,
    symbol_table: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[str | None, TreeNode | None]:
    term_node = node.children[0]
    tail_node = node.children[1]
    left_type, left_ast = _analyze_term(term_node, symbol_table, errors)
    expr_type, expr_ast = _fold_expression_prime(left_type, left_ast, tail_node, symbol_table, errors)
    _mark(node, "ok" if expr_type is not None else "error", expr_type)
    return expr_type, expr_ast


def _fold_expression_prime(
    current_type: str | None,
    current_ast: TreeNode | None,
    node: TreeNode,
    symbol_table: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[str | None, TreeNode | None]:
    if len(node.children) == 1 and node.children[0].symbol == EPSILON:
        _mark(node, "ok", current_type)
        return current_type, current_ast

    operator_node = node.children[0]
    term_node = node.children[1]
    tail_node = node.children[2]
    right_type, right_ast = _analyze_term(term_node, symbol_table, errors)

    result_type = _combine_numeric_types(current_type, right_type, operator_node.lexeme or operator_node.symbol, errors)
    result_ast = (
        TreeNode(operator_node.lexeme, children=[current_ast, right_ast])
        if current_ast is not None and right_ast is not None
        else None
    )
    _mark(operator_node, "ok" if result_type else "error")
    _mark(node, "ok" if result_type else "error", result_type)
    return _fold_expression_prime(result_type, result_ast, tail_node, symbol_table, errors)


def _analyze_term(
    node: TreeNode,
    symbol_table: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[str | None, TreeNode | None]:
    factor_node = node.children[0]
    tail_node = node.children[1]
    left_type, left_ast = _analyze_factor(factor_node, symbol_table, errors)
    term_type, term_ast = _fold_term_prime(left_type, left_ast, tail_node, symbol_table, errors)
    _mark(node, "ok" if term_type is not None else "error", term_type)
    return term_type, term_ast


def _fold_term_prime(
    current_type: str | None,
    current_ast: TreeNode | None,
    node: TreeNode,
    symbol_table: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[str | None, TreeNode | None]:
    if len(node.children) == 1 and node.children[0].symbol == EPSILON:
        _mark(node, "ok", current_type)
        return current_type, current_ast

    operator_node = node.children[0]
    factor_node = node.children[1]
    tail_node = node.children[2]
    right_type, right_ast = _analyze_factor(factor_node, symbol_table, errors)

    result_type = _combine_numeric_types(current_type, right_type, operator_node.lexeme or operator_node.symbol, errors)
    result_ast = (
        TreeNode(operator_node.lexeme, children=[current_ast, right_ast])
        if current_ast is not None and right_ast is not None
        else None
    )
    _mark(operator_node, "ok" if result_type else "error")
    _mark(node, "ok" if result_type else "error", result_type)
    return _fold_term_prime(result_type, result_ast, tail_node, symbol_table, errors)


def _analyze_factor(
    node: TreeNode,
    symbol_table: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[str | None, TreeNode | None]:
    first_child = node.children[0]
    if first_child.symbol == "identifier":
        name = first_child.lexeme or ""
        symbol = symbol_table.get(name)
        if symbol is None:
            message = f"identifier {name} used before declaration"
            errors.append(message)
            _mark(first_child, "error", message=message)
            _mark(node, "error", message=message)
            return None, TreeNode("Identifier", lexeme=name)
        inferred_type = symbol["declared_type"]
        _mark(first_child, "ok", inferred_type)
        _mark(node, "ok", inferred_type)
        return inferred_type, TreeNode(name)

    if first_child.symbol == "constant":
        inferred_type = _infer_constant_type(first_child.lexeme or "")
        _mark(first_child, "ok", inferred_type)
        _mark(node, "ok", inferred_type)
        return inferred_type, TreeNode(first_child.lexeme)

    expression_node = node.children[1]
    expr_type, expr_ast = _analyze_expression(expression_node, symbol_table, errors)
    _mark(node.children[0], "ok")
    _mark(node.children[2], "ok")
    _mark(node, "ok" if expr_type else "error", expr_type)
    return expr_type, expr_ast


def _infer_constant_type(lexeme: str) -> str:
    if "." in lexeme or "e" in lexeme.lower():
        return "float"
    return "int"


def _combine_numeric_types(
    left: str | None,
    right: str | None,
    operator: str,
    errors: list[str],
) -> str | None:
    if left is None or right is None:
        return None
    if left == "char" or right == "char":
        errors.append(f"operator {operator} does not accept char operands")
        return None
    numeric_order = ["int", "float", "double"]
    if left not in numeric_order or right not in numeric_order:
        errors.append(f"operator {operator} only accepts numeric operands")
        return None
    return numeric_order[max(numeric_order.index(left), numeric_order.index(right))]


def _is_assignment_compatible(declared_type: str, expression_type: str) -> bool:
    compatibility = {
        "char": {"char"},
        "int": {"int"},
        "float": {"int", "float"},
        "double": {"int", "float", "double"},
    }
    return expression_type in compatibility.get(declared_type, set())


def format_first_follow(
    first: dict[str, set[str]],
    follow: dict[str, set[str]],
) -> str:
    lines = ["FIRST sets:"]
    for symbol in sorted(first):
        lines.append(f"FIRST({symbol}) = {{{', '.join(sorted(first[symbol]))}}}")
    lines.append("")
    lines.append("FOLLOW sets:")
    for symbol in sorted(follow):
        lines.append(f"FOLLOW({symbol}) = {{{', '.join(sorted(follow[symbol]))}}}")
    return "\n".join(lines)


def format_parsing_table(grammar: Grammar, table: dict[tuple[str, str], Production]) -> str:
    terminals = [t for t in sorted(grammar.terminals) if t != "$"] + ["$"]
    lines = ["LL(1) Parsing Table:"]
    header = ["NonTerminal"] + terminals
    lines.append("\t".join(header))
    for non_terminal in sorted(grammar.non_terminals):
        row = [non_terminal]
        for terminal in terminals:
            production = table.get((non_terminal, terminal))
            row.append(str(production) if production else "")
        lines.append("\t".join(row))
    return "\n".join(lines)


def format_trace(trace: list[ParseTraceStep]) -> str:
    lines = ["step\tstack\tinput\taction"]
    for entry in trace:
        stack = " ".join(entry.stack)
        remaining = " ".join(entry.remaining_input)
        lines.append(f"{entry.step}\t{stack}\t{remaining}\t{entry.action}")
    return "\n".join(lines)
