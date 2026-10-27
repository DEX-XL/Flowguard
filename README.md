# FlowGuard

**An ED boarding-to-bed agent that can explain why.**

Team Rohit · Open Agent Hackathon 2026 · Track 02: The Agent That Can Explain Why

## The problem

Emergency department boarding, admitted patients waiting hours in the ED for an inpatient bed, is one of the most expensive and dangerous flow problems in hospitals. It delays care for the sickest patients, drives ambulance diversion, and burns out staff. The charge nurse solving it works across four fragmented systems at once: the ADT feed, the bed board, triage vitals in the EHR, and the staffing roster, usually by phone.

FlowGuard's lead builder spent two years as an ICU medical officer watching this problem from the receiving end. FlowGuard is the agent he needed: it watches the whole board, scores every waiting patient, and recommends the best safe bed, with the reasoning written out, or escalates loudly when no safe bed exists.

## What it does

For every run, FlowGuard:

1. **Senses** the ED waiting list and bed board through a unified semantic layer, not four separate systems.
2. **Assesses** each patient: ESI-style acuity from vital-sign danger zones and complaint red flags, plus a 0-100 boarding-risk score (acuity, wait time, isolation and telemetry needs), every point with a written rationale.
3. **Matches** patients to beds under hard capability constraints (a MedSurg bed is never assigned to an ESI 1 patient, an isolation patient only gets an isolation bed, a placement never breaches a nurse ratio), preferring the lowest-acuity bed that is safely sufficient, which preserves scarce ICU beds.
4. **Escalates** instead of forcing an unsafe placement when nothing fits, flagging bed management and the house supervisor.
5. **Hands off** with a 30-second shift summary, and remembers unresolved escalations for the next run.

In the surge demo (same census, bed pool cut to 6), FlowGuard places 5 patients and escalates 5 rather than making unsafe assignments. That refusal behaviour is a feature, and it is tested.

## Quick start

No dependencies beyond Python 3.10+. No API keys. No real patient data, the census is synthetic.

```bash
git clone <this repo> && cd flowguard
PYTHONPATH=src python3 -m flowguard.demo     # console run + data/last_run.json
PYTHONPATH=src python3 -m flowguard.server   # dashboard at http://localhost:8765
python3 tests/test_agent.py                  # 4 tests, all passing
```

Dashboard: run the agent on a normal census or a surge census and read the auditable rationale for every decision.

## Architecture

```
ADT feed ─┐
Bed board ┼─> Zetaris semantic layer ─> FlowGuard agent ─> recommendations
Vitals ───┤    (governed SQL)            │ triage scoring      + rationale
Roster ───┘                              │ bed matching        + escalations
                                         │ Meterless context:  + handoff
                                         │  World Model (event-sourced board)
                                         │  Markovian (patient state machine)
                                         │  H-MEM (handoff / escalation memory)
                                         │  Scout Intent (risk-checked routing)
```

- `src/flowguard/triage.py` deterministic, auditable acuity and boarding-risk scoring
- `src/flowguard/bed_match.py` hard constraints first, best-fit scoring second
- `src/flowguard/agent.py` the sense-assess-act-remember loop
- `src/flowguard/adapters/zetaris.py` + `zetaris/` the semantic layer and its SQL
- `src/flowguard/adapters/meterless.py` the four Meterless engines, local-first
- `dashboard/` the bed-board UI · `tests/` the conformance-style test suite

## Sponsor technology

**Zetaris** is FlowGuard's data layer. The semantic model in `zetaris/semantic_layer.yaml` unifies the four fragmented hospital sources into two governed entities, and the agent queries only those, using the Lightning SQL in `zetaris/queries.sql`. Unique to this build: the minimum-necessary field list is part of the semantic model, so the agent structurally cannot see data it does not need. With `ZETARIS_API_URL` and `ZETARIS_API_KEY` set, the adapter calls a live Zetaris Cloud Gateway endpoint; without them, the same queries resolve to the bundled synthetic dataset, labelled `synthetic-fallback` in every response, never passed off as live data.

**Meterless** is FlowGuard's context layer, using all four open engines (see `metadata.json`): the World Model event-sources the bed board so any run replays; the Markovian engine keeps each patient in a bounded state machine (`waiting → assessed → matched | escalated → placed`); H-MEM stores the handoff and unresolved escalations with provenance for the next shift; Scout Intent classifies each action request and risk-checks it, an unassessed patient can never be routed to a bed match. All four run locally in pure Python, per the Meterless open-engine specs, no keys, no cloud.

**NVIDIA**: the scoring and matching core is deliberately deterministic and CPU-only, because a bed recommendation must be reproducible in an audit. NVIDIA technology is the scale path, not a runtime dependency: the same agent loop is designed to serve its natural-language handoff narration from a local NVIDIA NIM endpoint and to run on DGX-class hardware at hospital scale, and Meterless itself is an NVIDIA Inception project whose local-first engines FlowGuard builds on. We state this plainly rather than claiming GPU use we did not need.

**Cursor** was not used for this build.

## Pre-existing components declaration

Built during the hackathon build window (27 Oct 2026) for this submission: all agent code, the semantic layer, the dashboard, tests, deck and video. Pre-existing, declared: the clinical concept and workflow knowledge come from the lead builder's prior work (a 2024 WhatsApp hospital triage bot and a hospital patient-flow agent concept he is developing in a separate hackathon); no code from those projects is reused in this repository. Open-source libraries: none, the build is Python standard library only.

## Safety

Decision support only. FlowGuard recommends; a clinician decides. It uses synthetic data only, contains no PHI, and its scoring rules are transparent and overrideable by design.

## Team

Team Rohit: Rohit Motwani (lead, Rutgers Business School, MS Supply Chain Analytics; medical doctor, two years ICU), Ujjawal Agarwal, Harsh Agrawal.
