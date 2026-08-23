import telemetry_pb2

successful_grasp = telemetry_pb2.GraspCandidate(
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

failed_grasp = telemetry_pb2.GraspCandidate(success=False)

print("Success")
print(successful_grasp)
print("Failed")
print(failed_grasp)
