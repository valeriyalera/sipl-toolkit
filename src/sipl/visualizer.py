from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from lark import Lark, Token, Tree

DEFAULT_GRAMMAR_PATH = Path(__file__).resolve().parent / "grammar" / "sipl.lark"

CATEGORY_MAP: Dict[str, str] = {
    "program": "P",
    "stmt": "S",
    "seq_stmt": "S",
    "single_stmt": "S",
    "assign_stmt": "S",
    "if_stmt": "S",
    "while_stmt": "S",
    "block_stmt": "S",
    "skip_stmt": "S",
    "a_expr": "Aexp",
    "a_term": "Aexp",
    "a_factor": "Aexp",
    "b_expr": "Bexp",
    "b_term": "Bexp",
    "b_factor": "Bexp",
    "rel_expr": "Bexp",
}

LABELS_BY_LANG: Dict[str, Dict[str, str]] = {
    "uk": {
        "P": "<програма>",
        "S": "<оператор>",
        "Aexp": "<вираз>",
        "Bexp": "<умова>",
        "Var": "<змінна>",
        "Num": "<число>",
    },
    "en": {
        "P": "P",
        "S": "S",
        "Aexp": "Aexp",
        "Bexp": "Bexp",
        "Var": "Var",
        "Num": "Num",
    },
}

VAR_TOKEN_TYPES = {"IDENT", "VAR", "NAME", "ID"}
NUM_TOKEN_TYPES = {"INT", "NUMBER", "NUM"}


def dot_escape(s: str) -> str:
    """Безпечне екранування для рядкових міток Graphviz label="..."."""
    cleaned = " ".join(s.splitlines())
    return cleaned.replace("\\", "\\\\").replace('"', '\\"')


def extract_source_slice(code: str, line: int, col: int, end_line: int, end_col: int) -> str:
    """Вирізає фрагмент вихідного тексту за 1-based координатами без переносів рядків."""
    lines = code.splitlines(keepends=True)
    if not (1 <= line <= len(lines)):
        return ""
    if line == end_line:
        cur_line = lines[line - 1]
        raw = cur_line[col - 1:end_col - 1].strip()
    else:
        first = lines[line - 1][col - 1:]
        middle = "".join(lines[line:end_line - 1])
        last = lines[end_line - 1][:end_col - 1] if end_line <= len(lines) else ""
        raw = (first + middle + last).strip()
    return re.sub(r"\s+", " ", raw)


@dataclass
class ParseNode:
    kind: str  # "NonTerminal" | "Terminal"
    category: str  # P, S, Aexp, Bexp, Var, Num або текст термінала
    source: str
    span: Dict[str, int]
    children: List["ParseNode"] = field(default_factory=list)
    leaf_index: Optional[int] = None


