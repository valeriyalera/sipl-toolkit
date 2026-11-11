import pytest

from sipl.interpreter import (
    DivisionByZeroError,
    Interpreter,
    StepLimitExceededError,
    UndefinedVariableError,
)
from sipl.parser import SIPLParser


@pytest.fixture
def parser():
    return SIPLParser()


@pytest.fixture
def interpreter():
    return Interpreter()


def test_execute_power_canonical(parser, interpreter):
    """Канонічний приклад X^Y з Практичної 1 (X=2, Y=5 -> R=32)."""
    code = """
    begin
        R := 1;
        while Y > 0 do
        begin
            R := R * X;
            Y := Y - 1
        end
    end
    """
    program = parser.parse(code)
    final_state = interpreter.execute(program, initial_state={"X": 2, "Y": 5})

    assert final_state["R"] == 32
    assert final_state["Y"] == 0
    assert final_state["X"] == 2


def test_execute_prime_check(parser, interpreter):
    """Перевірка простоти N=17 (Prime=1) та N=18 (Prime=0)."""
    code = """
    begin
        D := 2;
        Prime := 1;
        while D * D <= N and Prime = 1 do
        begin
            if N mod D = 0 then
                Prime := 0
            else
                skip;
            D := D + 1
        end
    end
    """
    prog = parser.parse(code)

    # N = 17 -> Prime = 1
    state17 = interpreter.execute(prog, initial_state={"N": 17})
    assert state17["Prime"] == 1

    # N = 18 -> Prime = 0
    state18 = interpreter.execute(prog, initial_state={"N": 18})
    assert state18["Prime"] == 0


def test_arithmetic_div_mod_and_precedence(parser, interpreter):
    """Арифметика div, mod, дужки та пріоритет."""
    code = """
    begin
        Q := 17 div 5;
        Rem := 17 mod 5;
        Calc := (2 + 3) * 4 - 6 div 2
    end
    """
    prog = parser.parse(code)
    state = interpreter.execute(prog)

    assert state["Q"] == 3
    assert state["Rem"] == 2
    assert state["Calc"] == 17  # 5 * 4 - 3 = 17


def test_if_else_branches(parser, interpreter):
    """Перевірка виконання обох гілок if-then-else."""
    code = """
    begin
        if A > B then
            Max := A
        else
            Max := B
    end
    """
    prog = parser.parse(code)

    state1 = interpreter.execute(prog, initial_state={"A": 10, "B": 5})
    assert state1["Max"] == 10

    state2 = interpreter.execute(prog, initial_state={"A": 3, "B": 8})
    assert state2["Max"] == 8


def test_infinite_loop_step_limit(parser):
    """Контроль нескінченних циклів: переривання при перевищенні ліміту."""
    code = """
    begin
        while true do
            skip
    end
    """
    prog = parser.parse(code)
    limited_interpreter = Interpreter(step_limit=50)

    with pytest.raises(StepLimitExceededError):
        limited_interpreter.execute(prog)


def test_division_by_zero(parser, interpreter):
    """Помилка ділення на 0."""
    code = "begin X := 10 div 0 end"
    prog = parser.parse(code)

    with pytest.raises(DivisionByZeroError):
        interpreter.execute(prog)


def test_undefined_variable(parser, interpreter):
    """Помилка доступу до неініціалізованої змінної."""
    code = "begin X := Y + 1 end"
    prog = parser.parse(code)

    with pytest.raises(UndefinedVariableError):
        interpreter.execute(prog)
