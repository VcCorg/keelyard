"""check_health() must probe TCP ports concurrently.

With 9 MCP services and a 2s per-port timeout, sequential probes stacked to
~18s — longer than the 10s dashboard/banner poll — and made status look
stale. This test pins the concurrent behaviour so a regression is loud.
"""

import time

from src.services import mcp_service


class _StubSrv:
    def __init__(self, name, host, port):
        self.name = name
        self.container_name = f"keel-{name}"
        self.container_status = None
        self._probe = (host, port)


def _stub_servers(names):
    return [_StubSrv(n, "localhost", 8100 + i) for i, n in enumerate(names)]


def test_ports_probed_in_parallel(monkeypatch):
    """5 slow ports probed together should take much less than serial."""
    names = ["a", "b", "c", "d", "e"]
    servers = _stub_servers(names)

    # Everything below removes the real network/docker/auth surface so we're
    # measuring only the concurrency of the port probes.
    monkeypatch.setattr(mcp_service, "list_mcp_servers", lambda: servers)
    monkeypatch.setattr(mcp_service, "_get_docker_status", lambda: {})
    monkeypatch.setattr(mcp_service, "_load_stack_env", lambda: {})
    monkeypatch.setattr(mcp_service, "_probe_auth", lambda name, env: ("n/a", ""))
    monkeypatch.setattr(mcp_service, "_probe_target", lambda s: s._probe)

    calls = []

    def slow_probe(host, port, timeout=2.0):
        calls.append((host, port, time.monotonic()))
        time.sleep(0.5)  # simulate a 500ms probe
        return False, f"Port {port} unreachable: timed out"

    monkeypatch.setattr(mcp_service, "_check_port", slow_probe)

    start = time.monotonic()
    results = mcp_service.check_health()
    elapsed = time.monotonic() - start

    # Serial would be 5 × 0.5s = 2.5s. Parallel should be closer to one probe.
    assert elapsed < 1.5, f"port probes were not parallelized (took {elapsed:.2f}s)"
    assert len(results) == 5
    assert all(not r.healthy for r in results)
    assert len(calls) == 5
