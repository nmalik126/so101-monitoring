from so101_monitoring.proto.telemetry import telemetry_pb2
import uuid
import time
from so101_monitoring.socket_manager import Client
from so101_monitoring.logging_config import configure_logging
import os
from dotenv import load_dotenv
from queue import Queue
import threading


def gen_plan(success: bool) -> telemetry_pb2.Envelope:
    if success:
        return telemetry_pb2.Envelope(pickPlan=telemetry_pb2.PickPlan(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            success=True,
            start_time=1.23,
            end_time=4.56,
            control_points=[telemetry_pb2.RobotConfig() for _ in range(8)]
        ))
    else:
        return telemetry_pb2.Envelope(pickPlan=telemetry_pb2.PickPlan(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            success=False
        ))


def gen_status(status: str) -> telemetry_pb2.Envelope:
    if status == "success":
        return telemetry_pb2.Envelope(pickStatus=telemetry_pb2.PickStatus(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            status=telemetry_pb2.PickStatus.SUCCESS
        ))
    elif status == "in_progress":
        return telemetry_pb2.Envelope(pickStatus=telemetry_pb2.PickStatus(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            status=telemetry_pb2.PickStatus.IN_PROGRESS,
            q=telemetry_pb2.RobotConfig()
        ))
    else:
        return telemetry_pb2.Envelope(pickStatus=telemetry_pb2.PickStatus(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            status=telemetry_pb2.PickStatus.FAILURE
        ))


load_dotenv()
HOST = os.environ.get("HOST")
PORT = os.environ.get("ROBOT_PORT")


def main() -> None:
    configure_logging()

    if (HOST is None) or (PORT is None):
        print("could not load address env vars")
        return

    cmd_queue: Queue[bytes] = Queue()
    telem_queue: Queue[bytes] = Queue()

    done = threading.Event()

    client = Client(HOST, int(PORT), cmd_queue, telem_queue, done)
    client_thread = threading.Thread(target=client.run_forever)

    client_thread.start()

    for _ in range(1):
        plan = gen_plan(True)
        binary_data = plan.SerializeToString()
        print(f"sending message of size {len(binary_data)}")
        telem_queue.put(binary_data)
        time.sleep(1)

    done.set()
    client_thread.join()


if __name__ == "__main__":
    main()
