"""Pytest socket guard for authoritative offline checks."""

from __future__ import annotations

import errno
import ipaddress
import os
import socket
from collections.abc import Callable
from typing import Any

OFFLINE_ENVIRONMENT_VARIABLE = "QUANTLAB_OFFLINE"
_DENIAL_MESSAGE = "QUANTLAB_OFFLINE blocks non-loopback network access"
_LOOPBACK_HOSTNAMES = {"localhost", "localhost."}


def _is_loopback_host(host: object) -> bool:
    """Return whether a socket host designates the local loopback interface."""
    if isinstance(host, bytes):
        try:
            host = host.decode("ascii")
        except UnicodeDecodeError:
            return False
    if not isinstance(host, str):
        return False

    normalized = host.rstrip(".").lower()
    if normalized in _LOOPBACK_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(normalized.split("%", maxsplit=1)[0]).is_loopback
    except ValueError:
        return False


def _socket_address_is_loopback(connection: socket.socket, address: object) -> bool:
    """Return whether an internet socket destination is explicitly loopback."""
    if connection.family not in (socket.AF_INET, socket.AF_INET6):
        return True
    return isinstance(address, tuple) and bool(address) and _is_loopback_host(address[0])


def _raise_network_denied() -> None:
    raise OSError(errno.ENETUNREACH, _DENIAL_MESSAGE)


class OfflineSocketGuard:
    """Temporarily prevent internet sockets from leaving the local machine."""

    _installations = 0
    _connect: Callable[..., Any] | None = None
    _connect_ex: Callable[..., Any] | None = None
    _sendto: Callable[..., Any] | None = None
    _getaddrinfo: Callable[..., Any] | None = None
    _gethostbyname: Callable[..., Any] | None = None
    _gethostbyname_ex: Callable[..., Any] | None = None
    _gethostbyaddr: Callable[..., Any] | None = None
    _getnameinfo: Callable[..., Any] | None = None
    _getfqdn: Callable[..., Any] | None = None

    def install(self) -> None:
        """Install the guard, allowing nested callers to share one patch."""
        if type(self)._installations == 0:
            type(self)._connect = socket.socket.connect
            type(self)._connect_ex = socket.socket.connect_ex
            type(self)._sendto = socket.socket.sendto
            type(self)._getaddrinfo = socket.getaddrinfo
            type(self)._gethostbyname = socket.gethostbyname
            type(self)._gethostbyname_ex = socket.gethostbyname_ex
            type(self)._gethostbyaddr = socket.gethostbyaddr
            type(self)._getnameinfo = socket.getnameinfo
            type(self)._getfqdn = socket.getfqdn
            socket.socket.connect = _guarded_connect
            socket.socket.connect_ex = _guarded_connect_ex
            socket.socket.sendto = _guarded_sendto
            socket.getaddrinfo = _guarded_getaddrinfo
            socket.gethostbyname = _guarded_gethostbyname
            socket.gethostbyname_ex = _guarded_gethostbyname_ex
            socket.gethostbyaddr = _guarded_gethostbyaddr
            socket.getnameinfo = _guarded_getnameinfo
            socket.getfqdn = _guarded_getfqdn
        type(self)._installations += 1

    def uninstall(self) -> None:
        """Restore Python's socket functions after the final guard exits."""
        if type(self)._installations == 0:
            raise RuntimeError("offline socket guard is not installed")
        type(self)._installations -= 1
        if type(self)._installations == 0:
            assert type(self)._connect is not None
            assert type(self)._connect_ex is not None
            assert type(self)._sendto is not None
            assert type(self)._getaddrinfo is not None
            assert type(self)._gethostbyname is not None
            assert type(self)._gethostbyname_ex is not None
            assert type(self)._gethostbyaddr is not None
            assert type(self)._getnameinfo is not None
            assert type(self)._getfqdn is not None
            socket.socket.connect = type(self)._connect
            socket.socket.connect_ex = type(self)._connect_ex
            socket.socket.sendto = type(self)._sendto
            socket.getaddrinfo = type(self)._getaddrinfo
            socket.gethostbyname = type(self)._gethostbyname
            socket.gethostbyname_ex = type(self)._gethostbyname_ex
            socket.gethostbyaddr = type(self)._gethostbyaddr
            socket.getnameinfo = type(self)._getnameinfo
            socket.getfqdn = type(self)._getfqdn
            type(self)._connect = None
            type(self)._connect_ex = None
            type(self)._sendto = None
            type(self)._getaddrinfo = None
            type(self)._gethostbyname = None
            type(self)._gethostbyname_ex = None
            type(self)._gethostbyaddr = None
            type(self)._getnameinfo = None
            type(self)._getfqdn = None

    def __enter__(self) -> OfflineSocketGuard:
        self.install()
        return self

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> None:
        self.uninstall()


