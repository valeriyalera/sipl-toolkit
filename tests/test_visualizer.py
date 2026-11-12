import json
import re
import shutil
from pathlib import Path

import pytest

from sipl.cli import EXIT_USAGE_ERROR, main
from sipl.visualizer import ParseTreeVisualizer, dot_escape


def test_dot_escape_does_not_use_html_entities():
    """Екранування для DOT не повинно перетворювати > на &gt; та не містити переносів рядків."""
    raw = 'while Y > 0 and X <= 5 do\n"test"'
    escaped = dot_escape(raw)
    assert "&gt;" not in escaped
    assert "&lt;" not in escaped
    assert "\n" not in escaped
    assert ">" in escaped
    assert "<=" in escaped
    assert '\\"test\\"' in escaped


def test_parse_tree_canonical_categories_and_collapsed_chains():
    """Перевірка канонічних категорій курсу без внутрішніх вузлів LALR (Aterm, Afactor, S_assign)."""
    code = "begin X := 1 + 2 * 3 end"
    vis_uk = ParseTreeVisualizer(code, lang="uk")
    text_uk = vis_uk.to_text()

    assert "<програма>" in text_uk
    assert "<оператор>" in text_uk
    assert "<вираз>" in text_uk
    assert "<змінна>" in text_uk
    assert "<число>" in text_uk
    for internal_name in ("Aterm", "Afactor", "S_assign", "Bterm", "Bfactor", "RelExpr"):
        assert internal_name not in text_uk

    vis_en = ParseTreeVisualizer(code, lang="en")
    text_en = vis_en.to_text()
    assert "P " in text_en
    assert "Aexp" in text_en
    assert "Var" in text_en
    assert "Num" in text_en


def test_power_sipl_leaves_count_and_yield():
    """Для power.sipl кількість листків дорівнює 24, а обхід зліва направо відновлює програму."""
    power_code = Path("examples/power.sipl").read_text(encoding="utf-8")
    vis = ParseTreeVisualizer(power_code, lang="uk")
    leaves = vis.get_leaves()

    assert len(leaves) == 24
    assert [lf.leaf_index for lf in leaves] == list(range(1, 25))

    reconstructed = " ".join(lf.source for lf in leaves)
    assert reconstructed == "begin R := 1 ; while Y > 0 do begin R := R * X ; Y := Y - 1 end end"
    assert "".join(lf.source for lf in leaves) == re.sub(r"\s+", "", power_code)


def test_binary_semicolon_nesting():
    """Послідовність із 3+ операторів будується як бінарне лівоасоціативне дерево S -> S ; S."""
    code = "begin A := 1 ; B := 2 ; C := 3 end"
    vis = ParseTreeVisualizer(code, lang="en")
    data = json.loads(vis.to_json())
    # P -> ['begin', S, 'end']
    top_seq = data["children"][1]
    assert top_seq["category"] == "S"
    assert len(top_seq["children"]) == 3
    assert top_seq["children"][0]["category"] == "S"
    assert top_seq["children"][1]["name"] == ";"
    assert top_seq["children"][2]["category"] == "S"


def test_parse_tree_json_and_source_attachment():
    """Перевірка прив'язки source і span до кожного вузла."""
    code = "begin skip end"
    vis = ParseTreeVisualizer(code, lang="uk")
    data = json.loads(vis.to_json())

    assert data["kind"] == "NonTerminal"
    assert data["name"] == "<програма>"
    assert data["source"] == "begin skip end"
    assert "span" in data

    children = data["children"]
    token_names = [ch["name"] for ch in children if ch["kind"] == "Terminal"]
    assert "begin" in token_names
    assert "end" in token_names


def test_parse_tree_dot_nodes_match_json():
    """Кількість оголошень nX [ у DOT відповідає загальній кількості вузлів у JSON та не має переносів у мітках."""
    code = "begin if X > 0 then Y := 1 else skip end"
    vis = ParseTreeVisualizer(code, lang="uk")
    dot = vis.to_dot()
    json_data = json.loads(vis.to_json())

    assert "Terminal\\n" not in dot
    for internal_name in ("Aterm", "Afactor", "S_assign", "Bterm", "Bfactor", "RelExpr"):
        assert internal_name not in dot

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
    vis = ParseTreeVisualizer(code, lang="uk")
    svg = vis.to_svg()
    assert svg.strip().startswith("<?xml") or "<svg" in svg


def test_cli_visualize_output_error_handling(tmp_path):
    f = tmp_path / "prog.sipl"
    f.write_text("begin skip end", encoding="utf-8")
    bad_dir_target = "/proc/invalid_path/out.dot"
    ret = main(["visualize", str(f), "--format", "dot", "-o", bad_dir_target])
    assert ret == EXIT_USAGE_ERROR
