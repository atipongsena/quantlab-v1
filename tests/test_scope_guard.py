"""Behavioral checks for the milestone scope guard."""

from __future__ import annotations

import errno
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from tests.socket_guard import offline_socket_guard

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCOPE_CHECK = PROJECT_ROOT / "scripts" / "check_scope.py"


@pytest.mark.parametrize(
    ("family", "address"),
    [
        (socket.AF_INET, ("198.51.100.1", 443)),
        (socket.AF_INET6, ("2001:db8::1", 443, 0, 0)),
        (socket.AF_INET, ("example.com", 443)),
    ],
    ids=("ipv4", "ipv6", "hostname"),
)
def test_socket_guard_blocks_external_network(
    family: socket.AddressFamily, address: tuple[object, ...]
) -> None:
    """Removing the offline address check would permit an external socket connection."""
    with offline_socket_guard():
        with socket.socket(family, socket.SOCK_STREAM) as connection:
            with pytest.raises(OSError) as error:
                connection.connect(address)

    assert error.value.errno == errno.ENETUNREACH


def test_socket_guard_permits_loopback_network() -> None:
    """Treating a local integration socket as external would break its connection."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        with offline_socket_guard():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
                connection.connect(listener.getsockname())
            with listener.accept()[0] as accepted_connection:
                assert accepted_connection.getpeername()[0] == "127.0.0.1"


def test_socket_guard_blocks_external_datagram_network() -> None:
    """Removing the datagram address check would send packets beyond loopback."""
    with offline_socket_guard():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            with pytest.raises(OSError) as error:
                connection.sendto(b"quantlab", 0, ("198.51.100.1", 443))

    assert error.value.errno == errno.ENETUNREACH


@pytest.mark.skipif(not hasattr(socket.socket, "sendmsg"), reason="sendmsg is unavailable")
def test_socket_guard_controls_sendmsg_destinations() -> None:
    """Removing sendmsg address checks would permit non-loopback datagrams."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener:
        listener.bind(("127.0.0.1", 0))
        with offline_socket_guard():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
                with pytest.raises(OSError) as error:
                    connection.sendmsg([b"quantlab"], [], 0, ("198.51.100.1", 443))

                assert connection.sendmsg([b"quantlab"], [], 0, listener.getsockname()) == 8

                connection.connect(listener.getsockname())
                assert connection.sendmsg([b"quantlab"]) == 8

        assert listener.recvfrom(16)[0] == b"quantlab"
        assert listener.recvfrom(16)[0] == b"quantlab"
    assert error.value.errno == errno.ENETUNREACH


@pytest.mark.skipif(not hasattr(socket.socket, "sendmsg"), reason="sendmsg is unavailable")
def test_socket_guard_restores_nested_sendmsg_installations() -> None:
    """An inner guard removal must not restore sendmsg before the outer guard exits."""
    original_sendmsg = socket.socket.sendmsg
    outer_guard = offline_socket_guard()
    inner_guard = offline_socket_guard()
    outer_guard.install()
    try:
        inner_guard.install()
        inner_guard.uninstall()

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            with pytest.raises(OSError) as error:
                connection.sendmsg([b"quantlab"], [], 0, ("198.51.100.1", 443))
    finally:
        outer_guard.uninstall()

    assert error.value.errno == errno.ENETUNREACH
    assert socket.socket.sendmsg is original_sendmsg


@pytest.mark.parametrize(
    ("resolver_name", "arguments"),
    [
        ("gethostbyname", ("198.51.100.1",)),
        ("gethostbyname_ex", ("198.51.100.1",)),
        ("gethostbyaddr", ("198.51.100.1",)),
        ("getnameinfo", (("198.51.100.1", 443), socket.NI_NUMERICHOST)),
        ("getfqdn", ("198.51.100.1",)),
    ],
)
def test_socket_guard_blocks_nonloopback_resolution_before_lookup(
    resolver_name: str, arguments: tuple[object, ...]
) -> None:
    """Removing resolver checks would permit external name resolution in offline mode."""
    with offline_socket_guard():
        with pytest.raises(OSError) as error:
            getattr(socket, resolver_name)(*arguments)

    assert error.value.errno == errno.ENETUNREACH


