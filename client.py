from socket_manager_2 import Client
import time


HOST = "127.0.0.1"
PORT = 65432

client = Client(HOST, PORT)
client.start()
for i in range(5):
    client.send(f"message number {i}".encode("utf-8"))
    time.sleep(1)
client.stop()