def _guarded_connect(connection: socket.socket, address: object) -> Any:
    if not _socket_address_is_loopback(connection, address):
        _raise_network_denied()
    assert OfflineSocketGuard._connect is not None
    return OfflineSocketGuard._connect(connection, address)


def _guarded_connect_ex(connection: socket.socket, address: object) -> int:
    if not _socket_address_is_loopback(connection, address):
        return errno.ENETUNREACH
    assert OfflineSocketGuard._connect_ex is not None
    return OfflineSocketGuard._connect_ex(connection, address)


def _guarded_sendto(connection: socket.socket, data: bytes, *arguments: object) -> int:
    address = arguments[-1]
    if not _socket_address_is_loopback(connection, address):
        _raise_network_denied()
    assert OfflineSocketGuard._sendto is not None
    return OfflineSocketGuard._sendto(connection, data, *arguments)


def _guarded_getaddrinfo(host: object, *arguments: object, **keyword_arguments: object) -> Any:
    if host is not None and not _is_loopback_host(host):
        _raise_network_denied()
    assert OfflineSocketGuard._getaddrinfo is not None
    return OfflineSocketGuard._getaddrinfo(host, *arguments, **keyword_arguments)


def _guarded_gethostbyname(host: object) -> Any:
    if not _is_loopback_host(host):
        _raise_network_denied()
    assert OfflineSocketGuard._gethostbyname is not None
    return OfflineSocketGuard._gethostbyname(host)


def _guarded_gethostbyname_ex(host: object) -> Any:
    if not _is_loopback_host(host):
        _raise_network_denied()
    assert OfflineSocketGuard._gethostbyname_ex is not None
    return OfflineSocketGuard._gethostbyname_ex(host)


def _guarded_gethostbyaddr(host: object) -> Any:
    if not _is_loopback_host(host):
        _raise_network_denied()
    assert OfflineSocketGuard._gethostbyaddr is not None
    return OfflineSocketGuard._gethostbyaddr(host)


def _guarded_getnameinfo(address: object, *arguments: object) -> Any:
    if not isinstance(address, tuple) or not address or not _is_loopback_host(address[0]):
        _raise_network_denied()
    assert OfflineSocketGuard._getnameinfo is not None
    return OfflineSocketGuard._getnameinfo(address, *arguments)


def _guarded_getfqdn(host: object = "") -> Any:
    if host not in ("", "0.0.0.0", "::") and not _is_loopback_host(host):
        _raise_network_denied()
    assert OfflineSocketGuard._getfqdn is not None
    return OfflineSocketGuard._getfqdn(host)


def offline_socket_guard() -> OfflineSocketGuard:
    """Return a context manager that enforces the offline socket contract."""
    return OfflineSocketGuard()


_pytest_guard: OfflineSocketGuard | None = None


def pytest_configure() -> None:
    """Enable the guard for every pytest run explicitly marked offline."""
    global _pytest_guard
    if os.environ.get(OFFLINE_ENVIRONMENT_VARIABLE) == "1":
        _pytest_guard = offline_socket_guard()
        _pytest_guard.install()


def pytest_unconfigure() -> None:
    """Restore global socket state after the offline pytest session ends."""
    global _pytest_guard
    if _pytest_guard is not None:
        _pytest_guard.uninstall()
        _pytest_guard = None
