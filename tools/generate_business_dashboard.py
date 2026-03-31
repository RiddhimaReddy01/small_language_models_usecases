from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

LEGACY_BENCHMARK_ROOT = ROOT / "model_runs" / "benchmark_75"
BENCHMARK_ROOT = LEGACY_BENCHMARK_ROOT if LEGACY_BENCHMARK_ROOT.exists() else ROOT / "model_runs"
OUTPUT_ROOT = BENCHMARK_ROOT / "business_analytics"
MODELS = [
    "tinyllama_1.1b",
    "qwen2.5_1.5b",
    "phi3_mini",
    "llama_llama-3.3-70b-versatile",
]
DISPLAY_NAMES = {
    "tinyllama_1.1b": "tinyllama:1.1b",
    "qwen2.5_1.5b": "qwen2.5:1.5b",
    "phi3_mini": "phi3:mini",
    "llama_llama-3.3-70b-versatile": "groq:llama-3.3-70b-versatile",
}
BASELINE_KEY = "llama_llama-3.3-70b-versatile"
SUPPORTED_TASKS = {
    "classification",
    "maths",
    "information_extraction",
    "instruction_following",
    "retrieval_grounded",
    "summarization",
    "code_generation",
    "text_generation",
}

# Explicit, editable proxy assumptions for economic analysis.
SUCCESS_VALUE_USD = 0.0500
FAILURE_LOSS_USD = 0.2000
LATENCY_COST_PER_SEC_USD = 0.0001
LOCAL_INFERENCE_COST_PER_SEC_USD = 0.0002
BASELINE_API_COST_PER_QUERY_USD = 0.0035


@dataclass
class ModelEconomics:
    task: str
    model_key: str
    display_name: str
    capability: float
    risk: float
    latency_sec: float
    throughput_qps: float
    direct_cost_usd: float
    cost_per_correct_usd: float | None
    cost_per_safe_query_usd: float | None
    expected_value_usd: float
    expected_loss_usd: float
    certified_limit_bin: int | None
    confidence_quadrant: str


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sample: dict[str, dict[str, Any]] = {}
    for row in rows:
        sample_id = str(row.get("sample_id"))
        existing = by_sample.get(sample_id)
        if existing is None:
            by_sample[sample_id] = row
            continue
        existing_timestamp = str(existing.get("timestamp") or "")
        row_timestamp = str(row.get("timestamp") or "")
        if row_timestamp >= existing_timestamp:
            by_sample[sample_id] = row
    return list(by_sample.values())


def _avg_latency(task_dir: Path, model_key: str) -> float:
    rows = _dedupe_rows(_read_jsonl(task_dir / model_key / "outputs.jsonl"))
    latencies = [float(row.get("latency_sec") or 0.0) for row in rows if row.get("latency_sec") is not None]
    return mean(latencies) if latencies else 0.0


def _direct_cost_usd(model_key: str, latency_sec: float) -> float:
    if model_key == BASELINE_KEY:
        return BASELINE_API_COST_PER_QUERY_USD
    return latency_sec * LOCAL_INFERENCE_COST_PER_SEC_USD


def _expected_value(capability: float, risk: float, latency_sec: float, direct_cost_usd: float) -> float:
    return (
        SUCCESS_VALUE_USD * capability
        - FAILURE_LOSS_USD * risk
        - LATENCY_COST_PER_SEC_USD * latency_sec
        - direct_cost_usd
    )


def _expected_loss(risk: float, latency_sec: float, direct_cost_usd: float) -> float:
    return FAILURE_LOSS_USD * risk + LATENCY_COST_PER_SEC_USD * latency_sec + direct_cost_usd


def _is_dominated(candidate: ModelEconomics, others: list[ModelEconomics]) -> bool:
    for other in others:
        if other.model_key == candidate.model_key:
            continue
        no_worse = (
            other.capability >= candidate.capability
            and other.risk <= candidate.risk
            and other.latency_sec <= candidate.latency_sec
            and other.direct_cost_usd <= candidate.direct_cost_usd
        )
        strictly_better = (
            other.capability > candidate.capability
            or other.risk < candidate.risk
            or other.latency_sec < candidate.latency_sec
            or other.direct_cost_usd < candidate.direct_cost_usd
        )
        if no_worse and strictly_better:
            return True
    return False


