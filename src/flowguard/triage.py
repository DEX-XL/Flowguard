"""Deterministic, auditable triage and boarding-risk scoring.

The rules here encode the same first-pass logic an ED charge nurse applies:
vital-sign danger zones (NEWS-style), complaint-specific red flags, and
boarding risk driven by acuity + wait time + special needs. Every score
returns its rationale so a clinician can audit or override it. This is
decision support only, never a clinical decision.
"""
from .models import Patient, Assessment

RED_FLAG_COMPLAINTS = {
    "chest pain": ["Possible cardiac event: chest pain presentation"],
    "shortness of breath": ["Respiratory presentation"],
    "stroke symptoms": ["Possible stroke: time-critical pathway"],
    "altered mental status": ["Altered mental status: high-risk presentation"],
    "sepsis suspected": ["Suspected sepsis: bundle clock starts at triage"],
    "gi bleed": ["Active bleeding risk"],
    "overdose": ["Overdose: airway and monitoring priority"],
}


def score_vitals(p: Patient) -> tuple[int, list[str]]:
    """Returns (danger points, rationale). Higher = sicker."""
    pts, why = 0, []
    if p.spo2 < 90:
        pts += 3; why.append(f"SpO2 {p.spo2}% is critically low")
    elif p.spo2 < 94:
        pts += 2; why.append(f"SpO2 {p.spo2}% is low")
    if p.resp_rate >= 30 or p.resp_rate < 9:
        pts += 3; why.append(f"Respiratory rate {p.resp_rate} is in a danger zone")
    elif p.resp_rate >= 22:
        pts += 2; why.append(f"Respiratory rate {p.resp_rate} is elevated")
    if p.heart_rate >= 130 or p.heart_rate < 45:
        pts += 3; why.append(f"Heart rate {p.heart_rate} is in a danger zone")
    elif p.heart_rate >= 110:
        pts += 2; why.append(f"Heart rate {p.heart_rate} is elevated")
    if p.systolic_bp < 90:
        pts += 3; why.append(f"Systolic BP {p.systolic_bp} suggests hypotension / shock risk")
    elif p.systolic_bp >= 200:
        pts += 2; why.append(f"Systolic BP {p.systolic_bp} is severely elevated")
    if p.temperature_c >= 39.5:
        pts += 2; why.append(f"Temperature {p.temperature_c}C is high (infection / sepsis risk)")
    elif p.temperature_c < 35.5:
        pts += 2; why.append(f"Temperature {p.temperature_c}C is low")
    if p.pain_score >= 8:
        pts += 1; why.append(f"Pain score {p.pain_score}/10 is severe")
    return pts, why


def assess(p: Patient) -> Assessment:
    vital_pts, rationale = score_vitals(p)
    complaint = p.chief_complaint.strip().lower()
    red_flags = RED_FLAG_COMPLAINTS.get(complaint, [])
    rationale = red_flags + rationale
    if p.icu_risk_factors:
        rationale.append("ICU risk factors: " + ", ".join(p.icu_risk_factors))
        vital_pts += min(3, len(p.icu_risk_factors))

    # ESI-style level: 1 resuscitation, 2 emergent, 3 urgent, 4 less urgent, 5 non-urgent
    if vital_pts >= 8:
        esi = 1
    elif vital_pts >= 5 or red_flags:
        esi = 2
    elif vital_pts >= 3:
        esi = 3
    elif vital_pts >= 1:
        esi = 4
    else:
        esi = 5

    # Boarding risk: acuity dominates, wait time and special needs compound it.
    risk = (6 - esi) * 14
    risk += min(30, p.minutes_waiting // 6)  # +5 per 30 min waited, capped
    if p.isolation_needed:
        risk += 8; rationale.append("Isolation need narrows the eligible bed pool")
    if p.telemetry_needed:
        risk += 6; rationale.append("Telemetry need narrows the eligible bed pool")
    if p.arrival_mode == "ambulance":
        risk += 4
    risk = max(0, min(100, risk))
    band = "critical" if risk >= 75 else "high" if risk >= 55 else "moderate" if risk >= 35 else "low"
    rationale.append(f"Boarding risk {band} ({risk}/100): ESI {esi}, waited {p.minutes_waiting} min")
    return Assessment(patient_id=p.patient_id, esi_level=esi,
                      boarding_risk=band, boarding_risk_score=risk, rationale=rationale)
