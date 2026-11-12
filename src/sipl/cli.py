import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, cast

from .ast_nodes import Program, ast_to_dict
from .interpreter import Interpreter, SIPLRuntimeError
from .parser import SIPLParser, SIPLSyntaxError
from .semantics import SemanticTermBuilder, TermFormatter
from .tracer import ExecutionTracer
from .visualizer import ParseTreeVisualizer

EXIT_OK = 0
EXIT_SYNTAX_ERROR = 1
EXIT_RUNTIME_ERROR = 2
EXIT_USAGE_ERROR = 3


def parse_state_arg(state_str: str) -> Dict[str, int]:
    """Парсить стан змінних. При помилці кидає ValueError."""
    if not state_str:
        return {}
    state_str = state_str.strip()
    if state_str.startswith("{"):
        try:
            parsed = json.loads(state_str)
            if not isinstance(parsed, dict):
                raise ValueError("JSON state must be an object (dictionary).")
            return {str(k): int(v) for k, v in parsed.items()}
        except Exception as e:
            raise ValueError(f"Invalid JSON in --state: {e}") from e

    res = {}
    for part in state_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Invalid key-value format in --state: '{part}'. Expected 'Var=Value'.")
        k, v = part.split("=", 1)
        k = k.strip()
        try:
            res[k] = int(v.strip())
        except ValueError:
            raise ValueError(f"Invalid integer value for variable '{k}': '{v.strip()}'.")
    return res


