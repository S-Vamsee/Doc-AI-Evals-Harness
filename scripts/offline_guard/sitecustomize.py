"""Refuse outbound network operations in offline, clean, and CI Python processes."""

import socket


def _deny(*_args, **_kwargs):
    raise RuntimeError("offline network disabled")


socket.socket.connect = _deny
socket.socket.connect_ex = _deny
socket.socket.sendto = _deny
socket.create_connection = _deny
socket.getaddrinfo = _deny

