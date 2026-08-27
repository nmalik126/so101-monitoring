from enum import Enum, auto
import logging
import queue
import threading

logger = logging.getLogger(__name__)


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
    """Finite State Machine (FSM) for pick-and-place pipeline.

    Args:
        cmd_queue (queue.Queue[bytes]): Command queue.
        event_queue (queue.Queue[Event]): Event queue.

    Attributes:
        state (State): Current FSM state.
    """

    def __init__(
            self,
            cmd_queue: queue.Queue[bytes],
            event_queue: queue.Queue[Event],
            done: threading.Event
            ) -> None:
        """Initializes FSM state to PLANNING_GRASP (nominal default)."""
        self.state = State.PLANNING_GRASP
        self.cmd_queue = cmd_queue
        self.event_queue = event_queue
        self.done = done

    def __str__(self):
        """Returns current FSM state in human-readable format."""
        return f"Current State: {self.state.name}"

    def dispatch(self, event: Event) -> None:
        """Handles new event.

        If the FSM event is valid for the current state, the state is transitioned.
        Otherwise, a warning is logged.

        Args:
            event: The event to dispatch to the FSM.
        """
        match (self.state, event):
            case (State.PLANNING_GRASP, Event.GRASP_PLAN_FAILURE):
                logger.info("Grasp plan failure, going home.")
                self.state = State.GO_HOME
            case (State.PLANNING_GRASP, Event.GRASP_PLAN_SUCCESS):
                logger.info("Grasp plan success, planning pick...")
                self.state = State.PLANNING_PICK
            case (State.PLANNING_PICK, Event.PICK_PLAN_FAILURE):
                logger.info("Pick plan failure, going home.")
                self.state = State.GO_HOME
            case (State.PLANNING_PICK, Event.PICK_PLAN_SUCCESS):
                logger.info("Pick plan success, executing pick...")
                self.state = State.EXECUTING_PICK
            case (State.EXECUTING_PICK, Event.PICK_EXECUTE_FAILURE):
                logger.info("Pick execute failure, going home.")
                self.state = State.GO_HOME
            case (State.EXECUTING_PICK, Event.PICK_EXECUTE_SUCCESS):
                logger.info("Pick execute success, planning next grasp...")
                self.state = State.PLANNING_GRASP
            case _:
                logger.warning(f"Event {event.name} invalid in state {self.state.name}")

    def dispatch_loop(self) -> None:
        while not self.done.is_set():
            try:
                event = self.event_queue.get(block=True, timeout=1.0)
                self.dispatch(event)
            except queue.Empty:
                pass
        logger.info("State machine dispatch loop stopped")
