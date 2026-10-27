"""Runnable demo: python -m flowguard.demo"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from flowguard.agent import FlowGuardAgent
from flowguard.adapters.meterless import MeterlessContext
from flowguard.data_gen import make_patients, make_beds


def main():
    agent = FlowGuardAgent(context=MeterlessContext())
    out = agent.run(make_patients(), make_beds())
    print(out["handoff"])
    print()
    for r in out["results"]:
        a, rec, p = r["assessment"], r["recommendation"], r["patient"]
        print(f"{p['patient_id']}  ESI {a['esi_level']}  risk {a['boarding_risk_score']:>3} ({a['boarding_risk']:<8}) "
              f"{p['chief_complaint']:<24} -> {rec['action'].upper():<8} {rec['bed_id'] or '-'}")
        for line in rec["rationale"][:2]:
            print(f"    - {line}")
        for flag in rec["escalation_flags"]:
            print(f"    ! {flag}")
    with open("data/last_run.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nFull run written to data/last_run.json")


if __name__ == "__main__":
    main()
