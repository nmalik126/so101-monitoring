import threading
from queue import Queue
from so101_monitoring.socket_manager import Client, Server
import pytest
import socket
import time


LOCALHOST = "127.0.0.1"


@pytest.fixture
def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((LOCALHOST, 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True)
def no_thread_leak():
    before = set(threading.enumerate())
    yield
    start = time.monotonic()
    while time.monotonic() - start < 2.0:
        leaked = [
            t.name for t in threading.enumerate()
            if t not in before and t.is_alive()
        ]
        if not leaked:
            break
        time.sleep(0.05)
    assert not leaked


def test_server_and_client_end_to_end(free_port):
    srv_cmd_q: Queue[bytes] = Queue()
    srv_telem_q: Queue[bytes] = Queue()
    cli_cmd_q: Queue[bytes] = Queue()
    cli_telem_q: Queue[bytes] = Queue()

    done = threading.Event()

    srv = Server(LOCALHOST, free_port, srv_cmd_q, srv_telem_q, done)
    srv_thread = threading.Thread(target=srv.run_forever)
    srv_thread.start()

    time.sleep(1.0)

    cli = Client(LOCALHOST, free_port, cli_cmd_q, cli_telem_q, done)
    cli_thread = threading.Thread(target=cli.run_forever)
    cli_thread.start()

    try:
        cli_telem_q.put(b"telem")
        assert srv_telem_q.get(timeout=2.0) == b"telem"
        srv_cmd_q.put(b"cmd")
        assert cli_cmd_q.get(timeout=2.0) == b"cmd"
    finally:
        done.set()
        srv_thread.join(timeout=2.0)
        cli_thread.join(timeout=2.0)
    assert not srv_thread.is_alive()
    assert not cli_thread.is_alive()
