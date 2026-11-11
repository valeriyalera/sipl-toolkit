import json

from sipl.cli import EXIT_OK, EXIT_RUNTIME_ERROR, EXIT_SYNTAX_ERROR, EXIT_USAGE_ERROR, main


def test_cli_check_success(tmp_path):
    f = tmp_path / "valid.sipl"
    f.write_text("begin X := 1 end", encoding="utf-8")
    assert main(["check", str(f)]) == EXIT_OK


def test_cli_check_syntax_error(tmp_path):
    f = tmp_path / "invalid.sipl"
    f.write_text("begin X := 1; end", encoding="utf-8")
    assert main(["check", str(f)]) == EXIT_SYNTAX_ERROR


def test_cli_file_not_found_json(tmp_path, capsys):
    ret = main(["check", str(tmp_path / "missing.sipl"), "--json"])
    assert ret == EXIT_USAGE_ERROR
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert out["error_type"] == "FileNotFound"


def test_cli_invalid_state_argument(tmp_path, capsys):
    f = tmp_path / "prog.sipl"
    f.write_text("begin skip end", encoding="utf-8")
    ret = main(["run", str(f), "--state", "X=abc", "--json"])
    assert ret == EXIT_USAGE_ERROR
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert out["error_type"] == "InvalidStateError"


def test_cli_parse_json(tmp_path, capsys):
    f = tmp_path / "prog.sipl"
    f.write_text("begin X := 42 end", encoding="utf-8")
    ret = main(["parse", str(f), "--json"])
    assert ret == EXIT_OK

    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["ast"]["type"] == "Program"
    assert out["ast"]["body"]["var"] == "X"


def test_cli_run_success_json(tmp_path, capsys):
    f = tmp_path / "calc.sipl"
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
    f.write_text(code, encoding="utf-8")
    ret = main(["run", str(f), "--state", "X=2,Y=4", "--json"])
    assert ret == EXIT_OK

    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["final_state"]["R"] == 16


def test_cli_run_runtime_error_exit_code(tmp_path, capsys):
    f = tmp_path / "divzero.sipl"
    f.write_text("begin X := 5 div 0 end", encoding="utf-8")
    ret = main(["run", str(f), "--json"])
    assert ret == EXIT_RUNTIME_ERROR
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert out["error_type"] == "DivisionByZeroError"


def test_cli_trace_json_and_truncation(tmp_path, capsys):
    f = tmp_path / "loop.sipl"
    f.write_text("begin I := 0; while I < 10 do I := I + 1 end", encoding="utf-8")
    ret = main(["trace", str(f), "--max-events", "5", "--json"])
    assert ret == EXIT_OK

    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["truncated"] is True
    assert len(out["events"]) == 5
