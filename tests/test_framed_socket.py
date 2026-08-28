import socket
import pytest
from so101_monitoring.socket_manager import FramedSocket


@pytest.fixture
def pair():
    sock_a, sock_b = socket.socketpair()
    sock_a.settimeout(1.0)
    sock_b.settimeout(1.0)
    a, b = FramedSocket(sock_a), FramedSocket(sock_b)
    yield a, b
    a.close()
    b.close()


def test_roundtrip(pair):
    a, b = pair
    a.send(b"hello")
    assert b.recv() == b"hello"
