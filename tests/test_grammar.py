import pytest
from lark import Lark, UnexpectedInput, UnexpectedToken

GRAMMAR_PATH = "grammar/sipl.lark"

@pytest.fixture(scope="module")
def parser():
    with open(GRAMMAR_PATH, "r", encoding="utf-8") as f:
        grammar = f.read()
    return Lark(grammar, parser="lalr", start="program")


# ==========================================================
# ПОЗИТИВНІ ТЕСТИ (≥10 прикладів згідно з БНФ курсу)
# ==========================================================
VALID_PROGRAMS = [
    # 1. Мінімальна програма: обов'язковий блок begin/end та оператор skip
    "begin skip end",

    # 2. Одне присвоювання
    "begin R := 1 end",

    # 3. Канонічна програма степеня x^y з практикуму (с. 10)
    """
    begin
        R := 1;
        while Y > 0 do
        begin
            R := R * X;
            Y := Y - 1
        end
    end
    """,

    # 4. Послідовність із трьох присвоювань (крапка з комою тільки між ними)
    "begin X := 5; Y := 10; Z := X + Y end",

    # 5. Умовне розгалуження з else skip
    "begin if X > 0 then Y := 1 else skip end",

    # 6. Вкладений блок begin ... end
    "begin A := 1; begin B := 2; C := 3 end; D := 4 end",

    # 7. Арифметика з div та mod (варіанти 2, 4, 15)
    "begin Q := A div B; Rem := A mod B end",

    # 8. Складна логічна умова з and, not та порівнянням
    "begin if not (X = 0) and Y > 0 then Z := 1 else Z := 0 end",

    # 9. Складені дужкові вирази в арифметиці
    "begin Ans := (X + Y) * (A - B) end",

    # 10. Алгоритм пошуку простоти числа (Варіант 15)
    """
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
    """,

    # 11. Програма з коментарями
    """
    // Головний блок
    begin
        /* Лічильник */
        I := 0;
        skip
    end
    """,

    # 12. Глибока вкладеність циклів і розгалужень
    """
    begin
        while A > 0 do
            if B > 0 then
                A := A - 1
            else
                B := B + 1
    end
    """
]

@pytest.mark.parametrize("code", VALID_PROGRAMS)
def test_valid_sipl_programs(parser, code):
    tree = parser.parse(code)
    assert tree is not None
    assert tree.data == "program"


# ==========================================================
# НЕГАТИВНІ ТЕСТИ (≥10 прикладів із синтаксичними помилками)
# ==========================================================
INVALID_PROGRAMS = [
    # 1. Відсутність обов'язкового begin/end для програми (P ::= begin S end)
    "R := 1",

    # 2. Зайва крапка з комою перед end (у БНФ курсу ';' це розділювач S1; S2)
    "begin R := 1; end",

    # 3. Незакритий блок begin
    "begin R := 1",

    # 4. If без обов'язкової гілки else (за БНФ: if b then S1 else S2)
    "begin if X > 0 then R := 1 end",

    # 5. Присвоювання через = замість :=
    "begin X = 5 end",

    # 6. Цикл while без ключового слова do
    "begin while X > 0 X := X - 1 end",

    # 7. Дві крапки з комою підряд (порожній оператор між ними)
    "begin X := 1; ; Y := 2 end",

    # 8. Бінарний арифметичний оператор без правого операнда
    "begin X := Y + end",

    # 9. Порівняння з некоректним оператором (== замість =)
    "begin if X == 0 then skip else skip end",

    # 10. Непарна дужка в арифметичному виразі
    "begin X := (A + B * C end",

    # 11. Порожня програма (відсутній текст)
    "",

    # 12. Оператор після завершення програми (після фінального end)
    "begin skip end; X := 1"
]

@pytest.mark.parametrize("code", INVALID_PROGRAMS)
def test_invalid_sipl_programs(parser, code):
    with pytest.raises((UnexpectedInput, UnexpectedToken)):
        parser.parse(code)