def load_and_parse(file_path_str: str, as_json: bool) -> Tuple[Optional[Program], Optional[str], int]:
    """Універсальний хелпер: зчитує файл і парсить AST. Повертає (ast, code_text, exit_code)."""
    path = Path(file_path_str)
    if not path.exists():
        msg = f"File not found: {path}"
        if as_json:
            print(json.dumps({"status": "error", "error_type": "FileNotFound", "message": msg}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return None, None, EXIT_USAGE_ERROR

    code = path.read_text(encoding="utf-8")
    parser = SIPLParser()
    try:
        ast = parser.parse(code)
        return ast, code, EXIT_OK
    except SIPLSyntaxError as e:
        if as_json:
            print(json.dumps({
                "status": "error",
                "error_type": "SIPLSyntaxError",
                "line": e.line,
                "column": e.column,
                "message": e.message
            }))
        else:
            print(f"Syntax Error in {path} at line {e.line}, column {e.column}: {e.message}", file=sys.stderr)
        return None, code, EXIT_SYNTAX_ERROR


def cmd_check(args) -> int:
    ast, _, exit_code = load_and_parse(args.file, args.json)
    if exit_code != EXIT_OK:
        return exit_code

    if args.json:
        print(json.dumps({"status": "ok", "file": str(args.file)}))
    else:
        print(f"Syntax OK: {args.file}")
    return EXIT_OK


def cmd_parse(args) -> int:
    ast, _, exit_code = load_and_parse(args.file, args.json)
    if exit_code != EXIT_OK or ast is None:
        return exit_code

    if args.json:
        print(json.dumps({"status": "ok", "ast": ast_to_dict(ast)}, indent=2, ensure_ascii=False))
    else:
        print(ast)
    return EXIT_OK


def cmd_run(args) -> int:
    try:
        initial_state = parse_state_arg(args.state) if args.state else {}
    except ValueError as e:
        if args.json:
            print(json.dumps({"status": "error", "error_type": "InvalidStateError", "message": str(e)}))
        else:
            print(f"Input Error: {e}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    ast, _, exit_code = load_and_parse(args.file, args.json)
    if exit_code != EXIT_OK or ast is None:
        return exit_code

    interpreter = Interpreter(step_limit=args.step_limit)
    try:
        final_state = interpreter.execute(ast, initial_state=initial_state)
        if args.json:
            print(json.dumps({
                "status": "ok",
                "final_state": final_state,
                "steps": interpreter.step_count
            }, indent=2))
        else:
            print("Execution finished successfully.")
            print(f"Final State: {final_state}")
            print(f"Steps: {interpreter.step_count}")
        return EXIT_OK
    except SIPLRuntimeError as e:
        if args.json:
            print(json.dumps({
                "status": "error",
                "error_type": type(e).__name__,
                "message": str(e),
                "steps": interpreter.step_count,
                "state": interpreter.state
            }))
        else:
            print(f"Runtime Error: {type(e).__name__} -> {e}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR


def cmd_trace(args) -> int:
    try:
        initial_state = parse_state_arg(args.state) if args.state else {}
    except ValueError as e:
        if args.json:
            print(json.dumps({"status": "error", "error_type": "InvalidStateError", "message": str(e)}))
        else:
            print(f"Input Error: {e}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    ast, _, exit_code = load_and_parse(args.file, args.json)
    if exit_code != EXIT_OK or ast is None:
        return exit_code

    tracer = ExecutionTracer(max_events=args.max_events)
    interpreter = Interpreter(step_limit=args.step_limit, tracer=tracer)

    runtime_error = None
    try:
        interpreter.execute(ast, initial_state=initial_state)
    except SIPLRuntimeError as e:
        runtime_error = e

    if args.json:
        data = tracer.to_dict()
        if runtime_error:
            data["status"] = "error"
            data["error_type"] = type(runtime_error).__name__
            data["message"] = str(runtime_error)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        for ev in tracer.events:
            print(f"[{ev.event_index:03d}] {ev.event_type:<16} | state={ev.state} | {ev.details}")
        if tracer.is_truncated:
            print(f"\n[Warning] Events limit exceeded ({args.max_events}). Trace was truncated.", file=sys.stderr)
        if runtime_error:
            print(f"\nExecution terminated with error: {runtime_error}", file=sys.stderr)

    return EXIT_RUNTIME_ERROR if runtime_error else EXIT_OK


def cmd_visualize(args) -> int:
    path = Path(args.file)
    if not path.exists():
        msg = f"File not found: {path}"
        if args.format == "json":
            print(json.dumps({"status": "error", "error_type": "FileNotFound", "message": msg}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    code = path.read_text(encoding="utf-8")
    try:
        visualizer = ParseTreeVisualizer(code, lang=args.lang)
    except Exception as e:
        if args.format == "json":
            print(json.dumps({"status": "error", "error_type": "ParseTreeError", "message": str(e)}))
        else:
            print(f"Syntax/Parse Error: {e}", file=sys.stderr)
        return EXIT_SYNTAX_ERROR

    fmt = args.format.lower()
    try:
        if fmt == "json":
            res = visualizer.to_json(indent=2)
        elif fmt == "dot":
            res = visualizer.to_dot()
        elif fmt == "svg":
            res = visualizer.to_svg()
        else:
            res = visualizer.to_text(show_spans=args.spans)
    except RuntimeError as e:
        if fmt == "json":
            print(json.dumps({"status": "error", "error_type": "RuntimeError", "message": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    if args.output:
        try:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(res, encoding="utf-8")
            if fmt != "json":
                print(f"Parse tree successfully saved to {out_path}")
        except OSError as e:
            print(f"File write error: {e}", file=sys.stderr)
            return EXIT_USAGE_ERROR
    else:
        print(res)

    return EXIT_OK


def cmd_term(args) -> int:
    ast, _, exit_code = load_and_parse(args.file, as_json=args.json)
    if exit_code != EXIT_OK or ast is None:
        return exit_code

    builder = SemanticTermBuilder()
    try:
        term = builder.build(ast)
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "error_type": "SemanticTermError", "message": str(e)}))
        else:
            print(f"Semantic Error: {e}", file=sys.stderr)
        return EXIT_RUNTIME_ERROR

    if args.json:
        print(json.dumps({"status": "ok", "term": term.to_dict()}, indent=2, ensure_ascii=False))
    else:
        formatter = TermFormatter(ascii_mode=args.ascii)
        print(formatter.format(term))

    return EXIT_OK


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sipl", description="SIPL Language Toolkit CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = subparsers.add_parser("check", help="Check syntax of a SIPL file")
    p_check.add_argument("file", help="Path to .sipl file")
    p_check.add_argument("--json", action="store_true", help="Output result as JSON")
    p_check.set_defaults(func=cmd_check)

    # parse
    p_parse = subparsers.add_parser("parse", help="Parse SIPL file to AST")
    p_parse.add_argument("file", help="Path to .sipl file")
    p_parse.add_argument("--json", action="store_true", help="Output AST as JSON")
    p_parse.set_defaults(func=cmd_parse)

    # run
    p_run = subparsers.add_parser("run", help="Execute a SIPL file")
    p_run.add_argument("file", help="Path to .sipl file")
    p_run.add_argument("--state", type=str, default="", help="Initial state: 'X=2,Y=5' or '{\"X\": 2}'")
    p_run.add_argument("--step-limit", type=int, default=100000, help="Max steps limit")
    p_run.add_argument("--json", action="store_true", help="Output final state and steps as JSON")
    p_run.set_defaults(func=cmd_run)

    # trace
    p_trace = subparsers.add_parser("trace", help="Trace execution events")
    p_trace.add_argument("file", help="Path to .sipl file")
    p_trace.add_argument("--state", type=str, default="", help="Initial state")
    p_trace.add_argument("--step-limit", type=int, default=10000, help="Max steps limit")
    p_trace.add_argument("--max-events", type=int, default=5000, help="Max recorded events")
    p_trace.add_argument("--json", action="store_true", help="Output event trace as JSON")
    p_trace.set_defaults(func=cmd_trace)

    # visualize
    p_vis = subparsers.add_parser("visualize", help="Visualize parse tree (text, json, dot, svg)")
    p_vis.add_argument("file", help="Path to .sipl file")
    p_vis.add_argument(
        "--format",
        choices=["text", "json", "dot", "svg"],
        default="text",
        help="Visualization format (default: text)"
    )
    p_vis.add_argument("--lang", choices=["uk", "en"], default="uk", help="Non-terminal label language (default: uk)")
    p_vis.add_argument("--spans", action="store_true", help="Include coordinates in text mode")
    p_vis.add_argument("-o", "--output", help="Save output to file")
    p_vis.set_defaults(func=cmd_visualize)

    # term
    p_term = subparsers.add_parser("term", help="Build semantic term (Practical Work #2 notation)")
    p_term.add_argument("file", help="Path to .sipl file")
    p_term.add_argument("--ascii", action="store_true", help="Output in ASCII notation (n_bar, x=>, .)")
    p_term.add_argument("--json", action="store_true", help="Output term AST as JSON")
    p_term.set_defaults(func=cmd_term)

    args = parser.parse_args(argv)
    return cast(int, args.func(args))


if __name__ == "__main__":
    sys.exit(main())
