from so101_monitoring.proto.telemetry import telemetry_pb2
import time
import uuid
from so101_monitoring.socket_manager import Client
from so101_monitoring.logging_config import configure_logging
import os
from dotenv import load_dotenv
from queue import Queue
import threading


def gen_grasp(success: bool) -> telemetry_pb2.Envelope:
    if success:
        return telemetry_pb2.Envelope(graspCandidate=telemetry_pb2.GraspCandidate(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            success=True,
            score=0.92,
            pose=telemetry_pb2.GraspCandidate.Pose(
                x=0.45,
                y=0.12,
                z=0.30,
                qx=0.0,
                qy=0.707,
                qz=0.0,
                qw=0.707,
            ),
        ))
    else:
        return telemetry_pb2.Envelope(graspCandidate=telemetry_pb2.GraspCandidate(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            success=False
        ))


load_dotenv()
HOST = os.environ.get("HOST")
PORT = os.environ.get("VISION_PORT")


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
        grasp = gen_grasp(True)
        binary_data = grasp.SerializeToString()
        print(f"sending message of size {len(binary_data)}")
        telem_queue.put(binary_data)
        time.sleep(1)

    done.set()
    client_thread.join()


if __name__ == "__main__":
    main()
