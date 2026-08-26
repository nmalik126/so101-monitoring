from so101_monitoring.socket_manager import Client
import time


HOST = "127.0.0.1"
PORT = 65432


def handle_msg(msg: bytes) -> None:
    print(f"got message: {msg!r}")


client = Client(HOST, PORT, handle_msg)
client.start()
for i in range(5):
    client.send(f"message number {i}".encode("utf-8"))
    time.sleep(1)
client.stop()