def test_socket_guard_permits_loopback_resolution() -> None:
    """Blocking local resolver calls would break loopback integration services."""
    with offline_socket_guard():
        assert socket.gethostbyname("127.0.0.1") == "127.0.0.1"
        assert "127.0.0.1" in socket.gethostbyname_ex("127.0.0.1")[2]
        assert socket.gethostbyaddr("127.0.0.1")[2] == ["127.0.0.1"]
        assert socket.getnameinfo(
            ("127.0.0.1", 5432), socket.NI_NUMERICHOST | socket.NI_NUMERICSERV
        ) == ("127.0.0.1", "5432")
        assert socket.getfqdn("127.0.0.1")


def test_socket_guard_restores_nested_installations() -> None:
    """Dropping an inner guard must leave the outer guard active and restore it last."""
    original_calls = (
        socket.socket.connect,
        socket.socket.connect_ex,
        socket.socket.sendto,
        socket.getaddrinfo,
        socket.gethostbyname,
        socket.gethostbyname_ex,
        socket.gethostbyaddr,
        socket.getnameinfo,
        socket.getfqdn,
    )
    outer_guard = offline_socket_guard()
    inner_guard = offline_socket_guard()
    outer_guard.install()
    try:
        inner_guard.install()
        inner_guard.uninstall()

        with pytest.raises(OSError) as error:
            socket.gethostbyname("198.51.100.1")
    finally:
        outer_guard.uninstall()

    assert error.value.errno == errno.ENETUNREACH
    assert (
        socket.socket.connect,
        socket.socket.connect_ex,
        socket.socket.sendto,
        socket.getaddrinfo,
        socket.gethostbyname,
        socket.gethostbyname_ex,
        socket.gethostbyaddr,
        socket.getnameinfo,
        socket.getfqdn,
    ) == original_calls


