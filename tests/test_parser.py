import pytest

from sipl.ast_nodes import Assign, If, Num, Program, RelOp, Seq, Skip, Var, While
from sipl.parser import SIPLParser, SIPLSyntaxError


@pytest.fixture
def parser():
    return SIPLParser()


def test_parse_power_ast_structure(parser):
    """Перевірка канонічної програми степеня з Практичної 1."""
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
    ast = parser.parse(code)

    assert isinstance(ast, Program)
    seq = ast.body
    assert isinstance(seq, Seq)
    assert len(seq.statements) == 2

    # Перший оператор: R := 1
    assign1 = seq.statements[0]
    assert isinstance(assign1, Assign)
    assert assign1.var == "R"
    assert isinstance(assign1.expr, Num)
    assert assign1.expr.value == 1

    # Другий оператор: While
    loop = seq.statements[1]
    assert isinstance(loop, While)
    assert isinstance(loop.cond, RelOp)
    assert loop.cond.op == ">"
    assert isinstance(loop.cond.left, Var) and loop.cond.left.name == "Y"
    assert isinstance(loop.cond.right, Num) and loop.cond.right.value == 0


def test_source_spans_present(parser):
    """Перевірка наявності точних координат рядків і колонок у вузлах."""
    code = "begin X := 42 end"
    ast = parser.parse(code)

    assert ast.span is not None
    assert ast.span.line == 1
    assert ast.span.column == 1

    assign = ast.body
    assert isinstance(assign, Assign)
    assert assign.span is not None
    assert assign.span.line == 1
    assert assign.span.column == 7
    assert assign.expr.span is not None
    assert assign.expr.span.line == 1


def test_syntax_error_with_coordinates(parser):
    """Перевірка генерації SIPLSyntaxError з точним рядком і колонкою."""
    bad_code = "begin X := 5; end"
    with pytest.raises(SIPLSyntaxError) as exc_info:
        parser.parse(bad_code)

    err = exc_info.value
    assert err.line == 1
    assert err.column > 0
    assert "Syntax Error" in str(err)


def test_syntax_error_eof_coordinates(parser):
    """Перевірка коректних координат при незакритому блоці на кінці файлу (EOF)."""
    code_without_end = "begin R := 1"
    with pytest.raises(SIPLSyntaxError) as exc_info:
        parser.parse(code_without_end)

    err = exc_info.value
    assert err.line >= 1
    assert err.column >= 1
    assert err.line != -1 and err.column != -1


def test_else_skip_semicolon_precedence(parser):
    """
    Перевірка пріоритету крапки з комою після else skip:
    S2 не повинно потрапляти всередину else!
    """
    code = "begin if X > 0 then Y := 1 else skip; Z := 2 end"
    ast = parser.parse(code)

    assert isinstance(ast.body, Seq)
    assert len(ast.body.statements) == 2

    # Перший оператор — це If
    first_stmt = ast.body.statements[0]
    assert isinstance(first_stmt, If)
    assert isinstance(first_stmt.else_branch, Skip)

    # Другий оператор — це Z := 2
    second_stmt = ast.body.statements[1]
    assert isinstance(second_stmt, Assign)
    assert second_stmt.var == "Z"
