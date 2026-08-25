import socket
import struct
import threading
from collections.abc import Callable


class FramedSocket:

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._max_payload = 0xFFFF
        self._header = struct.Struct("!H")

    def send(self, payload: bytes) -> None:
        if len(payload) > self._max_payload:
            raise ValueError(f"payload too large: {len(payload)} > {self._max_payload}")
        header = self._header.pack(len(payload))
        frame = header + payload
        self._sock.sendall(frame)

    def recv(self) -> bytes | None:
        header = self._recv_exact(self._header.size)
        if not header:
            return None
        payload_length = self._header.unpack(header)[0]
        payload = self._recv_exact(payload_length)
        if not payload:
            raise ConnectionError("peer closed connection after header")
        return payload

    def _recv_exact(self, num_bytes: int) -> bytes | None:
        data = bytearray()
        while len(data) < num_bytes:
            chunk = self._sock.recv(num_bytes - len(data))
            if not chunk:
                if data:
                    raise ConnectionError("peer closed connection mid-packet")
                return None # Peer closed connection
            data += chunk
        if len(data) > num_bytes:
            raise ValueError(f"expected payload of length {num_bytes}, got {len(data)}")
        return bytes(data)

    def close(self) -> None:
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self._sock.close()


class Server:

    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._client_conn = None
        self._done = threading.Event()

    def serve_forever(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self._host, self._port))
            listener.listen()
            print(f"Server listening on {self._host}:{self._port}")
            listener.settimeout(1.0)
            while not self._done.is_set():
                try:
                    sock, addr = listener.accept()
                    print(f"Connected by {addr}")
                    self._client_conn = FramedSocket(sock)
                    rx_thread = threading.Thread(target=self.receive_loop)
                    rx_thread.start()
                except TimeoutError:
                    pass

    def receive_loop(self) -> None:
        try:
            while True:
                msg = self._client_conn.recv()
                if not msg:
                    break
                print(f"Server got msg {msg}")
        except (ConnectionError, ValueError) as e:
            print(e)
        finally:
            self._client_conn.close()

    def send(self, msg: bytes) -> None:
        if not self._client_conn:
            raise ConnectionError("attempted send before peer connected")
        self._client_conn.send(msg)

    def stop(self):
        self._done.set()
        if self._client_conn:
            self._client_conn.close()
        print("Server stopped")


class Client:

    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._client_conn = None

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self._host, self._port))
        print("Client connected")
        self._client_conn = FramedSocket(sock)
        rx_thread = threading.Thread(target=self.receive_loop)
        rx_thread.start()
            
    def receive_loop(self) -> None:
        try:
            while True:
                msg = self._client_conn.recv()
                if not msg:
                    break
                print(f"Client got msg: {msg}")
        except (ConnectionError, ValueError) as e:
            print(e)
        finally:
            self._client_conn.close()

    def send(self, msg: bytes) -> None:
        if not self._client_conn:
            raise ConnectionError("attempted send before peer connected")
        self._client_conn.send(msg)

    def stop(self):
        if self._client_conn:
            self._client_conn.close()
        print("Client stopped")
