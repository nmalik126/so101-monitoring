from socket_manager_2 import Server
import time
import threading


HOST = "127.0.0.1"
PORT = 65432

server = Server(HOST, PORT)

# server.serve_forever()

# server_thread = threading.Thread(target=server.serve_forever)
# server_thread.start()

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("User keyboard interrupt")
finally:
    server.stop()
