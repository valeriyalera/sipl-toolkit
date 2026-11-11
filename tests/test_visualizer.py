import json
import re
import shutil

import pytest

from sipl.cli import EXIT_USAGE_ERROR, main
from sipl.visualizer import ParseTreeVisualizer, dot_escape


def test_dot_escape_does_not_use_html_entities():
    """Екранування для DOT не повинно перетворювати > на &gt;"""
    raw = 'while Y > 0 and X <= 5 do "test"'
    escaped = dot_escape(raw)
    assert "&gt;" not in escaped
    assert "&lt;" not in escaped
    assert ">" in escaped
    assert "<=" in escaped
    assert '\\"test\\"' in escaped


def test_parse_tree_derivation_chain():
    """Перевірка ланцюжка виведення нетерміналів Aexp -> Aterm -> Afactor."""
    code = "begin X := 1 + 2 * 3 end"
    vis = ParseTreeVisualizer(code)
    text = vis.to_text()

    assert "Aexp" in text
    assert "Aterm" in text
    assert "Afactor" in text
    assert "Token('1')" in text
    assert "Token('+')" in text


def test_parse_tree_json_and_source_attachment():
    """Перевірка прив'язки source і span до кожного вузла."""
    code = "begin skip end"
    vis = ParseTreeVisualizer(code)
    data = json.loads(vis.to_json())

    assert data["kind"] == "NonTerminal"
    assert "source" in data
    assert data["source"] == "begin skip end"
    assert "span" in data

    children = data["children"]
    token_names = [ch["name"] for ch in children if ch["kind"] == "Terminal"]
    assert "begin" in token_names
    assert "end" in token_names


def test_parse_tree_dot_nodes_match_json():
    """Кількість оголошень nX [ у DOT відповідає загальній кількості вузлів у JSON."""
    code = "begin if X > 0 then Y := 1 else skip end"
    vis = ParseTreeVisualizer(code)
    dot = vis.to_dot()
    json_data = json.loads(vis.to_json())

    def count_nodes(n):
        return 1 + sum(count_nodes(c) for c in n.get("children", []))

    total_nodes = count_nodes(json_data)
    dot_node_declarations = [
        line for line in dot.splitlines()
        if re.match(r"^\s*n\d+\s*\[", line)
    ]
    assert len(dot_node_declarations) == total_nodes

@pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz 'dot' utility is not installed")
def test_parse_tree_svg_generation():
    code = "begin R := 1 end"
    vis = ParseTreeVisualizer(code)
    svg = vis.to_svg()
    assert svg.strip().startswith("<?xml") or "<svg" in svg


def test_cli_visualize_output_error_handling(tmp_path):
    f = tmp_path / "prog.sipl"
    f.write_text("begin skip end", encoding="utf-8")
    bad_dir_target = "/proc/invalid_path/out.dot"
    ret = main(["visualize", str(f), "--format", "dot", "-o", bad_dir_target])
    assert ret == EXIT_USAGE_ERROR
