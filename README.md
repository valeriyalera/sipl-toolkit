# SIPL Toolkit

![CI](https://github.com/valeriyalera/sipl-toolkit/actions/workflows/ci.yml/badge.svg?branch=main)

Інструментарій для аналізу, інтерпретації, трасування, візуалізації та побудови денотаційної семантики програм мовою **Simple Imperative Programming Language (SIPL)** (курс «Теорія програмування»).

---

## Обрані ID завдань та заявлена кількість балів

| ID завдання | Опис | Бали | Статус |
| :--- | :--- | :---: | :---: |
| **CORE-01** | Граматика Lark + 12 позитивних / 12 негативних тестів | **0.5** | Виконано |
| **CORE-02** | Парсер, типізоване AST, SourceSpan, діагностика | **1.5** | Виконано |
| **CORE-03** | Інтерпретатор, ліміт кроків | **2.0** | Виконано |
| **CORE-04** | Trace подій (CLI + JSON) | **1.0** | Виконано |
| **CORE-05** | CLI: parse / check / run / trace | **1.0** | Виконано |
| **VIS-01** | Дерево виводу: text / JSON / DOT / SVG | **1.5** | Виконано |
| **SEM-01** | Семантичний терм у нотації курсу | **2.0** | Виконано |
| **REL-01** | CI (GitHub Actions) | **0.5** | Виконано |
| **Разом** | | **10.0** | **Готово до здачі** |

---

## Структура проєкту

```text
sipl-toolkit/
├── .github/workflows/ci.yml   # REL-01: GitHub Actions CI (lint, mypy, pytest, build)
├── docs/
│   ├── cli.md                 # Документація команд CLI
│   └── lexics.md              # Опис лексики та синтаксису SIPL
├── examples/
│   ├── factorial.sipl         # Обчислення факторіала N!
│   ├── gcd.sipl               # Алгоритм Евкліда (вкладені while та if-else)
│   └── logic_branch.sipl      # Логічні вирази (not, and, or), div та skip
│   └── power.sipl             # Приклади програм мовою SIPL
├── grammar/
│   └── sipl.lark              # CORE-01: Формальна граматика SIPL
├── src/sipl/
│   ├── __init__.py
│   ├── __main__.py            # Точка входу python -m sipl
│   ├── ast_nodes.py           # CORE-02: Типізовані вузли AST та SourceSpan
│   ├── parser.py              # CORE-01, CORE-02: LALR-парсер і діагностика помилок
│   ├── interpreter.py         # CORE-03: Інтерпретатор і ліміт кроків
│   ├── tracer.py              # CORE-04: Трасувальник подій виконання
│   ├── cli.py                 # CORE-05: CLI (parse, check, run, trace, visualize, term)
│   ├── visualizer.py          # VIS-01: Візуалізація дерева виводу (text, JSON, DOT, SVG)
│   └── semantics.py           # SEM-01: Побудова семантичного терму в нотації курсу
├── tests/
│   ├── test_grammar.py        # Тести граматики (12 позитивних / 12 негативних)
│   ├── test_parser.py         # Тести парсера, AST, SourceSpan та діагностики
│   ├── test_interpreter.py    # Тести інтерпретатора, ліміту кроків та помилок
│   ├── test_tracer.py         # Тести трасувальника подій та JSON-виводу
│   ├── test_cli.py            # Тести CLI-команд та кодів повернення
│   ├── test_visualizer.py     # Тести дерева виводу (text, JSON, DOT, SVG)
│   └── test_semantics.py      # Тести побудови семантичних термів та децукрування
├── pyproject.toml             # Конфігурація пакета, ruff та mypy
└── pytest.ini                 # Налаштування pytest