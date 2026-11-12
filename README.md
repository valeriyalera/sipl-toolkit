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
## Встановлення
    git clone https://github.com/valeriyalera/sipl-toolkit.git
    cd sipl-toolkit
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    pytest

## Використання
    sipl check examples/power.sipl
    sipl run examples/power.sipl --state "X=2,Y=5"
    sipl trace examples/power.sipl --state "X=2,Y=2" --json
    sipl visualize examples/power.sipl --format svg -o tree.svg
    sipl term examples/power.sipl
    
## Архітектура

```text
текст (.sipl) → Lark LALR(1) → CST ──► ParseTreeVisualizer (дерево виводу: text / JSON / DOT / SVG)
                                │
                                ▼ ASTBuilder
                         AST + SourceSpan
                                │
                                ├─► SemanticTermBuilder (семантичний терм: id / AS / · / IF / WH)
                                ├─► Interpreter (--step-limit)
                                ├─► ExecutionTracer (покрокові події)
                                └─► CLI (--json + коди завершення 0..3)
```

## Мова: ядро та розширення
- **Ядро (БНФ курсу):** `begin/end`, `:=`, `;`, `if-then-else`, `while-do`, `skip`, `+`, `-`, `*`, `=`, `>`, `∨`, `¬`.
- **Розширення:** `div`, `mod`, `<`, `<=`, `>=`, `!=`, `and`, `true/false`, коментарі, багатолітерні змінні. У семантичному терміні вони зводяться до ядра.
- `;` — роздільник, а не термінатор; `if` завжди з `else`; `*` має вищий пріоритет за `+`/`-`, асоціативність ліва.

## Коди завершення
| Код | Значення |
|---|---|
| 0 | успіх |
| 1 | синтаксична помилка |
| 2 | помилка виконання (ділення на 0, невизначена змінна, ліміт кроків) |
| 3 | помилка вводу (файл, `--state`) |

## Обмеження
- Нескінченний цикл переривається через `--step-limit`; зупинку не розв'язуємо.
- Читання неініціалізованої змінної — помилка.
- `and`/`or` обчислюються ліниво.
- `div`/`mod` працюють як floor-ділення Python.
- Для SVG потрібен Graphviz (`brew install graphviz`).

## Приклади
Валідні програми лежать у `examples/`; некоректні програми для перевірки `check` — у `tests/test_grammar.py`.

## Структура проєкту

```text
sipl-toolkit/
├── .github/workflows/ci.yml   # REL-01: GitHub Actions CI (lint, mypy, pytest, build)
├── docs/
│   ├── cli.md                 # Документація команд CLI
│   ├── lexics.md              # Опис лексики та синтаксису SIPL
│   └── power_tree.svg
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
