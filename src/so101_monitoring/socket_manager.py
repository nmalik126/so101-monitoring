import socket
import struct
import threading
import logging
import queue
from abc import ABC, abstractmethod

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


class Connection(ABC):

    def __init__(
            self,
            rx_queue: queue.Queue[bytes],
            tx_queue: queue.Queue[bytes],
            done: threading.Event
            ) -> None:
        self._rx_queue = rx_queue
        self._tx_queue = tx_queue
        self._done = done
        self._threads: list[threading.Thread] = []

    @abstractmethod
    def run_forever(self) -> None:
        """Infinite loop to run until `_done` event is set"""
        pass

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
                logger.debug(f"got msg {msg!r}")
                self._rx_queue.put(msg)
        except (OSError, ConnectionError) as e:
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
                    msg = self._tx_queue.get(timeout=1.0)
                    conn.send(msg)
                except queue.Empty:
                    continue
                except ValueError as e:
                    logger.warning(f"send loop warning: {e}")
                    continue
        except OSError as e:
            logger.info(f"send loop ended: {e}")
        finally:
            conn.close()

    def _spawn(self, conn: FramedSocket, name: str):
        """Creates and starts the Rx and Tx threads.

        Args:
            conn: The socket connection object.
            name: Name of spawner (e.g. server or client).
        """
        self._threads = [
            threading.Thread(
                target=self._receive_loop,
                args=(conn,),
                name=f"{name}-rx"
            ),
            threading.Thread(
                target=self._send_loop,
                args=(conn,),
                name=f"{name}-tx"
            )
        ]
        for t in self._threads:
            t.start()

    def _teardown(self, conn: FramedSocket):
        """Closes the connection object and joins the Rx and Tx threads.

        Args:
            conn: The connection object associated with the Rx and Tx threads.
        """
        conn.close()
        for t in self._threads:
            t.join(2.0)
            if t.is_alive():
                logger.error(f"{t.name} did not exit after close()")


class Server(Connection):

    def __init__(
            self,
            host: str,
            port: int,
            cmd_queue: queue.Queue[bytes],
            telem_queue: queue.Queue[bytes],
            done: threading.Event
            ) -> None:
        super().__init__(
            rx_queue=telem_queue,
            tx_queue=cmd_queue,
            done=done)
        self._host = host
        self._port = port
        self._conn: FramedSocket | None = None

    def run_forever(self) -> None:
        """Opens socket server and accepts client connections.

        Currently supports only one client connection at a time.
        Continuously listens for the next client connections.
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
            self._teardown(old_conn)
        if new_conn is not None:
            self._spawn(new_conn, "server")


class Client(Connection):

    def __init__(
            self,
            host: str,
            port: int,
            cmd_queue: queue.Queue[bytes],
            telem_queue: queue.Queue[bytes],
            done: threading.Event
            ) -> None:
        super().__init__(
            rx_queue=cmd_queue,
            tx_queue=telem_queue,
            done=done)
        self._host = host
        self._port = port

    def run_forever(self):
        """Opens a client connection."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self._host, self._port))
        logger.info("Client connected")
        conn = FramedSocket(sock)
        self._spawn(conn, "client")
        try:
            while not self._done.is_set():
                if conn.closed.wait(timeout=1.0):
                    logger.warning("connection to server lost")
        finally:
            self._teardown(conn)
