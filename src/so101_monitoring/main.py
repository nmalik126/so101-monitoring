from so101_monitoring.socket_manager import Server
from so101_monitoring.logging_config import configure_logging
import os
from dotenv import load_dotenv
from so101_monitoring.parser import Parser
import threading
from queue import Queue
from so101_monitoring.state_machine import Machine, Event


load_dotenv()
HOST = os.environ.get("HOST")
VISION_PORT = os.environ.get("VISION_PORT")
ROBOT_PORT = os.environ.get("ROBOT_PORT")


def main() -> None:
    configure_logging()

    if (HOST is None) or (VISION_PORT is None) or (ROBOT_PORT is None):
        print("could not load address env vars")
        return

    vision_cmd_queue: Queue[bytes] = Queue()
    robot_cmd_queue: Queue[bytes] = Queue()
    telem_queue: Queue[bytes] = Queue()
    event_queue: Queue[Event] = Queue()

    done = threading.Event()

    vision_server = Server(HOST, int(VISION_PORT), vision_cmd_queue, telem_queue, done)
    robot_server = Server(HOST, int(ROBOT_PORT), robot_cmd_queue, telem_queue, done)
    vision_server_thread = threading.Thread(target=vision_server.serve_forever)
    robot_server_thread = threading.Thread(target=robot_server.serve_forever)

    parser = Parser(telem_queue, event_queue, done)
    parser_thread = threading.Thread(target=parser.handle_telem_loop)

    machine = Machine(vision_cmd_queue, robot_cmd_queue, event_queue, done)
    machine_thread = threading.Thread(target=machine.dispatch_loop)

    threads = [
        vision_server_thread,
        robot_server_thread,
        parser_thread,
        machine_thread,
    ]

    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("User keyboard interrupt")
    finally:
        done.set()
        for thread in threads:
            thread.join()


if __name__ == "__main__":
    main()
