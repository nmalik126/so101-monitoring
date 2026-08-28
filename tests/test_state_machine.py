from so101_monitoring.state_machine import State, Event, Machine
import pytest
import queue
import threading
import logging
import time


TRANSITIONS: dict[tuple[State, Event], State] = {
    (State.PLANNING_GRASP, Event.GRASP_PLAN_SUCCESS): State.PLANNING_PICK,
    (State.PLANNING_GRASP, Event.GRASP_PLAN_FAILURE): State.GO_HOME,
    (State.PLANNING_PICK, Event.PICK_PLAN_SUCCESS): State.EXECUTING_PICK,
    (State.PLANNING_PICK, Event.PICK_PLAN_FAILURE): State.GO_HOME,
    (State.EXECUTING_PICK, Event.PICK_EXECUTE_SUCCESS): State.PLANNING_GRASP,
    (State.EXECUTING_PICK, Event.PICK_EXECUTE_FAILURE): State.GO_HOME,
}

INVALID_PAIRS = [
    (s, e) for s in State for e in Event
    if (s, e) not in TRANSITIONS
]


@pytest.fixture
def machine():
    vision_cmd_queue: queue.Queue[bytes] = queue.Queue()
    robot_cmd_queue: queue.Queue[bytes] = queue.Queue()
    event_queue: queue.Queue[Event] = queue.Queue()
    done = threading.Event()
    return Machine(vision_cmd_queue, robot_cmd_queue, event_queue, done)


def test_initial_state(machine):
    assert machine.state == State.PLANNING_GRASP


def test_str_reports_current_state(machine):
    assert "PLANNING_GRASP" in str(machine)


@pytest.mark.parametrize(
    "start, event, expected",
    [(s, e, n) for (s, e), n in TRANSITIONS.items()],
    ids=[f"{s.name}--{e.name}" for (s, e) in TRANSITIONS]
)
def test_valid_transition(machine, start, event, expected):
    machine.state = start
    machine.dispatch(event)
    assert machine.state == expected


@pytest.mark.parametrize(
    "start, event",
    INVALID_PAIRS,
    ids=[f"{s.name}--{e.name}" for (s, e) in INVALID_PAIRS]
)
def test_invalid_transition_is_noop_and_warns(machine, start, event, caplog):
    machine.state = start
    with caplog.at_level(logging.WARNING):
        machine.dispatch(event)
    assert machine.state == start
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_go_home_is_terminal(machine):
    machine.state = State.GO_HOME
    for event in Event:
        machine.dispatch(event)
        assert machine.state == State.GO_HOME


def test_dispatch_loop(machine):
    machine.event_queue.put(Event.GRASP_PLAN_SUCCESS)
    machine.event_queue.put(Event.PICK_PLAN_SUCCESS)

    t = threading.Thread(target=machine.dispatch_loop)
    t.start()

    start = time.monotonic()
    while (time.monotonic() - start) < 2.0:
        if machine.state == State.EXECUTING_PICK:
            break
        time.sleep(0.05)

    machine.done.set()
    t.join(timeout=2.0)
    assert not t.is_alive()
    assert machine.state == State.EXECUTING_PICK
