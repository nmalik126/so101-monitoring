from enum import Enum, auto


class State(Enum):
    PLANNING_GRASP = auto()
    PLANNING_PICK = auto()
    EXECUTING_PICK = auto()
    GO_HOME = auto()


class Event(Enum):
    GRASP_PLAN_FAILURE = auto()
    GRASP_PLAN_SUCCESS = auto()
    PICK_PLAN_FAILURE = auto()
    PICK_PLAN_SUCCESS = auto()
    PICK_EXECUTE_FAILURE = auto()
    PICK_EXECUTE_SUCCESS = auto()


class Machine:

    def __init__(self):
        self.state: State = State.PLANNING_GRASP

    def __str__(self):
        return f"Current State: {self.state.name}"

    def dispatch(self, event: Event):
        match (self.state, event):
            case (State.PLANNING_GRASP, Event.GRASP_PLAN_FAILURE):
                print("Grasp plan failure, going home.")
                self.state = State.GO_HOME
            case (State.PLANNING_GRASP, Event.GRASP_PLAN_SUCCESS):
                print("Grasp plan success, planning pick...")
                self.state = State.PLANNING_PICK
            case (State.PLANNING_PICK, Event.PICK_PLAN_FAILURE):
                print("Pick plan failure, going home.")
                self.state = State.GO_HOME
            case (State.PLANNING_PICK, Event.PICK_PLAN_SUCCESS):
                print("Pick plan success, executing pick...")
                self.state = State.EXECUTING_PICK
            case (State.EXECUTING_PICK, Event.PICK_EXECUTE_FAILURE):
                print("Pick execute failure, going home.")
                self.state = State.GO_HOME
            case (State.EXECUTING_PICK, Event.PICK_EXECUTE_SUCCESS):
                print("Pick execute success, planning next grasp...")
                self.state = State.PLANNING_GRASP
            case _:
                print(f"Event {event.name} invalid in state {self.state.name}")


# machine = Machine()
# print(machine)
# machine.dispatch(Event.GRASP_PLAN_FAILURE)
# print(machine)
# machine.dispatch(Event.GRASP_PLAN_SUCCESS)

machine = Machine()
print(machine)
machine.dispatch(Event.GRASP_PLAN_SUCCESS)
print(machine)
machine.dispatch(Event.PICK_PLAN_SUCCESS)
print(machine)
machine.dispatch(Event.PICK_EXECUTE_SUCCESS)
print(machine)
machine.dispatch(Event.GRASP_PLAN_SUCCESS)
print(machine)
machine.dispatch(Event.PICK_PLAN_SUCCESS)
print(machine)
machine.dispatch(Event.PICK_EXECUTE_SUCCESS)
print(machine)
