import socket
import struct
import threading
from typing import Any, Callable
import logging
import queue

logger = logging.getLogger(__name__)


class FramedSocket:
    """Applies simple framing protocol for sending and receiving packets over TCP socket.

    Attributes:
        _sock (socket.socket): TCP socket to send to and read from.
        _max_payload (int): Maximum payload size in bytes.
        _header (Struct): Struct representing length header.
    """

    def __init__(self, sock: socket.socket) -> None:
        """Initializes TCP socket and length header.

        Currently, a two-byte length header is hard coded for the `_max_payload` and `_header` attributes.
        This enforces a maximum payload size of 65535 bytes.

        Args:
            sock: TCP socket to send to and read from.
        """
        self._sock = sock
        self._max_payload: int = 0xFFFF
        self._header = struct.Struct("!H")
        self.closed = threading.Event()

    def send(self, payload: bytes) -> None:
        """Creates frame for payload and sends frame over socket.

        Reads length of payload to create length header.
        Prefixes length header to payload to create frame.
        Sends entire frame at once over socket.

        Args:
            payload: Binary payload to send over socket.

        Raises:
            ValueError: If payload size is greater than maximum allowed.
        """
        if len(payload) > self._max_payload:
            raise ValueError(f"payload too large: {len(payload)} > {self._max_payload}")
        header = self._header.pack(len(payload))
        frame = header + payload
        self._sock.sendall(frame)

    def recv(self) -> bytes | None:
        """Reads one packet from socket.

        Returns:
            bytes: Binary packet payload if packet was read successfully.
            None: If connection was nominally closed by peer.

        Raises:
            ConnectionError: If peer closed connection after sending a length header.
        """
        header = self._recv_exact(self._header.size)
        if header is None:
            return None
        payload_length = self._header.unpack(header)[0]
        payload = self._recv_exact(payload_length)
        if payload is None:
            raise ConnectionError("peer closed connection after header")
        return payload

    def _recv_exact(self, num_bytes: int) -> bytes | None:
        """Reads exactly `num_bytes` bytes from socket.

        Calls socket `recv` repeatedly until all bytes received.

        Args:
            num_bytes: Number of bytes to read.

        Returns:
            bytes: Binary data of size `num_bytes` if read was successful
            None: If connection was nominally closed by peer.

        Raises:
            ConnectionError: If peer closed connection in the middle of sending a payload.
            ValueError: If payload is longer than expected from the length header.
        """
        data = bytearray()
        while len(data) < num_bytes:
            chunk = self._sock.recv(num_bytes - len(data))
            if not chunk:
                if data:
                    raise ConnectionError("peer closed connection mid-packet")
                return None  # Peer closed connection
            data += chunk
        return bytes(data)

    def close(self) -> None:
        """Shuts down and closes socket."""
        if self.closed.is_set():
            return
        self.closed.set()
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self._sock.close()


