-- FlowGuard's Zetaris Lightning SQL queries (semantic layer, see semantic_layer.yaml)
-- The agent issues exactly these two governed queries per run.

-- 1. Current ED waiting list, unified from ADT + triage vitals
SELECT patient_id, age, sex, chief_complaint, heart_rate, resp_rate, spo2,
       systolic_bp, temperature_c, pain_score, arrival_mode,
       isolation_needed, telemetry_needed, icu_risk_factors, minutes_waiting
FROM semantic.ed_waiting_list
ORDER BY minutes_waiting DESC;

-- 2. Current bed board, unified from bed management + staffing roster
SELECT bed_id, unit, occupied, isolation_capable, telemetry_capable, nurse_ratio_ok
FROM semantic.bed_board;
