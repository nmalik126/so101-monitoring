import telemetry_pb2
import uuid
import time
import socket

def gen_plan(success: bool):
    if success:
        return telemetry_pb2.PickPlan(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            success=True,
            start_time=1.23,
            end_time=4.56,
            control_points=[telemetry_pb2.RobotConfig() for _ in range(8)]
        )
    else:
        return telemetry_pb2.PickPlan(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            success=False
        )

def gen_status(status: str):
    if status == "success":
        return telemetry_pb2.PickStatus(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            status=telemetry_pb2.PickStatus.SUCCESS
        )
    elif status == "in_progress":
        return telemetry_pb2.PickStatus(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            status=telemetry_pb2.PickStatus.IN_PROGRESS,
            q=telemetry_pb2.RobotConfig()
        )
    else:
        return telemetry_pb2.PickStatus(
            id=str(uuid.uuid4()),
            timestamp=time.time_ns(),
            status=telemetry_pb2.PickStatus.FAILURE
        )        


HOST = "127.0.0.1"
PORT = 65433

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print("Connected")
    while True:
        plan = gen_plan(True)
        binary_data = plan.SerializeToString()
        print(f"Robot component sending {plan}, serialized to {binary_data!r}")
        s.sendall(binary_data)
        time.sleep(1)
