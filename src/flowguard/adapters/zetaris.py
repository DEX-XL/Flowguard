"""Zetaris adapter.

Zetaris is the hackathon sponsor data virtualisation platform (Lightning
SQL over a unified semantic layer). FlowGuard defines its hospital semantic
layer in zetaris/semantic_layer.yaml: the ADT feed, bed board, triage
vitals stream and staffing roster, which live in four separate systems in
every real hospital, are exposed as two governed semantic entities
(ed_waiting_list, bed_board). The agent only ever runs the two Lightning
SQL queries in zetaris/queries.sql against that layer; it never queries a
source system directly.

Integration contract used here:
- If ZETARIS_API_KEY and ZETARIS_API_URL are set in the environment, the
  adapter POSTs a natural-language / SQL query to that endpoint and returns
  the JSON rows.
- If they are not set (local demo, judging sandbox), it falls back to the
  bundled synthetic dataset so the agent runs end to end with no secrets.
The fallback is explicit in every response (source="synthetic-fallback"),
never silently presented as live hospital data.
"""
import json
import os
import urllib.request


class ZetarisAdapter:
    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        self.api_url = api_url or os.environ.get("ZETARIS_API_URL", "")
        self.api_key = api_key or os.environ.get("ZETARIS_API_KEY", "")
        self.live = bool(self.api_url and self.api_key)

    def query(self, question: str, fallback_rows: list[dict]) -> dict:
        if not self.live:
            return {"source": "synthetic-fallback", "question": question, "rows": fallback_rows}
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps({"query": question}).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
            method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
        return {"source": "zetaris", "question": question,
                "rows": payload.get("rows", payload if isinstance(payload, list) else [])}
