from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Task:
    task_id: str
    dataset: str
    problem_text: str
    entry_point: str
    starter_code: str
    test_code: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GenerationConfig:
    temperature: float = 0.2
    max_new_tokens: int = 256
    min_new_tokens: int = 48
    top_p: float = 1.0
    seed: int = 42
    profile: str = "default"
    adaptive_max_new_tokens: bool = False


@dataclass(slots=True)
class ModelSpec:
    label: str
    kind: str
    model_name: str
    load_in_4bit: bool = False
    use_chat_template: bool = False
    api_key_env: str = "GEMINI_API_KEY"
    max_input_tokens: int | None = None
    input_cost_per_1k_tokens: float = 0.0
    output_cost_per_1k_tokens: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationConfig:
    human_eval_sample: int = 15
    mbpp_sample: int = 15
    time_budget_minutes: int = 15
    execution_timeout_seconds: int = 10
    seed: int = 42
    prompt_variant: str = "default"
    generations_per_task: int = 1
    reproducibility_retries: int = 0
    blocked_imports: list[str] = field(
        default_factory=lambda: [
            "subprocess",
            "socket",
            "requests",
            "urllib",
            "httpx",
            "aiohttp",
            "ftplib",
            "telnetlib",
            "shutil",
        ]
    )
    blocked_calls: list[str] = field(
        default_factory=lambda: [
            "os.system",
            "os.remove",
            "os.rmdir",
            "os.unlink",
            "os.removedirs",
            "shutil.rmtree",
            "subprocess.run",
            "subprocess.Popen",
            "subprocess.call",
            "socket.socket",
            "requests.get",
            "requests.post",
            "urllib.request.urlopen",
        ]
    )


@dataclass(slots=True)
class RunConfig:
    evaluation: EvaluationConfig
    generation: GenerationConfig
    models: list[ModelSpec]


@dataclass(slots=True)
class GenerationResult:
    raw_text: str
    code: str
    latency_seconds: float
    output_tokens: int
    tokens_per_second: float
    input_tokens: int = 0
    output_cost: float = 0.0


@dataclass(slots=True)
class SafetyReport:
    is_safe: bool
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TaskRunResult:
    model_label: str
    model_name: str
    dataset: str
    task_id: str
    attempted: bool
    completed: bool
    passed: bool
    status: str
    prompt: str
    prompt_variant: str
    entry_point: str
    raw_output: str
    generated_code: str
    latency_seconds: float
    tokens_per_second: float
    output_tokens: int
    input_tokens: int
    estimated_cost: float
    peak_ram_gb: float
    format_compliant: bool
    signature_compliant: bool
    instruction_adherent: bool
    deterministic_reproducible: bool | None
    self_consistency_score: float | None
    unsafe: bool
    unsafe_reasons: list[str] = field(default_factory=list)
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BenchmarkTableManifest:
    schema_version: str = "1.0"
    exported_at: str = ""
    source_run_dir: str = ""
    source_summary_path: str = ""
    source_report_path: str = ""
    source_config_snapshot_path: str | None = None
    source_config_path: str | None = None
    source_runs: list[dict[str, Any]] = field(default_factory=list)
    deprecated_runs: list[dict[str, Any]] = field(default_factory=list)
    evaluation: dict[str, Any] = field(default_factory=dict)
    generation: dict[str, Any] = field(default_factory=dict)
    models: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
