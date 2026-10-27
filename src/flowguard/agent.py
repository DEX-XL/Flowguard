"""FlowGuard agent: orchestrates triage, bed matching, escalation, handoff.

Loop per run:
  1. SENSE   Pull the ED waiting list and bed board through the Zetaris
             unified semantic layer (one governed query per source).
  2. CONTEXT Register everything in the Meterless World Model (event
             sourced), so the run is replayable.
  3. ASSESS  Score every waiting patient (triage + boarding risk); each
             patient moves through the Markovian state machine.
  4. ACT     Scout Intent risk-checks each placement, then the matcher
             assigns the best safe bed or escalates.
  5. REMEMBER Write the handoff and any unresolved escalations to H-MEM
             with provenance, for the next run / next shift.
"""
from .models import Patient, Bed
from .triage import assess
from .bed_match import recommend
from .adapters.zetaris import ZetarisAdapter
from .adapters.meterless import MeterlessContext


class FlowGuardAgent:
    def __init__(self, zetaris: ZetarisAdapter | None = None,
                 context: MeterlessContext | None = None):
        self.zetaris = zetaris or ZetarisAdapter()
        self.ctx = context or MeterlessContext()

    def run(self, patients: list[Patient], beds: list[Bed]) -> dict:
        # SENSE, through the governed semantic layer (synthetic fallback offline)
        self.zetaris.query("SELECT * FROM semantic.ed_waiting_list", [p.to_dict() for p in patients])
        self.zetaris.query("SELECT * FROM semantic.bed_board", [b.to_dict() for b in beds])

        # CONTEXT: event-source the world
        for b in beds:
            self.ctx.world.apply("bed_registered", b.to_dict())
        for p in patients:
            self.ctx.world.apply("patient_arrived", p.to_dict())

        results, escalations = [], 0
        working_beds = [Bed(**b.to_dict()) for b in beds]
        assessed = sorted(((assess(p), p) for p in patients),
                          key=lambda x: -x[0].boarding_risk_score)
        assessed_ids = {p.patient_id for _, p in assessed}
        for assessment, patient in assessed:
            self.ctx.markov.transition(patient.patient_id, "assessed")
            route = self.ctx.scout.classify(f"place patient {patient.patient_id}",
                                            assessed_ids, patient.patient_id)
            if not route["risk_check_passed"]:
                raise RuntimeError("Scout Intent blocked an unassessed placement")
            rec = recommend(patient, assessment, working_beds)
            if rec.action == "assign":
                self.ctx.markov.transition(patient.patient_id, "matched")
                for b in working_beds:
                    if b.bed_id == rec.bed_id:
                        b.occupied = True
                self.ctx.world.apply("bed_assigned",
                                     {"patient_id": patient.patient_id, "bed_id": rec.bed_id})
                self.ctx.markov.transition(patient.patient_id, "placed")
            else:
                escalations += 1
                self.ctx.markov.transition(patient.patient_id, "escalated")
                self.ctx.world.apply("escalation_raised", {"patient_id": patient.patient_id})
                self.ctx.memory.remember(
                    "unresolved_escalation",
                    f"{patient.patient_id}: {patient.chief_complaint}, ESI {assessment.esi_level}, "
                    f"risk {assessment.boarding_risk_score}",
                    {"engine": "H-MEM", "source": "flowguard-agent"})
            results.append({"patient": patient.to_dict(),
                            "assessment": assessment.to_dict(),
                            "recommendation": rec.to_dict()})

        handoff = self._handoff(results, escalations)
        self.ctx.memory.remember("handoff", handoff, {"engine": "H-MEM", "source": "flowguard-agent"})
        return {"results": results, "escalations": escalations, "handoff": handoff,
                "meterless_engines_used": MeterlessContext.ENGINES,
                "world_events": len(self.ctx.world.events)}

    @staticmethod
    def _handoff(results: list[dict], escalations: int) -> str:
        lines = [f"FlowGuard handoff: {len(results)} patients assessed, "
                 f"{sum(1 for r in results if r['recommendation']['action'] == 'assign')} placed, "
                 f"{escalations} escalated."]
        for r in results:
            rec, a, p = r["recommendation"], r["assessment"], r["patient"]
            if rec["action"] == "assign":
                lines.append(f"- {p['patient_id']} (ESI {a['esi_level']}, risk {a['boarding_risk']}) "
                             f"-> {rec['unit']} bed {rec['bed_id']}: {p['chief_complaint']}")
            else:
                lines.append(f"- {p['patient_id']} (ESI {a['esi_level']}, risk {a['boarding_risk']}) "
                             f"ESCALATED, no eligible bed: {p['chief_complaint']}")
        return "\n".join(lines)
