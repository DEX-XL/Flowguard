"""Synthetic ED census generator. No real patient data, ever."""
import random
from .models import Patient, Bed

COMPLAINTS = [
    ("chest pain", dict(telemetry_needed=True, icu_risk_factors=["possible ACS"])),
    ("shortness of breath", dict(icu_risk_factors=["respiratory distress"])),
    ("stroke symptoms", dict(icu_risk_factors=["thrombolysis window"])),
    ("sepsis suspected", dict(icu_risk_factors=["lactate pending"])),
    ("abdominal pain", dict()),
    ("fall with hip pain", dict()),
    ("fever and cough", dict(isolation_needed=True)),
    ("gi bleed", dict(icu_risk_factors=["active bleed"])),
    ("altered mental status", dict(icu_risk_factors=["airway risk"])),
    ("minor laceration", dict()),
]


def make_patients(n: int = 8, seed: int = 42) -> list[Patient]:
    rng = random.Random(seed)
    patients = []
    for i in range(n):
        complaint, extra = COMPLAINTS[i % len(COMPLAINTS)]
        sick = i in (0, 3, 8)  # a few genuinely sick patients in the mix
        patients.append(Patient(
            patient_id=f"ED-{101 + i}", age=rng.randint(19, 89),
            sex=rng.choice(["F", "M"]), chief_complaint=complaint,
            heart_rate=rng.randint(105, 135) if sick else rng.randint(62, 102),
            resp_rate=rng.randint(24, 32) if sick else rng.randint(12, 20),
            spo2=rng.randint(88, 93) if sick else rng.randint(95, 100),
            systolic_bp=rng.randint(85, 105) if sick else rng.randint(105, 145),
            temperature_c=round(rng.uniform(38.6, 39.8), 1) if complaint == "sepsis suspected"
            else round(rng.uniform(36.4, 37.8), 1),
            pain_score=rng.randint(5, 9), arrival_mode=rng.choice(["walk-in", "ambulance"]),
            minutes_waiting=rng.choice([25, 60, 95, 140, 210, 260]),
            **extra))
    return patients


def make_beds() -> list[Bed]:
    beds = []
    layout = [("ICU", 4, True, True), ("Stepdown", 6, False, True),
              ("Telemetry", 8, False, True), ("MedSurg", 10, False, False),
              ("Isolation", 3, True, False)]
    n = 1
    for unit, count, iso, tele in layout:
        for _ in range(count):
            beds.append(Bed(bed_id=f"{unit[:2].upper()}-{n}", unit=unit,
                            occupied=(n % 3 == 0), isolation_capable=iso,
                            telemetry_capable=tele, nurse_ratio_ok=True))
            n += 1
    return beds
