# Practical Operator QA

- Execution mode: **{{ mode }}**
- Ready: **{{ ready }}**
- Blocking scenarios: {{ blocking_scenario_ids }}

| Scenario | Status | Severity | Flow blocker |
|---|---|---|---|
| {{ scenario_id }}: {{ title }} | {{ status }} | {{ severity }} | {{ flow_blocker }} |

Every scenario must be exactly `passed`, `failed`, `not_run`, or
`accepted_risk`. An unexecuted scenario must remain `not_run` until an explicit
risk decision is recorded.
