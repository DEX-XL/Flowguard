"""Zero-dependency demo server: python -m flowguard.server (port 8765).

Serves the bed-board dashboard and a JSON API:
  GET /api/run    -> one full agent run on synthetic data
  GET /api/run?surge=1 -> same census against a reduced bed pool (escalations)
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from flowguard.agent import FlowGuardAgent
from flowguard.adapters.meterless import MeterlessContext
from flowguard.data_gen import make_patients, make_beds

DASH = os.path.join(os.path.dirname(__file__), "..", "..", "dashboard", "index.html")


def run_payload(surge: bool) -> dict:
    beds = make_beds()
    if surge:
        beds = [b for b in beds if b.bed_id in
                ("IC-1", "IC-7", "ST-5", "TE-11", "ME-19", "IS-29")]
    agent = FlowGuardAgent(context=MeterlessContext())
    out = agent.run(make_patients(10), beds)
    out["beds_after"] = beds
    return json.loads(json.dumps(out, default=lambda o: o.to_dict()))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            surge = parse_qs(parsed.query).get("surge", ["0"])[0] == "1"
            body = json.dumps(run_payload(surge)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            with open(DASH, "rb") as fh:
                body = fh.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    print("FlowGuard dashboard at http://localhost:8765  (API: /api/run, /api/run?surge=1)")
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
