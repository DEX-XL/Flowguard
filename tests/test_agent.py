import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from flowguard.models import Patient, Bed
from flowguard.triage import assess
from flowguard.agent import FlowGuardAgent
from flowguard.adapters.meterless import MeterlessContext
from flowguard.data_gen import make_patients, make_beds


def sick_patient():
    return Patient(patient_id="T-1", age=70, sex="F", chief_complaint="chest pain",
                   heart_rate=128, resp_rate=28, spo2=91, systolic_bp=92,
                   temperature_c=36.8, pain_score=9, arrival_mode="ambulance",
                   telemetry_needed=True, icu_risk_factors=["possible ACS"],
                   minutes_waiting=180)


def well_patient():
    return Patient(patient_id="T-2", age=25, sex="M", chief_complaint="minor laceration",
                   heart_rate=72, resp_rate=14, spo2=99, systolic_bp=120,
                   temperature_c=36.7, pain_score=3, arrival_mode="walk-in",
                   minutes_waiting=20)


def test_sick_scores_higher_than_well():
    assert assess(sick_patient()).esi_level <= 2
    assert assess(well_patient()).esi_level >= 4
    assert assess(sick_patient()).boarding_risk_score > assess(well_patient()).boarding_risk_score


def test_no_assignment_to_occupied_or_wrong_unit():
    beds = [Bed(bed_id="MS-1", unit="MedSurg", occupied=False)]
    out = FlowGuardAgent(context=MeterlessContext()).run(
        [sick_patient()], beds)
    rec = out["results"][0]["recommendation"]
    assert rec["action"] == "escalate"  # MedSurg is below the acuity floor for this patient


def test_isolation_patient_only_gets_isolation_bed():
    p = Patient(patient_id="T-3", age=50, sex="F", chief_complaint="fever and cough",
                heart_rate=95, resp_rate=20, spo2=96, systolic_bp=118,
                temperature_c=38.2, pain_score=2, arrival_mode="walk-in",
                isolation_needed=True, minutes_waiting=90)
    beds = [Bed(bed_id="MS-1", unit="MedSurg"), Bed(bed_id="IS-1", unit="Isolation", isolation_capable=True)]
    out = FlowGuardAgent(context=MeterlessContext()).run([p], beds)
    rec = out["results"][0]["recommendation"]
    assert rec["bed_id"] == "IS-1"


def test_full_demo_run_places_and_escalates():
    out = FlowGuardAgent(context=MeterlessContext()).run(
        make_patients(), make_beds())
    actions = [r["recommendation"]["action"] for r in out["results"]]
    assert "assign" in actions
    assert out["handoff"].startswith("FlowGuard handoff")


if __name__ == "__main__":
    test_sick_scores_higher_than_well()
    test_no_assignment_to_occupied_or_wrong_unit()
    test_isolation_patient_only_gets_isolation_bed()
    test_full_demo_run_places_and_escalates()
    print("All 4 tests passed.")
