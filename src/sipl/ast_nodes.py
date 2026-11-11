from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SourceSpan:
    """Точні координати вузла у вихідному коді."""
    line: int
    column: int
    end_line: int
    end_column: int

    def __repr__(self) -> str:
        return f"{self.line}:{self.column}-{self.end_line}:{self.end_column}"


class ASTNode:
    """Базовий клас для всіх вузлів AST."""
    span: Optional[SourceSpan] = None


# --- Арифметичні вирази (Aexp) ---
class AExpr(ASTNode):
    pass


@dataclass
class Num(AExpr):
    value: int
    span: Optional[SourceSpan] = None


@dataclass
class Var(AExpr):
    name: str
    span: Optional[SourceSpan] = None


@dataclass
class BinOp(AExpr):
    op: str  # '+', '-', '*', 'div', 'mod'
    left: AExpr
    right: AExpr
    span: Optional[SourceSpan] = None


# --- Булеві вирази (Bexp) ---
class BExpr(ASTNode):
    pass


@dataclass
class BoolConst(BExpr):
    value: bool
    span: Optional[SourceSpan] = None


@dataclass
class RelOp(BExpr):
    op: str  # '=', '!=', '<', '<=', '>', '>='
    left: AExpr
    right: AExpr
    span: Optional[SourceSpan] = None


@dataclass
class NotOp(BExpr):
    expr: BExpr
    span: Optional[SourceSpan] = None


@dataclass
class LogicBinOp(BExpr):
    op: str  # 'and', 'or'
    left: BExpr
    right: BExpr
    span: Optional[SourceSpan] = None


# --- Оператори (Statements) ---
class Statement(ASTNode):
    pass


@dataclass
class Skip(Statement):
    span: Optional[SourceSpan] = None


@dataclass
class Assign(Statement):
    var: str
    expr: AExpr
    span: Optional[SourceSpan] = None


@dataclass
class Seq(Statement):
    statements: List[Statement]
    span: Optional[SourceSpan] = None


@dataclass
class If(Statement):
    cond: BExpr
    then_branch: Statement
    else_branch: Statement
    span: Optional[SourceSpan] = None


@dataclass
class While(Statement):
    cond: BExpr
    body: Statement
    span: Optional[SourceSpan] = None


@dataclass
class Block(Statement):
    body: Statement
    span: Optional[SourceSpan] = None


@dataclass
class Program(ASTNode):
    body: Statement
    span: Optional[SourceSpan] = None


def format_expr(node: ASTNode) -> str:
    """Форматує арифметичний або булевий вираз у канонічний людиночитаний рядок."""
    if isinstance(node, Num):
        return str(node.value)
    elif isinstance(node, Var):
        return node.name
    elif isinstance(node, BinOp):
        return f"{format_expr(node.left)} {node.op} {format_expr(node.right)}"
    elif isinstance(node, BoolConst):
        return "true" if node.value else "false"
    elif isinstance(node, NotOp):
        return f"not ({format_expr(node.expr)})"
    elif isinstance(node, LogicBinOp):
        return f"({format_expr(node.left)} {node.op} {format_expr(node.right)})"
    elif isinstance(node, RelOp):
        return f"{format_expr(node.left)} {node.op} {format_expr(node.right)}"
    return str(node)


def ast_to_dict(node: ASTNode) -> Dict[str, Any]:
    """Рекурсивно серіалізує AST-вузол у формат словника для JSON-експорту."""
    if isinstance(node, Num):
        res: Dict[str, Any] = {"type": "Num", "value": node.value}
    elif isinstance(node, Var):
        res = {"type": "Var", "name": node.name}
    elif isinstance(node, BinOp):
        res = {
            "type": "BinOp",
            "op": node.op,
            "left": ast_to_dict(node.left),
            "right": ast_to_dict(node.right)
        }
    elif isinstance(node, BoolConst):
        res = {"type": "BoolConst", "value": node.value}
    elif isinstance(node, NotOp):
        res = {"type": "NotOp", "expr": ast_to_dict(node.expr)}
    elif isinstance(node, LogicBinOp):
        res = {
            "type": "LogicBinOp",
            "op": node.op,
            "left": ast_to_dict(node.left),
            "right": ast_to_dict(node.right)
        }
    elif isinstance(node, RelOp):
        res = {
            "type": "RelOp",
            "op": node.op,
            "left": ast_to_dict(node.left),
            "right": ast_to_dict(node.right)
        }
    elif isinstance(node, Skip):
        res = {"type": "Skip"}
    elif isinstance(node, Assign):
        res = {"type": "Assign", "var": node.var, "expr": ast_to_dict(node.expr)}
    elif isinstance(node, Seq):
        res = {"type": "Seq", "statements": [ast_to_dict(s) for s in node.statements]}
    elif isinstance(node, If):
        res = {
            "type": "If",
            "cond": ast_to_dict(node.cond),
            "then_branch": ast_to_dict(node.then_branch),
            "else_branch": ast_to_dict(node.else_branch)
        }
    elif isinstance(node, While):
        res = {
            "type": "While",
            "cond": ast_to_dict(node.cond),
            "body": ast_to_dict(node.body)
        }
    elif isinstance(node, Block):
        res = {"type": "Block", "body": ast_to_dict(node.body)}
    elif isinstance(node, Program):
        res = {"type": "Program", "body": ast_to_dict(node.body)}
    else:
        res = {"type": type(node).__name__}

    if node.span:
        res["span"] = {
            "line": node.span.line,
            "column": node.span.column,
            "end_line": node.span.end_line,
            "end_column": node.span.end_column
        }
    return res
