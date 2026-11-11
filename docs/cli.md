# SIPL Toolkit CLI Documentation

Запуск інструменту:
`python -m sipl <command> [options]`

## Коди завершення (Exit Codes)
| Код | Опис |
| :---: | :--- |
| `0` | **EXIT_OK** — успішне виконання команди. |
| `1` | **EXIT_SYNTAX_ERROR** — синтаксична помилка парсингу файлу. |
| `2` | **EXIT_RUNTIME_ERROR** — помилка під час виконання (ділення на 0, ліміт кроків тощо). |
| `3` | **EXIT_USAGE_ERROR** — файл не знайдено або невалідний формат вхідних аргументів (`--state`). |

## Команди та формати JSON

### 1. `check`
* `python -m sipl check file.sipl --json`
* **JSON успіху:** `{"status": "ok", "file": "path"}`
* **JSON помилки:** `{"status": "error", "error_type": "...", "message": "...", "line": 1, "column": 5}`

### 2. `parse`
* `python -m sipl parse file.sipl --json`
* **JSON успіху:** `{"status": "ok", "ast": { "type": "Program", ... }}`

### 3. `run`
* `python -m sipl run file.sipl --state "X=2,Y=5" --json`
* **JSON успіху:** `{"status": "ok", "final_state": {"X": 2, ...}, "steps": 12}`

### 4. `trace`
* `python -m sipl trace file.sipl --state "X=2" --max-events 100 --json`
* **JSON успіху:** `{"status": "ok", "events": [...], "total_events": 45, "truncated": false}`

### 5. `visualize`
Візуалізує дерево синтаксичного виводу / AST у форматах `text`, `json`, `dot`.
* `python -m sipl visualize examples/power.sipl` (текстове дерево в консолі)
* `python -m sipl visualize examples/power.sipl --format dot -o ast.dot` (генерація Graphviz)
* `python -m sipl visualize examples/power.sipl --format json` (ієрархічний JSON)