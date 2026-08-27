from so101_monitoring.proto.telemetry import telemetry_pb2
import logging
import queue
import threading
from so101_monitoring.state_machine import Event

logger = logging.getLogger(__name__)


class Parser:

    def __init__(
            self,
            telem_queue: queue.Queue[bytes],
            event_queue: queue.Queue[Event],
            done: threading.Event
            ) -> None:
        self.telem_queue = telem_queue
        self.event_queue = event_queue
        self.done = done

    def handle_telem_loop(self) -> None:
        while not self.done.is_set():
            try:
                msg = self.telem_queue.get(block=True, timeout=1.0)
                self.handle_message(msg)
            except queue.Empty:
                pass
        logger.info("Parser telem loop stopped")

    def handle_message(self, message: bytes) -> None:
        logger.debug(f"Handling message of size {len(message)}")

        envelope = telemetry_pb2.Envelope()
        envelope.ParseFromString(message)
        payload_type = envelope.WhichOneof("payload")

        if payload_type is None:
            logger.warning("Payload type could not be parsed, discarding")
            return

        match payload_type:
            case "graspCandidate":
                self.handle_grasp_candidate(envelope.graspCandidate)
            case "pickPlan":
                self.handle_pick_plan(envelope.pickPlan)
            case "pickStatus":
                self.handle_pick_status(envelope.pickStatus)
            case _:
                logger.warning("Unknown payload type, discarding")

    def handle_grasp_candidate(self, grasp_candidate: telemetry_pb2.GraspCandidate) -> None:
        logger.info(f"Handling grasp candidate, id: {grasp_candidate.id}")
        if grasp_candidate.success:
            self.event_queue.put(Event.GRASP_PLAN_SUCCESS)
        else:
            self.event_queue.put(Event.GRASP_PLAN_FAILURE)

    def handle_pick_plan(self, pick_plan: telemetry_pb2.PickPlan) -> None:
        logger.info(f"Handling pick plan, id: {pick_plan.id}")
        if pick_plan.success:
            self.event_queue.put(Event.PICK_PLAN_SUCCESS)
        else:
            self.event_queue.put(Event.PICK_PLAN_FAILURE)

    def handle_pick_status(self, pick_status: telemetry_pb2.PickStatus) -> None:
        logger.info(f"Handling pick status, id: {pick_status.id}")
        match pick_status.status:
            case telemetry_pb2.PickStatus.Status.SUCCESS:
                self.event_queue.put(Event.PICK_EXECUTE_SUCCESS)
            case telemetry_pb2.PickStatus.Status.FAILURE:
                self.event_queue.put(Event.PICK_EXECUTE_FAILURE)
