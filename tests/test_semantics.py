import json

import pytest

from sipl.cli import EXIT_OK, main
from sipl.parser import SIPLParser
from sipl.semantics import SemanticTermBuilder, TermFormatter


@pytest.fixture
def parser():
    return SIPLParser()


@pytest.fixture
def builder():
    return SemanticTermBuilder()


def test_golden_power_semantic_term_ascii(parser, builder):
    """
    Golden-тест за посібником (с. 16):
    AS^R(1_bar) . WH(S^2(gr, Y=>, 0_bar), AS^R(S^2(mult, R=>, X=>)) . AS^Y(S^2(sub, Y=>, 1_bar)))
    """
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
    term = builder.build(ast)
    formatter = TermFormatter(ascii_mode=True)
    res = formatter.format(term)

    expected = (
        "AS^R(1_bar) . WH(S^2(gr, Y=>, 0_bar), "
        "AS^R(S^2(mult, R=>, X=>)) . AS^Y(S^2(sub, Y=>, 1_bar)))"
    )
    assert res == expected


def test_golden_power_semantic_term_unicode(parser, builder):
    """Golden-тест у канонічному юнікоді практикуму (AS^R(1̄) · WH(...))."""
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
    term = builder.build(ast)
    formatter = TermFormatter(ascii_mode=False)
    res = formatter.format(term)

    assert "AS^R(1\u0304)" in res
    assert " \u00b7 " in res
    assert "Y\u21d2" in res
    assert "0\u0304" in res


def test_all_base_operators_coverage(parser, builder):
    """Покриття всіх базових операторів: skip, if, +, -, *, =, >, or, not."""
    code = """
    begin
        skip;
        if not (X = 0) or Y > 0 then
            Z := X + Y - 1
        else
            Z := X * 2
    end
    """
    ast = parser.parse(code)
    term = builder.build(ast)
    formatter = TermFormatter(ascii_mode=True)
    out = formatter.format(term)

    assert "id ." in out
    assert "IF(" in out
    assert "S^1(neg, S^2(eq, X=>, 0_bar))" in out
    assert "S^2(gr, Y=>, 0_bar)" in out
    assert "AS^Z(S^2(sub, S^2(add, X=>, Y=>), 1_bar))" in out
    assert "AS^Z(S^2(mult, X=>, 2_bar))" in out


def test_desugaring_expansions(parser, builder):
    """Зведення додаткових операторів (<, !=, and) до ядра."""
    formatter = TermFormatter(ascii_mode=True)

    # a < b -> S^2(gr, b, a)
    t_less = builder.build(parser.parse("begin if A < B then skip else skip end"))
    assert "S^2(gr, B=>, A=>)" in formatter.format(t_less)

    # a != b -> S^1(neg, S^2(eq, a, b))
    t_neq = builder.build(parser.parse("begin if A != B then skip else skip end"))
    assert "S^1(neg, S^2(eq, A=>, B=>))" in formatter.format(t_neq)

    # a and b -> S^1(neg, S^2(or, S^1(neg, a), S^1(neg, b)))
    t_and = builder.build(parser.parse("begin if A > 0 and B > 0 then skip else skip end"))
    res_and = formatter.format(t_and)
    assert "S^1(neg, S^2(or, S^1(neg, S^2(gr, A=>, 0_bar)), S^1(neg, S^2(gr, B=>, 0_bar))))" in res_and


def test_cli_term_execution(tmp_path, capsys):
    """Перевірка команди CLI sipl term."""
    f = tmp_path / "simple.sipl"
    f.write_text("begin X := 5; skip end", encoding="utf-8")

    # ASCII вивід
    assert main(["term", str(f), "--ascii"]) == EXIT_OK
    assert "AS^X(5_bar) . id" in capsys.readouterr().out

    # JSON вивід структурованого терму
    assert main(["term", str(f), "--json"]) == EXIT_OK
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["term"]["name"] == "compose"
