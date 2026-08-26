from so101_monitoring.socket_manager import Server
# import time
# import threading


HOST = "127.0.0.1"
PORT = 65432


def handle_msg(msg: bytes) -> None:
    print(f"got message: {msg!r}")


server = Server(HOST, PORT, handle_msg)

# server.serve_forever()

# server_thread = threading.Thread(target=server.serve_forever)
# server_thread.start()

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("User keyboard interrupt")
finally:
    server.stop()
