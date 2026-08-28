# so101-monitoring
Supervisory control for a pick-and-place pipeline.

A central Finite State Machine (FSM) coordinates two external components - a computer vision process and a robot control process - over INET TCP sockets. The FSM runs the server side, and the two external components connect as clients. The wire protocol is protobuf with a 2-byte length prefix.

## Architecture

![Architecture Diagram](/assets/architecture.svg)

Every component runs on its own thread and communicates through `queue.Queue`. A single `threading.Event` is shared by all participants and signals shutdown.

| Entity | Module | Role |
| --- | --- | --- |
| `FramedSocket` | `socket_manager.py` | Length-prefixed framing over a TCP socket |
| `Connection` | `socket_manager.py` | Base class: rx/tx threads bridge a `FrameSocket` to rx/tx queues |
| `Server` | `socket_manager.py` | Accepts one client at a time; a new client replaces the old one |
| `Client` | `socket_manager.py` | Connects to a `Server`; for use in the vision/robot processes |
| `Parser` | `parser.py` | Decodes protobuf telemetry into state-machine `Events`s |
| `Machine` | `state_machine.py` | FSM for pick-and-place cycle |
| - | `main.py` | Example server-side implementation; initializes `Machine`, `Parser`, and `Server`s for vision and robot |
| - | `mock_vision.py` and `mock_robot.py` | Example client-side implementations |

### State Machine
![State Machine Diagram](/assets/state_diagram.svg)

## Known Limitations

- One client per server; a second connection replaces the first.

- 64 KiB maximum frame size (2-byte length header).

- No client-side reconnect; client processes must restart `run_forever` on disconnect.

- No authentication or encryption; intended for a trusted local network.

- Error state (GO HOME) is terminal.