def run_scope_check(root: Path, milestone: str) -> tuple[int, dict[str, object]]:
    """Run the real guard against an isolated filesystem tree."""
    completed = subprocess.run(
        [sys.executable, str(SCOPE_CHECK), milestone],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    return completed.returncode, json.loads(completed.stdout)


def test_scope_rejects_premature_packages(tmp_path: Path) -> None:
    """Adding a package assigned to a future milestone must halt M0 work."""
    (tmp_path / "quantlab" / "data").mkdir(parents=True)
    (tmp_path / "quantlab" / "data" / "__init__.py").touch()

    exit_code, result = run_scope_check(tmp_path, "M0")

    assert exit_code == 2
    assert result == {
        "milestone": "M0",
        "status": "rejected",
        "violations": [
            {
                "available_in": "M1",
                "kind": "premature_package",
                "path": "quantlab/data",
            }
        ],
    }


def test_scope_rejects_premature_namespace_packages(tmp_path: Path) -> None:
    """Removing directory checks would allow an uninitialized M8 web package in M0."""
    (tmp_path / "apps" / "web").mkdir(parents=True)

    exit_code, result = run_scope_check(tmp_path, "M0")

    assert exit_code == 2
    assert result == {
        "milestone": "M0",
        "status": "rejected",
        "violations": [
            {
                "available_in": "M8",
                "kind": "premature_package",
                "path": "apps/web",
            }
        ],
    }


def test_scope_allows_m0_package_roots(tmp_path: Path) -> None:
    """The package boundaries explicitly introduced in M0 are accepted."""
    (tmp_path / "quantlab").mkdir()
    (tmp_path / "quantlab" / "__init__.py").touch()

    exit_code, result = run_scope_check(tmp_path, "M0")

    assert exit_code == 0
    assert result == {"milestone": "M0", "status": "ok", "violations": []}


def test_scope_rejects_forbidden_content_in_neutral_source_and_config_files(
    tmp_path: Path,
) -> None:
    """Removing content checks would allow forbidden capabilities behind neutral paths."""
    source_file = tmp_path / "quantlab" / "runner.py"
    source_file.parent.mkdir()
    source_file.write_text(
        'execution_frequency = "intraday"\norder_destination = "live-money"\n',
        encoding="utf-8",
    )
    config_file = tmp_path / "configs" / "runtime.toml"
    config_file.parent.mkdir()
    config_file.write_text(
        'instrument_class = "options"\nderivative_kind = "derivatives"\nexposure = "leveraged"\n',
        encoding="utf-8",
    )

    exit_code, result = run_scope_check(tmp_path, "M9")

    assert exit_code == 2
    assert result == {
        "milestone": "M9",
        "status": "rejected",
        "violations": [
            {
                "kind": "forbidden_v1_feature",
                "path": "quantlab/runner.py",
                "rule": "live_money",
            },
            {
                "kind": "forbidden_v1_feature",
                "path": "quantlab/runner.py",
                "rule": "intraday",
            },
            {
                "kind": "forbidden_v1_feature",
                "path": "configs/runtime.toml",
                "rule": "options",
            },
            {
                "kind": "forbidden_v1_feature",
                "path": "configs/runtime.toml",
                "rule": "derivatives",
            },
            {
                "kind": "forbidden_v1_feature",
                "path": "configs/runtime.toml",
                "rule": "leverage",
            },
        ],
    }


def test_scope_rejects_premature_dependencies_in_metadata(tmp_path: Path) -> None:
    """Removing metadata checks would allow M5 and M8 dependencies during M0."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["fastapi==0.1.0"]\n',
        encoding="utf-8",
    )
    (tmp_path / "requirements.lock").write_text("lightgbm==4.0.0\n", encoding="utf-8")

    exit_code, result = run_scope_check(tmp_path, "M0")

    assert exit_code == 2
    assert result == {
        "milestone": "M0",
        "status": "rejected",
        "violations": [
            {
                "available_in": "M8",
                "dependency": "fastapi",
                "kind": "premature_dependency",
                "path": "pyproject.toml",
            },
            {
                "available_in": "M5",
                "dependency": "lightgbm",
                "kind": "premature_dependency",
                "path": "requirements.lock",
            },
        ],
    }


def test_scope_ignores_planned_dependencies_but_rejects_runtime_dependencies(
    tmp_path: Path,
) -> None:
    """Treating policy prose as code would reject M0, while imports must still be denied."""
    exit_code, result = run_scope_check(PROJECT_ROOT, "M4")

    assert exit_code == 0
    assert result == {"milestone": "M4", "status": "ok", "violations": []}

    runtime_config = tmp_path / "configs" / "models" / "current.yaml"
    runtime_config.parent.mkdir(parents=True)
    runtime_config.write_text('model = "lightgbm"\ntransport = "mcp"\n', encoding="utf-8")
    exit_code, result = run_scope_check(tmp_path, "M0")

    assert exit_code == 2
    assert result == {
        "milestone": "M0",
        "status": "rejected",
        "violations": [
            {
                "available_in": "M5",
                "dependency": "lightgbm",
                "kind": "premature_dependency",
                "path": "configs/models/current.yaml",
            },
            {
                "available_in": "M7",
                "dependency": "mcp",
                "kind": "premature_dependency",
                "path": "configs/models/current.yaml",
            },
        ],
    }

    source_file = tmp_path / "quantlab" / "runner.py"
    source_file.parent.mkdir()
    source_file.write_text("import lightgbm\n", encoding="utf-8")
    exit_code, result = run_scope_check(tmp_path, "M0")

    assert exit_code == 2
    assert result == {
        "milestone": "M0",
        "status": "rejected",
        "violations": [
            {
                "available_in": "M5",
                "dependency": "lightgbm",
                "kind": "premature_dependency",
                "path": "configs/models/current.yaml",
            },
            {
                "available_in": "M7",
                "dependency": "mcp",
                "kind": "premature_dependency",
                "path": "configs/models/current.yaml",
            },
            {
                "available_in": "M5",
                "dependency": "lightgbm",
                "kind": "premature_dependency",
                "path": "quantlab/runner.py",
            },
        ],
    }


def test_scope_rejects_forbidden_v1_features(tmp_path: Path) -> None:
    """V1 non-goals must be rejected even after their nominal milestone."""
    forbidden_markers = (
        "live_money",
        "intraday",
        "tick_data",
        "high_frequency",
        "options",
        "futures",
        "forex",
        "crypto",
        "shorting",
        "leverage",
        "borrow_model",
        "reinforcement_learning",
        "lstm",
        "transformer",
        "alternative_data",
        "paid_data",
        "factor_library",
        "arbitrary_strategy_code",
        "agent_swarm",
        "kubernetes",
        "spark",
        "multi_tenancy",
        "tax_accounting",
    )
    source_root = tmp_path / "quantlab"
    source_root.mkdir()
    for marker in forbidden_markers:
        (source_root / f"{marker}.py").touch()

    exit_code, result = run_scope_check(tmp_path, "M9")

    assert exit_code == 2
    assert result["milestone"] == "M9"
    assert result["status"] == "rejected"
    assert result["violations"] == [
        {
            "kind": "forbidden_v1_feature",
            "path": f"quantlab/{marker}.py",
            "rule": marker,
        }
        for marker in forbidden_markers
    ]
