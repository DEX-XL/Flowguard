"""Bed matching: hard capability constraints first, then best-fit scoring."""
from .models import Patient, Bed, Assessment, Recommendation

UNIT_FOR_ESI = {1: ["ICU", "Stepdown"], 2: ["ICU", "Stepdown", "Telemetry"],
                3: ["Stepdown", "Telemetry", "MedSurg", "Isolation"],
                4: ["Telemetry", "MedSurg", "Isolation"],
                5: ["MedSurg", "Isolation"]}


def _eligible(p: Patient, a: Assessment, b: Bed) -> tuple[bool, list[str]]:
    why_not = []
    if b.occupied:
        why_not.append("occupied")
    if not b.nurse_ratio_ok:
        why_not.append("nurse ratio would be breached")
    if b.unit not in UNIT_FOR_ESI[a.esi_level]:
        why_not.append(f"{b.unit} is below the acuity floor for ESI {a.esi_level}")
    if p.isolation_needed and not b.isolation_capable:
        why_not.append("not isolation-capable")
    if p.telemetry_needed and not b.telemetry_capable and b.unit not in ("ICU", "Stepdown"):
        why_not.append("no telemetry")
    return (len(why_not) == 0), why_not


def recommend(p: Patient, a: Assessment, beds: list[Bed]) -> Recommendation:
    candidates = []
    for b in beds:
        ok, _ = _eligible(p, a, b)
        if not ok:
            continue
        # Prefer the lowest-acuity unit that safely fits: preserves ICU beds.
        unit_order = UNIT_FOR_ESI[a.esi_level]
        score = 100 - unit_order.index(b.unit) * 12
        if p.isolation_needed and b.isolation_capable:
            score += 6
        if p.telemetry_needed and b.telemetry_capable:
            score += 6
        candidates.append((score, b))
    candidates.sort(key=lambda x: (-x[0], x[1].bed_id))

    flags = []
    if a.boarding_risk in ("high", "critical"):
        flags.append(f"Boarding risk {a.boarding_risk}: escalate to bed management / house supervisor")
    if a.esi_level <= 2:
        flags.append("ESI 1-2: notify receiving unit charge nurse directly, do not queue silently")

    if not candidates:
        return Recommendation(
            patient_id=p.patient_id, bed_id=None, unit=None, action="escalate",
            confidence=0.95,
            rationale=["No eligible bed matches the capability constraints right now"] + a.rationale,
            escalation_flags=flags + ["No-bed escalation: open surge protocol / expedite a discharge"])
    score, bed = candidates[0]
    return Recommendation(
        patient_id=p.patient_id, bed_id=bed.bed_id, unit=bed.unit, action="assign",
        confidence=round(min(0.99, score / 100), 2),
        rationale=[f"Best safe fit: {bed.unit} bed {bed.bed_id} preserves higher-acuity beds where possible"] + a.rationale,
        escalation_flags=flags)
