from pathlib import Path
from typing import cast

from lark import Lark, Transformer, UnexpectedInput, v_args

from .ast_nodes import (
    Assign,
    BinOp,
    Block,
    BoolConst,
    If,
    LogicBinOp,
    NotOp,
    Num,
    Program,
    RelOp,
    Seq,
    Skip,
    SourceSpan,
    Var,
    While,
)

DEFAULT_GRAMMAR_PATH = Path(__file__).resolve().parent / "grammar" / "sipl.lark"


class SIPLSyntaxError(Exception):
    """Кастомний виняток синтаксичної помилки з координатами."""

    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Syntax Error at {line}:{column} -> {message}")


def make_span(meta) -> SourceSpan:
    return SourceSpan(
        line=meta.line,
        column=meta.column,
        end_line=meta.end_line,
        end_column=meta.end_column
    )


@v_args(meta=True)
class ASTBuilder(Transformer):
    """Трансформує сире дерево Lark у типізоване AST SIPL."""

    def program(self, meta, children):
        stmt = children[0]
        return Program(body=stmt, span=make_span(meta))

    def seq_stmt(self, meta, children):
        if len(children) == 1:
            return children[0]
        return Seq(statements=list(children), span=make_span(meta))

    def assign_stmt(self, meta, children):
        var_token, expr = children
        return Assign(var=str(var_token), expr=expr, span=make_span(meta))

    def if_stmt(self, meta, children):
        cond, then_b, else_b = children
        return If(cond=cond, then_branch=then_b, else_branch=else_b, span=make_span(meta))

    def while_stmt(self, meta, children):
        cond, body = children
        return While(cond=cond, body=body, span=make_span(meta))

    def block_stmt(self, meta, children):
        return Block(body=children[0], span=make_span(meta))

    def skip_stmt(self, meta, children):
        return Skip(span=make_span(meta))

    # --- Арифметика ---
    def add(self, meta, children):
        return BinOp(op="+", left=children[0], right=children[1], span=make_span(meta))

    def sub(self, meta, children):
        return BinOp(op="-", left=children[0], right=children[1], span=make_span(meta))

    def mul(self, meta, children):
        return BinOp(op="*", left=children[0], right=children[1], span=make_span(meta))

    def div(self, meta, children):
        return BinOp(op="div", left=children[0], right=children[1], span=make_span(meta))

    def mod(self, meta, children):
        return BinOp(op="mod", left=children[0], right=children[1], span=make_span(meta))

    def var(self, meta, children):
        return Var(name=str(children[0]), span=make_span(meta))

    def num(self, meta, children):
        return Num(value=int(children[0]), span=make_span(meta))

    # --- Булеві вирази ---
    def rel_expr(self, meta, children):
        left, op_tok, right = children
        return RelOp(op=str(op_tok), left=left, right=right, span=make_span(meta))

    def b_or(self, meta, children):
        return LogicBinOp(op="or", left=children[0], right=children[1], span=make_span(meta))

    def b_and(self, meta, children):
        return LogicBinOp(op="and", left=children[0], right=children[1], span=make_span(meta))

    def b_not(self, meta, children):
        return NotOp(expr=children[0], span=make_span(meta))

    def b_true(self, meta, children):
        return BoolConst(value=True, span=make_span(meta))

    def b_false(self, meta, children):
        return BoolConst(value=False, span=make_span(meta))


class SIPLParser:
    def __init__(self, grammar_path: Path = DEFAULT_GRAMMAR_PATH):
        with open(grammar_path, "r", encoding="utf-8") as f:
            grammar = f.read()
        self.parser = Lark(grammar, parser="lalr", start="program", propagate_positions=True)
        self.transformer = ASTBuilder()

    def parse(self, code: str) -> Program:
        """Парсить вихідний код SIPL у типізоване AST Program."""
        try:
            raw_tree = self.parser.parse(code)
            res = self.transformer.transform(raw_tree)
            return cast(Program, res)
        except UnexpectedInput as e:
            line = getattr(e, "line", None)
            column = getattr(e, "column", None)

            if line is None or column is None or line <= 0 or column <= 0:
                lines = code.splitlines()
                line = max(1, len(lines))
                column = max(1, len(lines[-1]) + 1 if lines else 1)

            raise SIPLSyntaxError(
                message=f"Unexpected syntax or token near '{getattr(e, 'token', 'EOF')}': expected valid statement",
                line=line,
                column=column
            ) from e
