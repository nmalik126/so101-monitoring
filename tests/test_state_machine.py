from so101_monitoring.state_machine import State, Event, Machine

def test_initial_state():
    machine = Machine()
    assert machine.state == State.PLANNING_GRASP