class Server:
    """Creates and manages a bi-directional INET TCP socket server.

    Attributes:
        _host (str): IPv4 address.
        _port (int): Port number.
        _cmd_queue (queue.Queue[bytes]): Command queue.
        _telem_queue (queue.Queue[bytes]): Telemetry queue.
        _client_conn (FramedSocket | None): Client socket connection to send to and read from.
        _done (threading.Event): Event representing closure of server.
    """

    def __init__(
            self,
            host: str,
            port: int,
            cmd_queue: queue.Queue[bytes],
            telem_queue: queue.Queue[bytes],
            done: threading.Event
            ) -> None:
        """Initializes socket address and queues to read/write.

        Args:
            host: IPv4 address.
            port: Port number.
            cmd_queue: Command queue.
            telem_queue: Telemetry queue.
            done: Event representing closure of server.
        """
        self._host = host
        self._port = port
        self._cmd_queue = cmd_queue
        self._telem_queue = telem_queue
        self._done = done
        self._conn: FramedSocket | None = None

    def serve_forever(self) -> None:
        """Opens socket server and accepts client connections.

        Currently supports only one client connection at a time.
        Continuously listens for the next client connections.
        When connection accepted, starts a new listener thread.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self._host, self._port))
            listener.listen()
            listener.settimeout(1.0)
            logger.info(f"Server listening on {self._host}:{self._port}")
            try:
                while not self._done.is_set():
                    try:
                        sock, addr = listener.accept()
                    except TimeoutError:
                        continue
                    logger.info(f"Connected by {addr}")
                    self._replace_conn(FramedSocket(sock))
            finally:
                self._replace_conn(None)

    def _replace_conn(self, new_conn: FramedSocket | None):
        """Replaces old socket with new one, or None.

        If the new socket is not None, send and receive loops are started for it.

        Args:
            new_conn: New socket.
        """
        old_conn = self._conn
        self._conn = new_conn
        if old_conn is not None:
            old_conn.close()
        if new_conn is not None:
            threading.Thread(target=self._receive_loop, args=(new_conn,)).start()
            threading.Thread(target=self._send_loop, args=(new_conn,)).start()

    def _receive_loop(self, conn: FramedSocket) -> None:
        """Infinitely listens for new packets on client socket connection.

        Args:
            conn: Socket to read from.

        On packet reception, forwards packet to user-specified callback function.
        """
        try:
            while not self._done.is_set():
                msg = conn.recv()
                if msg is None:
                    break
                logger.debug(f"Server got msg {msg!r}")
                self._telem_queue.put(msg)
        except (OSError, ValueError) as e:
            logger.info(f"receive loop ended: {e}")
        finally:
            conn.close()

    def _send_loop(self, conn: FramedSocket) -> None:
        """Infinitely sends packets from command queue to client over socket.

        Args:
            conn: Socket to send to.

        Raises:
            ConnectionError: If method is called before client has connected.
        """
        try:
            while not self._done.is_set() and not conn.closed.is_set():
                try:
                    msg = self._cmd_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                conn.send(msg)
        except OSError as e:
            logger.info(f"send loop ended: {e}")
        finally:
            conn.close()


class Client:
    """Creates and manages a bi-directional INET TCP socket client.

    Attributes:
        _host (str): IPv4 address.
        _port (int): Port number.
        _callback (Callable[[bytes], Any]): Callback to invoke on message reception.
        _client_conn (FramedSocket | None): Client socket connection to send to and read from.
    """

    def __init__(self, host: str, port: int, callback: Callable[[bytes], Any]):
        """Initializes socket address and callback.

        Args:
            host: IPv4 address.
            port: Port number.
            callback: Callback to invoke on message reception.
        """
        self._host = host
        self._port = port
        self._callback = callback
        self._client_conn: FramedSocket | None = None

    def start(self) -> None:
        """Opens socket client.

        When connection accepted, starts a new listener thread.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self._host, self._port))
        logger.info("Client connected")
        self._client_conn = FramedSocket(sock)
        rx_thread = threading.Thread(target=self.receive_loop)
        rx_thread.start()

    def receive_loop(self) -> None:
        """Infinitely listens for new packets on client socket connection.

        On packet reception, forwards packet to user-specified callback function.
        """
        try:
            while True:
                if not self._client_conn:
                    raise ConnectionError("Receive loop started before client connection established")
                msg = self._client_conn.recv()
                if msg is None:
                    break
                logger.debug(f"Client got msg: {msg!r}")
                self._callback(msg)
        except (ConnectionError, ValueError):
            logger.exception("client receive loop error")
        finally:
            if self._client_conn:
                self._client_conn.close()

    def send(self, msg: bytes) -> None:
        """Sends packet to server over socket.

        Args:
            msg: Binary payload to send.

        Raises:
            ConnectionError: If method is called before client has connected.
        """
        if not self._client_conn:
            raise ConnectionError("attempted send before peer connected")
        self._client_conn.send(msg)

    def stop(self):
        """Closes the client socket."""
        if self._client_conn:
            self._client_conn.close()
        logger.info("Client stopped")
