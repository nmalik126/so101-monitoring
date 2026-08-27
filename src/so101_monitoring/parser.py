from so101_monitoring.proto.telemetry import telemetry_pb2
import logging

logger = logging.getLogger(__name__)


def handle_message(message: bytes) -> None:
    logger.info(f"Handling message of size {len(message)}")

    envelope = telemetry_pb2.Envelope()
    envelope.ParseFromString(message)
    payload_type = envelope.WhichOneof("payload")

    if payload_type is None:
        logger.warning("Payload type could not be parsed, discarding")
        return

    match payload_type:
        case "graspCandidate":
            handle_grasp_candidate(envelope.graspCandidate)
        case "pickPlan":
            handle_pick_plan(envelope.pickPlan)
        case "pickStatus":
            handle_pick_status(envelope.pickStatus)
        case _:
            logger.warning("Unknown payload type, discarding")


def handle_grasp_candidate(grasp_candidate: telemetry_pb2.GraspCandidate) -> None:
    logger.info(f"Handling grasp candidate, id: {grasp_candidate.id}")


def handle_pick_plan(pick_plan: telemetry_pb2.PickPlan) -> None:
    logger.info(f"Handling pick plan, id: {pick_plan.id}")


def handle_pick_status(pick_status: telemetry_pb2.PickStatus) -> None:
    logger.info(f"Handling pick status, id: {pick_status.id}")