def _bin_distribution(counts_by_bin: dict[str, Any]) -> dict[int, float]:
    counts = {int(bin_id): int(count) for bin_id, count in counts_by_bin.items()}
    total = sum(counts.values())
    if total == 0:
        return {bin_id: 0.0 for bin_id in counts}
    return {bin_id: count / total for bin_id, count in counts.items()}


def _blended_strategy(
    slm: ModelEconomics,
    baseline: ModelEconomics,
    slm_thresholds: dict[str, Any],
    baseline_thresholds: dict[str, Any],
    limit_bin: int | None,
) -> dict[str, Any]:
    if limit_bin is None:
        return {
            "route_share_to_slm": 0.0,
            "blended_capability": baseline.capability,
            "blended_risk": baseline.risk,
            "blended_latency_sec": baseline.latency_sec,
            "blended_direct_cost_usd": baseline.direct_cost_usd,
            "blended_expected_value_usd": baseline.expected_value_usd,
            "blended_expected_loss_usd": baseline.expected_loss_usd,
            "savings_vs_all_baseline_usd": 0.0,
            "expected_value_delta_vs_all_baseline_usd": 0.0,
            "break_even_failure_loss_usd": None,
        }

    distribution = _bin_distribution(slm_thresholds["counts_by_bin"])
    slm_cap_curve = {int(k): float(v) for k, v in slm_thresholds["expected_capability_curve"].items()}
    slm_risk_curve = {int(k): float(v) for k, v in slm_thresholds["expected_risk_curve"].items()}
    base_cap_curve = {int(k): float(v) for k, v in baseline_thresholds["expected_capability_curve"].items()}
    base_risk_curve = {int(k): float(v) for k, v in baseline_thresholds["expected_risk_curve"].items()}

    blended_capability = 0.0
    blended_risk = 0.0
    route_share = 0.0
    for bin_id, prob in distribution.items():
        use_slm = bin_id <= limit_bin
        route_share += prob if use_slm else 0.0
        blended_capability += prob * (slm_cap_curve.get(bin_id, slm.capability) if use_slm else base_cap_curve.get(bin_id, baseline.capability))
        blended_risk += prob * (slm_risk_curve.get(bin_id, slm.risk) if use_slm else base_risk_curve.get(bin_id, baseline.risk))

    blended_latency_sec = route_share * slm.latency_sec + (1.0 - route_share) * baseline.latency_sec
    blended_direct_cost_usd = route_share * slm.direct_cost_usd + (1.0 - route_share) * baseline.direct_cost_usd
    blended_expected_value_usd = _expected_value(blended_capability, blended_risk, blended_latency_sec, blended_direct_cost_usd)
    blended_expected_loss_usd = _expected_loss(blended_risk, blended_latency_sec, blended_direct_cost_usd)

    delta_cap = blended_capability - baseline.capability
    delta_risk = blended_risk - baseline.risk
    delta_cost = blended_direct_cost_usd - baseline.direct_cost_usd
    delta_latency = blended_latency_sec - baseline.latency_sec
    break_even_failure_loss_usd = None
    if delta_risk > 0:
        break_even_failure_loss_usd = (
            SUCCESS_VALUE_USD * delta_cap - delta_cost - LATENCY_COST_PER_SEC_USD * delta_latency
        ) / delta_risk

    return {
        "route_share_to_slm": route_share,
        "route_share_to_baseline": 1.0 - route_share,
        "abstention_share_estimate": 0.0,
        "blended_capability": blended_capability,
        "blended_risk": blended_risk,
        "blended_latency_sec": blended_latency_sec,
        "blended_direct_cost_usd": blended_direct_cost_usd,
        "blended_expected_value_usd": blended_expected_value_usd,
        "blended_expected_loss_usd": blended_expected_loss_usd,
        "savings_vs_all_baseline_usd": baseline.direct_cost_usd - blended_direct_cost_usd,
        "expected_value_delta_vs_all_baseline_usd": blended_expected_value_usd - baseline.expected_value_usd,
        "break_even_failure_loss_usd": break_even_failure_loss_usd,
        "interpretation_note": "Blended economics uses certified limit bin. Abstention lane is reported but not priced separately here.",
    }


