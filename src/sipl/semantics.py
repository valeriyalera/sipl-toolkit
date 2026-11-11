from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .ast_nodes import (
    AExpr,
    Assign,
    ASTNode,
    BExpr,
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
    Statement,
    Var,
    While,
)


@dataclass
class Term:
    """Вузол семантичного терму."""
    name: str
    args: List[Any]
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "args": [a.to_dict() if isinstance(a, Term) else a for a in self.args],
            "meta": self.meta or {}
        }


class SemanticTermBuilder:
    """Рекурсивна побудова семантичного терму з AST за правилами Практичної роботи №2."""

    def build(self, node: ASTNode) -> Term:
        if isinstance(node, Program):
            return self.build_stmt(node.body)
        elif isinstance(node, Statement):
            return self.build_stmt(node)
        elif isinstance(node, AExpr):
            return self.build_aexpr(node)
        elif isinstance(node, BExpr):
            return self.build_bexpr(node)
        raise ValueError(f"Unknown AST node type: {type(node)}")

    def build_stmt(self, stmt: Statement) -> Term:
        if isinstance(stmt, Skip):
            return Term("id", [])

        elif isinstance(stmt, Assign):
            a_term = self.build_aexpr(stmt.expr)
            return Term("AS", [stmt.var, a_term])

        elif isinstance(stmt, Seq):
            if not stmt.statements:
                return Term("id", [])
            terms = [self.build_stmt(s) for s in stmt.statements]
            res = terms[0]
            for next_t in terms[1:]:
                res = Term("compose", [res, next_t])
            return res

        elif isinstance(stmt, If):
            b_term = self.build_bexpr(stmt.cond)
            s1_term = self.build_stmt(stmt.then_branch)
            s2_term = self.build_stmt(stmt.else_branch)
            return Term("IF", [b_term, s1_term, s2_term])

        elif isinstance(stmt, While):
            b_term = self.build_bexpr(stmt.cond)
            s_term = self.build_stmt(stmt.body)
            return Term("WH", [b_term, s_term])

        elif isinstance(stmt, Block):
            return self.build_stmt(stmt.body)

        raise ValueError(f"Unsupported Statement node: {type(stmt)}")

    def build_aexpr(self, expr: AExpr) -> Term:
        if isinstance(expr, Num):
            return Term("const", [expr.value])

        elif isinstance(expr, Var):
            return Term("var", [expr.name])

        elif isinstance(expr, BinOp):
            left = self.build_aexpr(expr.left)
            right = self.build_aexpr(expr.right)
            op_map = {"+": "add", "-": "sub", "*": "mult", "div": "div", "mod": "mod"}
            op_name = op_map.get(expr.op, expr.op)
            return Term("S2", [op_name, left, right])

        raise ValueError(f"Unsupported AExpr node: {type(expr)}")

    def build_bexpr(self, expr: BExpr) -> Term:
        if isinstance(expr, BoolConst):
            zero = Term("const", [0])
            eq_zero = Term("S2", ["eq", zero, zero])
            if expr.value:
                return eq_zero
            return Term("S1", ["neg", eq_zero])

        elif isinstance(expr, RelOp):
            left = self.build_aexpr(expr.left)
            right = self.build_aexpr(expr.right)

            if expr.op == "=":
                return Term("S2", ["eq", left, right])
            elif expr.op == ">":
                return Term("S2", ["gr", left, right])
            elif expr.op == "<":
                return Term("S2", ["gr", right, left])
            elif expr.op == ">=":
                return Term("S2", ["or", Term("S2", ["gr", left, right]), Term("S2", ["eq", left, right])])
            elif expr.op == "<=":
                return Term("S2", ["or", Term("S2", ["gr", right, left]), Term("S2", ["eq", left, right])])
            elif expr.op == "!=":
                return Term("S1", ["neg", Term("S2", ["eq", left, right])])

        elif isinstance(expr, NotOp):
            return Term("S1", ["neg", self.build_bexpr(expr.expr)])

        elif isinstance(expr, LogicBinOp):
            left = self.build_bexpr(expr.left)
            right = self.build_bexpr(expr.right)
            if expr.op == "or":
                return Term("S2", ["or", left, right])
            elif expr.op == "and":
                not_l = Term("S1", ["neg", left])
                not_r = Term("S1", ["neg", right])
                return Term("S1", ["neg", Term("S2", ["or", not_l, not_r])])

        raise ValueError(f"Unsupported BExpr node: {type(expr)}")


class TermFormatter:
    """Форматування семантичного терму в Unicode або ASCII."""

    def __init__(self, ascii_mode: bool = False):
        self.ascii_mode = ascii_mode

    def format(self, term: Term) -> str:
        name = term.name
        args = term.args

        if name == "id":
            return "id"

        elif name == "const":
            n = args[0]
            return f"{n}_bar" if self.ascii_mode else f"{n}\u0304"

        elif name == "var":
            x = args[0]
            return f"{x}=>" if self.ascii_mode else f"{x}\u21d2"

        elif name == "AS":
            var, a_term = args[0], self.format(args[1])
            return f"AS^{var}({a_term})"

        elif name == "compose":
            t1, t2 = self.format(args[0]), self.format(args[1])
            dot = " . " if self.ascii_mode else " \u00b7 "
            return f"{t1}{dot}{t2}"

        elif name == "IF":
            b, s1, s2 = self.format(args[0]), self.format(args[1]), self.format(args[2])
            return f"IF({b}, {s1}, {s2})"

        elif name == "WH":
            b, s = self.format(args[0]), self.format(args[1])
            return f"WH({b}, {s})"

        elif name == "S1":
            op, arg = args[0], self.format(args[1])
            return f"S^1({op}, {arg})"

        elif name == "S2":
            op, a1, a2 = args[0], self.format(args[1]), self.format(args[2])
            return f"S^2({op}, {a1}, {a2})"

        return f"{name}({', '.join(self.format(a) if isinstance(a, Term) else str(a) for a in args)})"
