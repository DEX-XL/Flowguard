from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Patient:
    patient_id: str
    age: int
    sex: str
    chief_complaint: str
    heart_rate: int
    resp_rate: int
    spo2: int
    systolic_bp: int
    temperature_c: float
    pain_score: int  # 0-10
    arrival_mode: str  # walk-in | ambulance | transfer
    isolation_needed: bool = False
    telemetry_needed: bool = False
    icu_risk_factors: list = field(default_factory=list)
    minutes_waiting: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass
class Bed:
    bed_id: str
    unit: str  # ICU | Stepdown | Telemetry | MedSurg | Isolation
    occupied: bool = False
    isolation_capable: bool = False
    telemetry_capable: bool = False
    nurse_ratio_ok: bool = True

    def to_dict(self):
        return asdict(self)


@dataclass
class Assessment:
    patient_id: str
    esi_level: int  # 1 (most urgent) to 5
    boarding_risk: str  # low | moderate | high | critical
    boarding_risk_score: int  # 0-100
    rationale: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class Recommendation:
    patient_id: str
    bed_id: Optional[str]
    unit: Optional[str]
    action: str  # assign | escalate | wait
    confidence: float
    rationale: list = field(default_factory=list)
    escalation_flags: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
