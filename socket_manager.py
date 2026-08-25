import struct
import socket
import telemetry_pb2
import threading
import time


def send_message(sock: socket.socket, message: bytes):
    header = struct.pack('!H', len(message))
    sock.sendall(header + message)


def read_exact(sock: socket.socket, num_bytes: int):
    data = bytearray()
    while len(data) < num_bytes:
        packet = sock.recv(num_bytes - len(data))
        if not packet:
            return None # Connection closed
        data.extend(packet)
    return bytes(data)


def read_message(sock: socket.socket):
    header = read_exact(sock, 2)
    if not header:
        return None

    payload_length = struct.unpack('!H', header)[0]
    payload = read_exact(sock, payload_length)
    if not payload:
        return None

    envelope = telemetry_pb2.Envelope()
    envelope.ParseFromString(payload)
    return envelope


def handle_message(envelope):
    payload_type = envelope.WhichOneof("payload")

    handlers = {
        "graspCandidate": handle_grasp_candidate,
        "pickPlan": handle_pick_plan
    }

    handlers[payload_type](getattr(envelope, payload_type))


def handle_grasp_candidate(msg):
    print("Handle grasp candidate")


def handle_pick_plan(msg):
    print("Handle pick plan")


class ThreadingSocketServer:

    def __init__(self, host, port, msg_callback):
        self.host = host
        self.port = port
        self.msg_callback = msg_callback
        self.close_event = threading.Event()

    def listen(self):
        with self.client_conn:
            while not self.close_event.is_set():
                msg = read_message(self.client_conn)
                if not msg:
                    print("Client disconnected")
                    break
                print("Got message")
                self.msg_callback(msg)

    def send(self, msg: bytes):
        send_message(self.client_conn, msg)

    def start(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(1)

        print(f"Server listening on {self.host}:{self.port}")
        self.client_conn, addr = self.server_sock.accept()
        print(f"Connected by {addr}")

        # create rx thread
        rx_thread = threading.Thread(target=self.listen, daemon=True)
        rx_thread.start()

    def close(self):
        self.close_event.set()
        self.server_sock.close()
        self.client_conn.close()


try:
    server = ThreadingSocketServer(
        host="127.0.0.1", 
        port=65432, 
        msg_callback=handle_message
    )
    server.start()
    # send requests here using server.send(data)
    # time.sleep is a placeholder
    time.sleep(1)
    
except KeyboardInterrupt:
    pass
finally:
    server.close()


