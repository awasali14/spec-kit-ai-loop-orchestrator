# Analyze Convergence Ledger

Feature: `{{ feature_dir }}`  
Ledger revision: `{{ revision }}`  
Ready for implementation: **{{ ready_for_implementation }}**  
Blocking Critical/High findings: **{{ blocking_critical_high }}**

| ID | Severity | Status | Category | Finding | Artifacts |
|---|---|---|---|---|---|
| {{ id }} | {{ severity }} | {{ status }} | {{ category }} | {{ title }} | {{ artifact_refs }} |

The JSON ledger is authoritative. Generate this view with
`scripts/analyze_ledger.py render`; do not edit status or readiness here.
