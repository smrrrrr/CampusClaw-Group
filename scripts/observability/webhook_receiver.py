#!/usr/bin/env python3
"""告警测试接收器：把 Alertmanager 实际推送的告警原样追加到 JSONL。

只用于证明“规则→Firing→送达”链路；不代表真实负责人已收到。
用法：python scripts/observability/webhook_receiver.py --port 9099 --output logs/alerts.jsonl
"""

import argparse
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    output: Path

    def do_POST(self):
        length = int(self.headers.get("content-length", 0) or 0)
        body = self.rfile.read(length)
        record = {"received_at": datetime.now(timezone.utc).isoformat(), "size": len(body)}
        try:
            payload = json.loads(body)
            record["status"] = payload.get("status")
            record["alerts"] = [
                {"name": item.get("labels", {}).get("alertname"),
                 "state": item.get("status"),
                 "startsAt": item.get("startsAt"),
                 "labels": item.get("labels", {}),
                 "annotations": item.get("annotations", {})}
                for item in payload.get("alerts", [])
            ]
        except ValueError:
            record["raw_prefix"] = body[:200].decode("utf-8", errors="replace")
        self.output.parent.mkdir(parents=True, exist_ok=True)
        with self.output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_):
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9099)
    parser.add_argument("--output", type=Path, default=Path("logs/alerts.jsonl"))
    args = parser.parse_args()
    Handler.output = args.output
    print(f"告警接收器监听 0.0.0.0:{args.port}，写入 {args.output}")
    HTTPServer(("0.0.0.0", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
