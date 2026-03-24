# Canonical Model Ladder

This repo uses the following canonical model ladder across all tasks.

## Ladder

1. `SLM-0`: 0.5B tiny model
2. `SLM-1`: Qwen 2B-class model
3. `SLM-2`: Phi 3B-class model
4. `BASELINE`: Groq-hosted LLM

## Intended Use

- `SLM-0`
  - fastest and cheapest local route
  - first candidate for low-risk, low-difficulty inputs
- `SLM-1`
  - mid-tier local route
  - preferred when `SLM-0` fails risk or capability thresholds
- `SLM-2`
  - strongest local SLM route
  - preferred when more capability is needed before escalation
- `BASELINE`
  - reference quality ceiling
  - fallback when no SLM satisfies `tau_risk` then `tau_cap`

## Routing Policy

For each task example:

1. Evaluate models in size order: `SLM-0 -> SLM-1 -> SLM-2 -> BASELINE`
2. Apply the risk gate first using `tau_risk`
3. Apply the capability gate second using `tau_cap`
4. Select the smallest model that passes both gates
5. Escalate to `BASELINE` if no SLM qualifies

## Required Reporting

Every task should report results for all four ladder entries using:
- task-specific capability metrics
- semantic risk metrics
- latency, throughput, and cost
- prompt configuration
- model configuration
- hardware/runtime configuration
- SDDF artifacts and routing outputs
