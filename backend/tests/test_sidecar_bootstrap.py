from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
READY_LINE_TIMEOUT_SECONDS = 15
SHUTDOWN_TIMEOUT_SECONDS = 10


def _read_announced_port(process: subprocess.Popen[str]) -> int:
    assert process.stdout is not None
    lines: queue.Queue[str] = queue.Queue()

    def _pump() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            lines.put(line)

    threading.Thread(target=_pump, daemon=True).start()

    while True:
        try:
            line = lines.get(timeout=READY_LINE_TIMEOUT_SECONDS)
        except queue.Empty as exc:  # pragma: no cover - only on real failure
            raise TimeoutError("sidecar did not announce a port in time") from exc
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("event") == "sidecar_ready":
            return int(payload["port"])


@pytest.fixture
def running_sidecar() -> Iterator[int]:
    process = subprocess.Popen(
        [sys.executable, "-m", "app"],
        cwd=BACKEND_ROOT,
        env={
            **os.environ,
            "WEEKLY_REPORT_ENVIRONMENT": "test",
            "WEEKLY_REPORT_HOST": "127.0.0.1",
            "WEEKLY_REPORT_PORT": "0",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        yield _read_announced_port(process)
    finally:
        process.terminate()
        try:
            process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            process.kill()
            process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)


def test_sidecar_announces_a_dynamic_port_and_serves_the_health_contract(
    running_sidecar: int,
) -> None:
    port = running_sidecar

    response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=5)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"
    assert isinstance(body["data"]["version"], str) and body["data"]["version"]


def test_two_consecutive_launches_get_different_dynamic_ports(
    running_sidecar: int,
) -> None:
    first_port = running_sidecar

    process = subprocess.Popen(
        [sys.executable, "-m", "app"],
        cwd=BACKEND_ROOT,
        env={
            **os.environ,
            "WEEKLY_REPORT_ENVIRONMENT": "test",
            "WEEKLY_REPORT_HOST": "127.0.0.1",
            "WEEKLY_REPORT_PORT": "0",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        second_port = _read_announced_port(process)
    finally:
        process.terminate()
        try:
            process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            process.kill()
            process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)

    assert first_port != second_port
