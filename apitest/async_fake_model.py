"""隔离复现专用OpenAI格式假模型，不作为应用运行模式提供。"""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATE = {"fail_enabled": True, "calls": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.reply({"status": "ok", "calls": STATE["calls"]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/control":
            STATE["fail_enabled"] = bool(body["fail_enabled"])
            self.reply({"ok": True})
            return
        STATE["calls"] += 1
        messages = json.dumps(body.get("messages", []))
        time.sleep(2 if "SLOW_ME" in messages else .2)
        content = "invalid-json" if "FAIL_ME" in messages and STATE["fail_enabled"] else '{"score":70,"feedback":"synthetic feedback"}'
        self.reply({"choices": [{"message": {"role": "assistant", "content": content}}]})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
