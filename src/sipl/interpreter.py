from typing import Dict, Optional

from .ast_nodes import (
    AExpr,
    Assign,
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
    format_expr,
)
from .tracer import ExecutionTracer


class SIPLRuntimeError(Exception):
    """Базовий виняток для помилок під час виконання програми."""
    pass


class StepLimitExceededError(SIPLRuntimeError):
    """Помилка перевищення ліміту кроків (захист від зациклення)."""
    pass


class DivisionByZeroError(SIPLRuntimeError):
    """Помилка ділення на нуль."""
    pass


class UndefinedVariableError(SIPLRuntimeError):
    """Спроба прочитати змінну, якій не було присвоєно значення."""
    pass


class Interpreter:
    def __init__(self, step_limit: int = 100000, tracer: Optional[ExecutionTracer] = None):
        self.step_limit = step_limit
        self.step_count = 0
        self.state: Dict[str, int] = {}
        self.tracer: Optional[ExecutionTracer] = tracer

    def _tick(self):
        self.step_count += 1
        if self.step_count > self.step_limit:
            raise StepLimitExceededError(
                f"Execution step limit exceeded ({self.step_limit} steps). Possible infinite loop."
            )

    def execute(self, program: Program, initial_state: Optional[Dict[str, int]] = None) -> Dict[str, int]:
        self.step_count = 0
        self.state = dict(initial_state) if initial_state else {}
        if self.tracer:
            self.tracer.clear()

        try:
            self._exec_stmt(program.body)
        except SIPLRuntimeError as e:
            if self.tracer:
                self.tracer.emit_error(type(e).__name__, str(e), self.state)
            raise

        if self.tracer:
            self.tracer.emit_finished(self.state, total_steps=self.step_count)

        return self.state

    def _exec_stmt(self, stmt: Statement):
        self._tick()
        stmt_name = type(stmt).__name__

        if self.tracer:
            self.tracer.emit_before_stmt(stmt_name, stmt.span, self.state)

        if isinstance(stmt, Skip):
            pass

        elif isinstance(stmt, Assign):
            old_val = self.state.get(stmt.var)
            val = self._eval_aexpr(stmt.expr)
            self.state[stmt.var] = val
            if self.tracer:
                self.tracer.emit_var_change(stmt.var, old_val, val, self.state, stmt.span)

        elif isinstance(stmt, Seq):
            for s in stmt.statements:
                self._exec_stmt(s)

        elif isinstance(stmt, If):
            cond_res = self._eval_bexpr(stmt.cond)
            if self.tracer:
                self.tracer.emit_condition_check(
                    format_expr(stmt.cond),
                    cond_res,
                    origin="If",
                    span=stmt.cond.span,
                    current_state=self.state
                )

            if cond_res:
                self._exec_stmt(stmt.then_branch)
            else:
                self._exec_stmt(stmt.else_branch)

        elif isinstance(stmt, While):
            while True:
                cond_res = self._eval_bexpr(stmt.cond)
                if self.tracer:
                    self.tracer.emit_condition_check(
                        format_expr(stmt.cond),
                        cond_res,
                        origin="While",
                        span=stmt.cond.span,
                        current_state=self.state
                    )

                if not cond_res:
                    break

                self._exec_stmt(stmt.body)

        elif isinstance(stmt, Block):
            self._exec_stmt(stmt.body)

        else:
            raise SIPLRuntimeError(f"Unknown statement type: {type(stmt)}")

        if self.tracer:
            self.tracer.emit_after_stmt(stmt_name, stmt.span, self.state)

    def _eval_aexpr(self, expr: AExpr) -> int:
        if isinstance(expr, Num):
            return expr.value

        elif isinstance(expr, Var):
            if expr.name not in self.state:
                raise UndefinedVariableError(f"Variable '{expr.name}' is referenced before assignment.")
            return self.state[expr.name]

        elif isinstance(expr, BinOp):
            left = self._eval_aexpr(expr.left)
            right = self._eval_aexpr(expr.right)

            if expr.op == "+":
                return left + right
            elif expr.op == "-":
                return left - right
            elif expr.op == "*":
                return left * right
            elif expr.op == "div":
                if right == 0:
                    raise DivisionByZeroError("Division by zero in 'div' operation.")
                return left // right
            elif expr.op == "mod":
                if right == 0:
                    raise DivisionByZeroError("Division by zero in 'mod' operation.")
                return left % right
            else:
                raise SIPLRuntimeError(f"Unknown arithmetic operator: {expr.op}")

        else:
            raise SIPLRuntimeError(f"Unknown arithmetic expression type: {type(expr)}")

    def _eval_bexpr(self, expr: BExpr) -> bool:
        if isinstance(expr, BoolConst):
            return expr.value

        elif isinstance(expr, NotOp):
            return not self._eval_bexpr(expr.expr)

        elif isinstance(expr, LogicBinOp):
            if expr.op == "and":
                return self._eval_bexpr(expr.left) and self._eval_bexpr(expr.right)
            elif expr.op == "or":
                return self._eval_bexpr(expr.left) or self._eval_bexpr(expr.right)
            else:
                raise SIPLRuntimeError(f"Unknown logical operator: {expr.op}")

        elif isinstance(expr, RelOp):
            left = self._eval_aexpr(expr.left)
            right = self._eval_aexpr(expr.right)

            if expr.op == "=":
                return left == right
            elif expr.op == "!=":
                return left != right
            elif expr.op == "<":
                return left < right
            elif expr.op == "<=":
                return left <= right
            elif expr.op == ">":
                return left > right
            elif expr.op == ">=":
                return left >= right
            else:
                raise SIPLRuntimeError(f"Unknown relational operator: {expr.op}")

        else:
            raise SIPLRuntimeError(f"Unknown boolean expression type: {type(expr)}")
