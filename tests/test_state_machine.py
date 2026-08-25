from so101_monitoring.state_machine import State, Event, Machine
import pytest


@pytest.fixture
def machine():
    return Machine()


def test_initial_state(machine):
    assert machine.state == State.PLANNING_GRASP


def test_failure(machine):
    machine.dispatch(Event.GRASP_PLAN_FAILURE)
    assert machine.state == State.GO_HOME

    machine.dispatch(Event.GRASP_PLAN_SUCCESS)
    assert machine.state == State.GO_HOME


def test_success(machine):
    machine.dispatch(Event.GRASP_PLAN_SUCCESS)
    assert machine.state == State.PLANNING_PICK

    machine.dispatch(Event.PICK_PLAN_SUCCESS)
    assert machine.state == State.EXECUTING_PICK

    machine.dispatch(Event.PICK_EXECUTE_SUCCESS)
    assert machine.state == State.PLANNING_GRASP
