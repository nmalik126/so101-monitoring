from so101_monitoring.socket_manager import Server
from so101_monitoring.logging_config import configure_logging
import os
from dotenv import load_dotenv
from so101_monitoring.parser import handle_message
import threading


load_dotenv()
HOST = os.environ.get("HOST")
VISION_PORT = os.environ.get("VISION_PORT")
ROBOT_PORT = os.environ.get("ROBOT_PORT")


def main():
    configure_logging()

    if any([ev is None for ev in (HOST, VISION_PORT, ROBOT_PORT)]):
        print("could not load address env vars")
        return

    vision_server = Server(HOST, int(VISION_PORT), handle_message)
    robot_server = Server(HOST, int(ROBOT_PORT), handle_message)

    vision_server_thread = threading.Thread(target=vision_server.serve_forever)
    robot_server_thread = threading.Thread(target=robot_server.serve_forever)

    try:
        # vision_server.serve_forever()
        vision_server_thread.start()
        robot_server_thread.start()
        vision_server_thread.join()
        robot_server_thread.join()
    except KeyboardInterrupt:
        print("User keyboard interrupt")
    finally:
        vision_server.stop()
        robot_server.stop()
        vision_server_thread.join()
        robot_server_thread.join()


if __name__ == "__main__":
    main()
