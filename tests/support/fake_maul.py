#!/usr/bin/env python3
"""Stand-in Maul binary for Holds tests. No Rust toolchain required."""

from __future__ import annotations

import argparse
import json
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import override

COMPLETION = {
    "id": "chatcmpl-fake-maul",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "refund_request"},
            "finish_reason": "stop",
        }
    ],
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fake-maul")
    parser.add_argument("--config", default="maul.yaml")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)
    config_path = Path(args.config)
    config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    if args.validate:
        return 0
    address = _listen_addr(config_text)
    force_500 = "force_500" in config_text
    host, port_text = address.rsplit(":", 1)
    httpd = ThreadingHTTPServer((host, int(port_text)), _handler(force_500))
    httpd.allow_reuse_address = True
    stop = threading.Event()

    def _handle_signal(_signum: int, _frame: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    stop.wait()
    httpd.shutdown()
    thread.join(timeout=2)
    _write_report(Path("reliability_report.json"), force_500=force_500)
    return 0


def _handler(force_500: bool) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            if force_500:
                body = b'{"error":"injected force_500"}'
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            payload = json.dumps(COMPLETION).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        @override
        def log_message(self, format: str, *args: object) -> None:
            del format, args

    return Handler


def _listen_addr(config_text: str) -> str:
    for line in config_text.splitlines():
        if line.startswith("proxy_listen:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return "127.0.0.1:0"


def _write_report(path: Path, *, force_500: bool) -> None:
    unrecovered = 1 if force_500 else 0
    report = {
        "schema_version": "0.2",
        "run_id": "fake-maul",
        "seed": 7,
        "faults_injected": 1 if force_500 else 0,
        "budget_snapshot": {
            "calls_limit": 20,
            "cost_limit_usd": {"micro_usd": 1_000_000, "display": "$1.000000"},
        },
        "summary": {
            "successful_requests": 0 if force_500 else 1,
            "failed_requests": 1 if force_500 else 0,
            "budget_rejections": 0,
            "recovery_events": 0,
            "unrecovered_sessions": unrecovered,
            "observed_cost_usd": {"micro_usd": 0, "display": "$0.000000"},
        },
        "requests": [
            {
                "path": "/v1/chat/completions",
                "status": 500 if force_500 else 200,
                "fault_injected": "force_500" if force_500 else None,
                "budget_decision": "Allowed",
                "model": "gpt-4o-mini",
                "session_id": "session-a",
                "sequence": 1,
            }
        ],
    }
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