class ParseTreeVisualizer:
    """
    Будує та візуалізує канонічне дерево синтаксичного виводу згідно з БНФ курсу
    'Теорія програмування' (Рис. 1 практичної роботи №2).
    """

    def __init__(
        self,
        code: str,
        grammar_path: Path = DEFAULT_GRAMMAR_PATH,
        lang: str = "uk",
    ):
        if lang not in LABELS_BY_LANG:
            raise ValueError(f"Unsupported language '{lang}'. Choose 'uk' or 'en'.")
        self.code = code
        self.lang = lang
        self.raw_cst = self._build_cst(grammar_path, code)
        self.root = self._normalize_tree(self.raw_cst)
        self._number_leaves(self.root)

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

    def _display_name(self, node: ParseNode) -> str:
        if node.kind == "Terminal":
            return node.category
        return LABELS_BY_LANG[self.lang].get(node.category, node.category)

    def _normalize_tree(self, item: Tree | Token) -> ParseNode:
        if isinstance(item, Token):
            span = {
                "line": item.line or 0,
                "column": item.column or 0,
                "end_line": item.end_line or 0,
                "end_column": item.end_column or 0,
            }
            val = str(item.value)
            term_node = ParseNode(
                kind="Terminal",
                category=val,
                source=val,
                span=span,
            )
            if item.type in VAR_TOKEN_TYPES:
                return ParseNode(
                    kind="NonTerminal",
                    category="Var",
                    source=val,
                    span=span,
                    children=[term_node],
                )
            if item.type in NUM_TOKEN_TYPES:
                return ParseNode(
                    kind="NonTerminal",
                    category="Num",
                    source=val,
                    span=span,
                    children=[term_node],
                )
            return term_node

        assert isinstance(item, Tree)
        rule_name = str(item.data)
        category = CATEGORY_MAP.get(rule_name, rule_name)
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

        norm_children = [self._normalize_tree(ch) for ch in item.children]

        # Бінаризація послідовності операторів з лівою вкладеністю: S -> S1 ; S2
        if rule_name == "seq_stmt" and len(norm_children) > 3:
            acc = ParseNode(
                kind="NonTerminal",
                category="S",
                source=f"{norm_children[0].source} ; {norm_children[2].source}",
                span={
                    "line": norm_children[0].span["line"],
                    "column": norm_children[0].span["column"],
                    "end_line": norm_children[2].span["end_line"],
                    "end_column": norm_children[2].span["end_column"],
                },
                children=norm_children[:3],
            )
            idx = 3
            while idx + 1 < len(norm_children):
                semi = norm_children[idx]
                rhs = norm_children[idx + 1]
                acc = ParseNode(
                    kind="NonTerminal",
                    category="S",
                    source=f"{acc.source} ; {rhs.source}",
                    span={
                        "line": acc.span["line"],
                        "column": acc.span["column"],
                        "end_line": rhs.span["end_line"],
                        "end_column": rhs.span["end_column"],
                    },
                    children=[acc, semi, rhs],
                )
                idx += 2
            node = acc
        else:
            node = ParseNode(
                kind="NonTerminal",
                category=category,
                source=source,
                span=span,
                children=norm_children,
            )

        # Схлопування унарних ланцюжків однакових категорій (Aexp -> Aexp -> Num => Aexp -> Num)
        while (
            node.kind == "NonTerminal"
            and len(node.children) == 1
            and node.children[0].kind == "NonTerminal"
            and node.children[0].category == node.category
        ):
            child = node.children[0]
            node = ParseNode(
                kind="NonTerminal",
                category=node.category,
                source=node.source or child.source,
                span=node.span,
                children=child.children,
            )

        return node

    def _number_leaves(self, node: ParseNode) -> None:
        counter = 1

        def walk(curr: ParseNode) -> None:
            nonlocal counter
            if curr.kind == "Terminal":
                curr.leaf_index = counter
                counter += 1
                return
            for ch in curr.children:
                walk(ch)

        walk(node)

    def get_leaves(self) -> List[ParseNode]:
        leaves: List[ParseNode] = []

        def walk(curr: ParseNode) -> None:
            if curr.kind == "Terminal":
                leaves.append(curr)
                return
            for ch in curr.children:
                walk(ch)

        walk(self.root)
        return leaves

    def to_text(self, show_spans: bool = False) -> str:
        lines: List[str] = []
        self._build_text(self.root, prefix="", is_last=True, lines=lines, show_spans=show_spans)
        return "\n".join(lines)

    def _build_text(
        self,
        node: ParseNode,
        prefix: str,
        is_last: bool,
        lines: List[str],
        show_spans: bool,
    ) -> None:
        connector = "└── " if is_last else "├── "
        span_str = f" [{node.span['line']}:{node.span['column']}]" if show_spans else ""
        disp = self._display_name(node)

        if node.kind == "Terminal":
            label = f"[{node.leaf_index}] '{disp}'{span_str}"
        else:
            src_clean = " ".join(node.source.splitlines())
            src_preview = (
                f' "{src_clean[:24]}..."'
                if len(src_clean) > 24
                else f' "{src_clean}"'
            )
            label = f"{disp}{src_preview}{span_str}"

        lines.append(f"{prefix}{connector}{label}")

        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(node.children):
            self._build_text(child, child_prefix, i == len(node.children) - 1, lines, show_spans)

    def to_json_dict(self, node: Optional[ParseNode] = None) -> Dict[str, Any]:
        curr = node if node is not None else self.root
        res: Dict[str, Any] = {
            "kind": curr.kind,
            "category": curr.category,
            "name": self._display_name(curr),
            "source": curr.source,
            "span": curr.span,
        }
        if curr.kind == "Terminal":
            res["leaf_index"] = curr.leaf_index
        else:
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

        def traverse(curr: ParseNode) -> int:
            nonlocal node_id
            curr_id = node_id
            node_id += 1

            disp = dot_escape(self._display_name(curr))
            if curr.kind == "Terminal":
                label = f"[{curr.leaf_index}] {disp}"
                style = 'fillcolor="#F3F4F6", color="#6B7280", fontcolor="#111827", shape=ellipse'
            else:
                src = dot_escape(curr.source)
                if len(src) > 26:
                    src = src[:23] + "..."
                label = f"{disp}\\n\\\"{src}\\\""
                style = 'fillcolor="#EFF6FF", color="#3B82F6", fontcolor="#1E3A8A"'

            dot_lines.append(f'    n{curr_id} [label="{label}" {style}];')

            for ch in curr.children:
                cid = traverse(ch)
                dot_lines.append(f"    n{curr_id} -> n{cid};")

            return curr_id

        traverse(self.root)
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


# Аліас для зворотної сумісності
TreeVisualizer = ParseTreeVisualizer
