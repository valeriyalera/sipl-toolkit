from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from lark import Lark, Token, Tree

DEFAULT_GRAMMAR_PATH = Path(__file__).resolve().parent / "grammar" / "sipl.lark"

NON_TERMINAL_MAP = {
    "program": "P",
    "stmt": "S",
    "seq_stmt": "S",
    "single_stmt": "S",
    "assign_stmt": "S_assign",
    "if_stmt": "S_if",
    "while_stmt": "S_while",
    "block_stmt": "S_block",
    "skip_stmt": "S_skip",
    "a_expr": "Aexp",
    "a_term": "Aterm",
    "a_factor": "Afactor",
    "b_expr": "Bexp",
    "b_term": "Bterm",
    "b_factor": "Bfactor",
    "rel_expr": "RelExpr",
}


def dot_escape(s: str) -> str:
    """Безпечне екранування для рядкових міток Graphviz label="..."."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def extract_source_slice(code: str, line: int, col: int, end_line: int, end_col: int) -> str:
    """Вирізає фрагмент вихідного тексту за 1-based координатами."""
    lines = code.splitlines(keepends=True)
    if not (1 <= line <= len(lines)):
        return ""
    if line == end_line:
        cur_line = lines[line - 1]
        return cur_line[col - 1:end_col - 1].strip()

    first = lines[line - 1][col - 1:]
    middle = "".join(lines[line:end_line - 1])
    last = lines[end_line - 1][:end_col - 1] if end_line <= len(lines) else ""
    return (first + middle + last).strip()


class ParseTreeVisualizer:
    """
    Будує та візуалізує повне конкретне дерево синтаксичного виводу (Parse Tree / CST)
    згідно з правилами виведення курсу 'Теорія програмування'.
    """

    def __init__(self, code: str, grammar_path: Path = DEFAULT_GRAMMAR_PATH):
        self.code = code
        self.raw_cst = self._build_cst(grammar_path, code)

    def _build_cst(self, grammar_path: Path, code: str) -> Tree:
        grammar_text = grammar_path.read_text(encoding="utf-8")
        cst_grammar = re.sub(r"^\s*\?([a-zA-Z_]+:)", r"\1", grammar_text, flags=re.MULTILINE)
        cst_grammar = re.sub(r"->\s*[a-zA-Z_]+", "", cst_grammar)

        parser = Lark(
            cst_grammar,
            parser="lalr",
            start="program",
            keep_all_tokens=True,
            propagate_positions=True,
        )
        return parser.parse(code)

    def _get_node_info(self, item: Tree | Token) -> Dict[str, Any]:
        if isinstance(item, Tree):
            name = NON_TERMINAL_MAP.get(str(item.data), str(item.data))
            meta = item.meta
            span = {
                "line": meta.line,
                "column": meta.column,
                "end_line": meta.end_line,
                "end_column": meta.end_column,
            }
            source = extract_source_slice(
                self.code, meta.line, meta.column, meta.end_line, meta.end_column
            )
            return {"kind": "NonTerminal", "name": name, "span": span, "source": source}

        assert isinstance(item, Token)
        span = {
            "line": item.line or 0,
            "column": item.column or 0,
            "end_line": item.end_line or 0,
            "end_column": item.end_column or 0,
        }
        return {"kind": "Terminal", "name": str(item.value), "span": span, "source": str(item.value)}

    def to_text(self, show_spans: bool = False) -> str:
        lines: List[str] = []
        self._build_text(self.raw_cst, prefix="", is_last=True, lines=lines, show_spans=show_spans)
        return "\n".join(lines)

    def _build_text(
        self,
        item: Tree | Token,
        prefix: str,
        is_last: bool,
        lines: List[str],
        show_spans: bool,
    ) -> None:
        info = self._get_node_info(item)
        connector = "└── " if is_last else "├── "
        span_str = f" [{info['span']['line']}:{info['span']['column']}]" if show_spans else ""

        if info["kind"] == "Terminal":
            label = f"Token('{info['name']}'){span_str}"
        else:
            src_preview = (
                f' "{info["source"][:20]}..."'
                if len(info["source"]) > 20
                else f' "{info["source"]}"'
            )
            label = f"{info['name']}{src_preview}{span_str}"

        lines.append(f"{prefix}{connector}{label}")

        if isinstance(item, Tree):
            children = item.children
            child_prefix = prefix + ("    " if is_last else "│   ")
            for i, child in enumerate(children):
                self._build_text(child, child_prefix, i == len(children) - 1, lines, show_spans)

    def to_json_dict(self, item: Optional[Tree | Token] = None) -> Dict[str, Any]:
        curr = item if item is not None else self.raw_cst
        info = self._get_node_info(curr)
        res: Dict[str, Any] = {
            "kind": info["kind"],
            "name": info["name"],
            "source": info["source"],
            "span": info["span"],
        }
        if isinstance(curr, Tree):
            res["children"] = [self.to_json_dict(ch) for ch in curr.children]
        return res

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_json_dict(), indent=indent, ensure_ascii=False)

    def to_dot(self) -> str:
        dot_lines = [
            "digraph SIPL_ParseTree {",
            "    rankdir=TB;",
            '    node [fontname="Helvetica", fontsize=10, shape=box, style="filled,rounded", penwidth=1.2];',
            '    edge [fontname="Helvetica", fontsize=8, color="#555555"];',
            "",
        ]

        node_id = 0

        def traverse(item: Tree | Token) -> int:
            nonlocal node_id
            curr_id = node_id
            node_id += 1

            info = self._get_node_info(item)
            if info["kind"] == "Terminal":
                val = dot_escape(info["name"])
                label = f"Terminal\\n'{val}'"
                style = 'fillcolor="#F3F4F6", color="#6B7280", fontcolor="#111827", shape=ellipse'
            else:
                src = dot_escape(info["source"])
                if len(src) > 24:
                    src = src[:21] + "..."
                label = f"{info['name']}\\n\\\"{src}\\\""
                style = 'fillcolor="#EFF6FF", color="#3B82F6", fontcolor="#1E3A8A"'

            dot_lines.append(f'    n{curr_id} [label="{label}" {style}];')

            if isinstance(item, Tree):
                for ch in item.children:
                    cid = traverse(ch)
                    dot_lines.append(f"    n{curr_id} -> n{cid};")

            return curr_id

        traverse(self.raw_cst)
        dot_lines.append("}")
        return "\n".join(dot_lines)

    def to_svg(self) -> str:
        dot_code = self.to_dot()
        if shutil.which("dot") is None:
            raise RuntimeError(
                "Graphviz utility 'dot' is not installed or not in PATH. Run 'brew install graphviz' on macOS."
            )
        proc = subprocess.run(
            ["dot", "-Tsvg"],
            input=dot_code,
            text=True,
            capture_output=True,
            check=True,
        )
        return proc.stdout


# Аліас для зворотної сумісності з попередніми тестами
TreeVisualizer = ParseTreeVisualizer