def _format_money(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"${value:.4f}"


def _format_float(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.3f}"


def _plot_task_pareto(task: str, models: list[ModelEconomics], output_path: Path) -> None:
    plt.figure(figsize=(8, 6))
    plt.xlabel("Direct Cost per Query (USD)")
    plt.ylabel("Expected Value per Query (USD)")
    plt.title(f"{task} Pareto View")
    plt.grid(True, alpha=0.3)

    for model in models:
        color = "tab:red" if model.model_key == BASELINE_KEY else "tab:blue"
        plt.scatter(
            [model.direct_cost_usd],
            [model.expected_value_usd],
            s=max(80, 1200 * model.throughput_qps),
            color=color,
            alpha=0.8,
            edgecolor="black",
            linewidth=0.8,
        )
        plt.annotate(
            (
                f"{model.display_name}\n"
                f"cap={model.capability:.2f}, risk={model.risk:.2f}\n"
                f"lat={model.latency_sec:.2f}s, thr={model.throughput_qps:.2f} q/s"
            ),
            (model.direct_cost_usd, model.expected_value_usd),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    dashboard: dict[str, Any] = {
        "assumptions": {
            "success_value_usd": SUCCESS_VALUE_USD,
            "failure_loss_usd": FAILURE_LOSS_USD,
            "latency_cost_per_sec_usd": LATENCY_COST_PER_SEC_USD,
            "local_inference_cost_per_sec_usd": LOCAL_INFERENCE_COST_PER_SEC_USD,
            "baseline_api_cost_per_query_usd": BASELINE_API_COST_PER_QUERY_USD,
            "note": "These are explicit proxy economics layered on top of SDDF outputs; edit them to reflect your real business environment.",
        },
        "tasks": {},
    }

    lines = [
        "# Benchmark 75 Business Dashboard",
        "",
        "This dashboard uses SDDF capability/risk plus explicit proxy economics to estimate unit economics, expected value/loss, and break-even routing.",
        "",
        "## Assumptions",
        "",
        f"- Success value per correct query: {_format_money(SUCCESS_VALUE_USD)}",
        f"- Failure loss per semantic failure: {_format_money(FAILURE_LOSS_USD)}",
        f"- Latency cost per second: {_format_money(LATENCY_COST_PER_SEC_USD)}",
        f"- Local inference cost per second: {_format_money(LOCAL_INFERENCE_COST_PER_SEC_USD)}",
        f"- Baseline API cost per query: {_format_money(BASELINE_API_COST_PER_QUERY_USD)}",
        "",
    ]

    for task_dir in sorted(p for p in BENCHMARK_ROOT.iterdir() if p.is_dir()):
        if task_dir.name not in SUPPORTED_TASKS:
            continue
        routing_path = task_dir / "sddf" / "routing_policy.json"
        if not routing_path.exists():
            continue

        routing = _read_json(routing_path)
        decision = routing["decision_matrix"]
        thresholds = routing["thresholds"]
        task_models: list[ModelEconomics] = []
        for model_key in MODELS:
            if model_key not in decision:
                continue
            latency_sec = _avg_latency(task_dir, model_key)
            throughput_qps = 0.0 if latency_sec <= 0 else 1.0 / latency_sec
            direct_cost_usd = _direct_cost_usd(model_key, latency_sec)
            capability = float(decision[model_key]["avg_expected_capability"])
            risk = float(decision[model_key]["avg_expected_risk"])
            task_models.append(
                ModelEconomics(
                    task=task_dir.name,
                    model_key=model_key,
                    display_name=DISPLAY_NAMES[model_key],
                    capability=capability,
                    risk=risk,
                    latency_sec=latency_sec,
                    throughput_qps=throughput_qps,
                    direct_cost_usd=direct_cost_usd,
                    cost_per_correct_usd=None if capability <= 0 else direct_cost_usd / capability,
                    cost_per_safe_query_usd=None if risk >= 1 else direct_cost_usd / max(1e-9, (1.0 - risk)),
                    expected_value_usd=_expected_value(capability, risk, latency_sec, direct_cost_usd),
                    expected_loss_usd=_expected_loss(risk, latency_sec, direct_cost_usd),
                    certified_limit_bin=decision[model_key]["confidence_certified_routing_policy"].get("limit_bin"),
                    confidence_quadrant=decision[model_key].get("tau_quadrant", decision[model_key].get("confidence_quadrant", "NA")),
                )
            )

        if not task_models:
            dashboard["tasks"][task_dir.name] = {
                "status": "no_models_in_decision_matrix",
                "frontier_models": [],
                "models": [],
            }
            continue

        baseline = next((model for model in task_models if model.model_key == BASELINE_KEY), None)
        model_payloads: list[dict[str, Any]] = []
        frontier_models: list[str] = []
        for model in task_models:
            dominated = _is_dominated(model, task_models)
            if not dominated:
                frontier_models.append(model.display_name)
            policy = decision[model.model_key].get("confidence_certified_routing_policy", {})
            certified_strategy: dict[str, Any]
            if baseline is None:
                certified_strategy = {
                    "route_share_to_slm": None,
                    "route_share_to_baseline": None,
                    "abstention_share_estimate": None,
                    "blended_capability": None,
                    "blended_risk": None,
                    "blended_latency_sec": None,
                    "blended_direct_cost_usd": None,
                    "blended_expected_value_usd": None,
                    "blended_expected_loss_usd": None,
                    "savings_vs_all_baseline_usd": None,
                    "expected_value_delta_vs_all_baseline_usd": None,
                    "break_even_failure_loss_usd": None,
                    "interpretation_note": "Baseline missing in decision matrix for this task.",
                }
            else:
                certified_strategy = _blended_strategy(
                    model,
                    baseline,
                    thresholds[model.model_key],
                    thresholds[baseline.model_key],
                    model.certified_limit_bin,
                )
            certified_strategy.update(
                {
                    "limit_bin": policy.get("limit_bin"),
                    "limit_difficulty": policy.get("limit_difficulty"),
                    "abstention_band_half_width": policy.get("abstention_band_half_width", 0.0),
                    "risk_gate_pass": policy.get("risk_gate_pass"),
                    "capability_gate_pass": policy.get("capability_gate_pass"),
                }
            )
            model_payloads.append(
                {
                    "model": model.display_name,
                    "capability": model.capability,
                    "risk": model.risk,
                    "latency_sec": model.latency_sec,
                    "throughput_qps": model.throughput_qps,
                    "direct_cost_usd": model.direct_cost_usd,
                    "cost_per_correct_usd": model.cost_per_correct_usd,
                    "cost_per_safe_query_usd": model.cost_per_safe_query_usd,
                    "expected_value_usd": model.expected_value_usd,
                    "expected_loss_usd": model.expected_loss_usd,
                    "confidence_quadrant": model.confidence_quadrant,
                    "certified_limit_bin": model.certified_limit_bin,
                    "pareto_status": "frontier" if not dominated else "dominated",
                    "confidence_certified_strategy": certified_strategy,
                }
            )

        dashboard["tasks"][task_dir.name] = {
            "status": "ok" if baseline is not None else "baseline_missing",
            "frontier_models": frontier_models,
            "models": model_payloads,
        }
        _plot_task_pareto(task_dir.name, task_models, OUTPUT_ROOT / f"{task_dir.name}_pareto.png")

        lines.extend(
            [
                f"## {task_dir.name}",
                "",
                f"- Pareto frontier: {', '.join(frontier_models)}",
                f"- Task status: {dashboard['tasks'][task_dir.name]['status']}",
                f"- Chart: `{(OUTPUT_ROOT / f'{task_dir.name}_pareto.png').relative_to(ROOT)}`",
                "",
                "| Model | Cap | Risk | Latency (s) | Throughput (q/s) | Direct Cost | EV | Pareto | Limit Bin | Delta | Route Share SLM |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
            ]
        )
        for payload in model_payloads:
            lines.append(
                "| {model} | {cap} | {risk} | {lat} | {thr} | {cost} | {ev} | {pareto} | {limit_bin} | {delta} | {cert} |".format(
                    model=payload["model"],
                    cap=_format_float(payload["capability"]),
                    risk=_format_float(payload["risk"]),
                    lat=_format_float(payload["latency_sec"]),
                    thr=_format_float(payload["throughput_qps"]),
                    cost=_format_money(payload["direct_cost_usd"]),
                    ev=_format_money(payload["expected_value_usd"]),
                    pareto=payload["pareto_status"],
                    limit_bin=payload.get("certified_limit_bin") if payload.get("certified_limit_bin") is not None else "NA",
                    delta=_format_float(payload["confidence_certified_strategy"].get("abstention_band_half_width")),
                    cert=_format_float(payload["confidence_certified_strategy"].get("route_share_to_slm")),
                )
            )
        lines.append("")

    (OUTPUT_ROOT / "dashboard.json").write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
    (OUTPUT_ROOT / "dashboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote business dashboard for {len(dashboard['tasks'])} tasks to {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
