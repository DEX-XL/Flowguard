"""Meterless open engines, implemented as a local-first context layer.

Meterless (github.com/Meterless/Meterless) publishes four open context
engines as implementation specs with runnable references. FlowGuard builds
its agent context on all four patterns, in pure Python with no API keys,
exactly as the specs intend (local-first, on your own machine):

- WORLD MODEL  Event-sourced state for users, tasks and environments.
               Here: the hospital. Every change (patient arrived, bed
               freed, bed assigned, escalation raised) is an event; the
               current bed board is a fold over the event log, so any
               recommendation can be replayed and audited.
- MARKOVIAN    Bounded state for long runs. Here: each patient is a small
               state machine (waiting -> assessed -> matched | escalated
               -> placed) with a fixed state record, so a shift-long run
               keeps a constant memory footprint per patient.
- H-MEM        Hierarchical memory with provenance and an audit trail.
               Here: every run writes its handoff, placements and
               escalations to memory with provenance (run id, timestamp);
               the next run recalls unresolved escalations first.
- SCOUT INTENT Intent detection, risk checks and tool routing. Here:
               incoming requests ("place this patient", "find an isolation
               bed", "escalate") are classified, risk-checked (never act
               on an unassessed patient), and routed to the right tool.
"""
import time

ALLOWED_TRANSITIONS = {
    "waiting": {"assessed"},
    "assessed": {"matched", "escalated"},
    "matched": {"placed", "escalated"},
    "escalated": {"matched", "placed"},
    "placed": set(),
}


class WorldModel:
    def __init__(self):
        self.events: list[dict] = []
        self.patients: dict[str, dict] = {}
        self.beds: dict[str, dict] = {}

    def apply(self, kind: str, payload: dict) -> dict:
        event = {"seq": len(self.events) + 1, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "kind": kind, "payload": payload}
        self.events.append(event)
        if kind == "patient_arrived":
            self.patients[payload["patient_id"]] = payload
        elif kind == "bed_registered":
            self.beds[payload["bed_id"]] = payload
        elif kind == "bed_assigned":
            if payload["bed_id"] in self.beds:
                self.beds[payload["bed_id"]]["occupied"] = True
        elif kind == "bed_freed":
            if payload["bed_id"] in self.beds:
                self.beds[payload["bed_id"]]["occupied"] = False
        return event


class MarkovianState:
    def __init__(self):
        self.state: dict[str, str] = {}

    def transition(self, patient_id: str, new_state: str) -> str:
        current = self.state.get(patient_id, "waiting")
        if new_state not in ALLOWED_TRANSITIONS[current]:
            raise ValueError(f"Illegal transition {current} -> {new_state} for {patient_id}")
        self.state[patient_id] = new_state
        return new_state


class HMem:
    def __init__(self):
        self.records: list[dict] = []

    def remember(self, kind: str, content: str, provenance: dict) -> dict:
        rec = {"kind": kind, "content": content, "provenance": provenance,
               "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        self.records.append(rec)
        return rec

    def recall(self, kind: str | None = None) -> list[dict]:
        return [r for r in self.records if kind is None or r["kind"] == kind]


class ScoutIntent:
    INTENTS = {
        "place": "bed_match", "assign": "bed_match", "bed for": "bed_match",
        "isolation": "bed_match_isolation", "escalate": "escalation",
        "handoff": "handoff", "summary": "handoff",
    }

    def classify(self, text: str, assessed_patient_ids: set[str], patient_id: str | None = None) -> dict:
        low = text.lower()
        intent = next((v for k, v in self.INTENTS.items() if k in low), "unknown")
        risk_ok = True
        if intent.startswith("bed_match") and patient_id is not None:
            # Risk check: never route a placement for a patient who has not
            # been assessed. This is the Scout contract's safety gate.
            risk_ok = patient_id in assessed_patient_ids
        return {"intent": intent, "routed_tool": intent if risk_ok else "blocked",
                "risk_check_passed": risk_ok, "text": text}


class MeterlessContext:
    """One object bundling the four engines, used by the FlowGuard agent."""

    ENGINES = ["World Model", "Markovian", "H-MEM", "Scout Intent"]

    def __init__(self):
        self.world = WorldModel()
        self.markov = MarkovianState()
        self.memory = HMem()
        self.scout = ScoutIntent()
