"""Configuration for Retrieval-Grounded QA benchmark."""

from dataclasses import dataclass, field
from typing import List, Optional

# Strict grounding prompt for retrieval-grounded QA
PROMPT_TEMPLATE = """Answer the question using only the information in the context.

Context:
{context}

Question:
{question}

Answer:"""


@dataclass
class BenchmarkConfig:
    """Benchmark configuration."""

    # Dataset
    dataset_name: str = "squad"
    dataset_split: str = "validation"
    num_questions: int = 30
    max_context_tokens: int = 300
    max_answer_tokens: int = 10

    # Models
    models: List[str] = field(
        default_factory=lambda: [
            "Qwen/Qwen2.5-Coder-0.5B-Instruct",
            "deepseek-ai/deepseek-coder-1.3b-instruct",
            "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        ]
    )
    optional_baseline: Optional[str] = "google/gemini-1.5-flash"  # API model, skipped on CPU

    # Inference
    temperature: float = 0.0
    top_p: float = 1.0
    max_new_tokens: int = 30
    do_sample: bool = False

    # Device
    device: str = "cpu"

    # Output
    output_dir: str = "results"
    save_per_model: bool = True
