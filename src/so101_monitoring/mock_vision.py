from .proto.telemetry import telemetry_pb2
import socket
import time
import uuid

def gen_grasp(success: bool):
    if success:
        return telemetry_pb2.GraspCandidate(
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
        )
    else:
        return telemetry_pb2.GraspCandidate(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            success=False
        )

# print("Success")
# print(successful_grasp)
# print("Failed")
# print(failed_grasp)

HOST = "127.0.0.1"
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print("Connected")
    while True:
        grasp = gen_grasp(True)
        binary_data = grasp.SerializeToString()
        print(f"Vision component sending {grasp}, serialized to {binary_data!r}")
        s.sendall(binary_data)
        time.sleep(1)
