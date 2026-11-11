import json

import pytest

from sipl.interpreter import DivisionByZeroError, Interpreter, StepLimitExceededError
from sipl.parser import SIPLParser
from sipl.tracer import ExecutionTracer


@pytest.fixture
def parser():
    return SIPLParser()


def test_tracer_clean_condition_and_json(parser):
    """Перевірка людиночитаного виразу умови, origin та JSON."""
    code = """
    begin
        X := 2;
        if X > 1 then
            Y := 10
        else
            Y := 0
    end
    """
    program = parser.parse(code)
    tracer = ExecutionTracer()
    interpreter = Interpreter(tracer=tracer)

    final_state = interpreter.execute(program)
    assert final_state == {"X": 2, "Y": 10}

    events = tracer.events
    assert len(events) > 0

    # Перевірка умови: замість repr маємо 'X > 1', а origin — 'If'
    cond_events = [e for e in events if e.event_type == "ConditionCheck"]
    assert len(cond_events) == 1
    assert cond_events[0].details["condition"] == "X > 1"
    assert cond_events[0].details["origin"] == "If"
    assert cond_events[0].details["result"] is True

    # Перевірка реєстрації зміни змінної
    x_changes = [e for e in events if e.event_type == "VariableChange" and e.details["var"] == "X"]
    assert len(x_changes) == 1
    assert x_changes[0].details["new_value"] == 2

    # Перевірка фінішу: є і total_steps, і total_events
    finish_event = events[-1]
    assert finish_event.event_type == "ProgramFinished"
    assert "total_steps" in finish_event.details
    assert "total_events" in finish_event.details

    # JSON валідний об'єкт
    parsed = json.loads(tracer.to_json())
    assert isinstance(parsed, dict)
    assert parsed["status"] == "ok"
    assert isinstance(parsed["events"], list)
    assert len(parsed["events"]) == len(events)
    assert parsed["truncated"] is False


def test_tracer_records_error_event(parser):
    """Перевірка генерації події ProgramError при перевищенні ліміту кроків."""
    code = """
    begin
        while true do
            skip
    end
    """
    program = parser.parse(code)
    tracer = ExecutionTracer()
    interpreter = Interpreter(step_limit=20, tracer=tracer)

    with pytest.raises(StepLimitExceededError):
        interpreter.execute(program)

    assert len(tracer.events) > 0
    last_event = tracer.events[-1]
    assert last_event.event_type == "ProgramError"
    assert last_event.details["error_type"] == "StepLimitExceededError"
    assert "limit exceeded" in last_event.details["message"]


def test_tracer_division_by_zero_error(parser):
    """Перевірка ProgramError при діленні на нуль."""
    code = "begin X := 5 div 0 end"
    program = parser.parse(code)
    tracer = ExecutionTracer()
    interpreter = Interpreter(tracer=tracer)

    with pytest.raises(DivisionByZeroError):
        interpreter.execute(program)

    last_event = tracer.events[-1]
    assert last_event.event_type == "ProgramError"
    assert last_event.details["error_type"] == "DivisionByZeroError"


def test_tracer_loop_with_multiple_statements(parser):
    """Перевірка циклу з блоком і послідовністю дій."""
    code = """
    begin
        I := 0;
        S := 0;
        while I < 2 do
        begin
            S := S + 10;
            I := I + 1
        end
    end
    """
    program = parser.parse(code)
    tracer = ExecutionTracer()
    interpreter = Interpreter(tracer=tracer)
    interpreter.execute(program)

    cond_events = [e for e in tracer.events if e.event_type == "ConditionCheck"]
    assert len(cond_events) == 3
    for ce in cond_events:
        assert ce.details["origin"] == "While"
        assert ce.details["condition"] == "I < 2"

    assert cond_events[0].details["result"] is True
    assert cond_events[1].details["result"] is True
    assert cond_events[2].details["result"] is False
