from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TEXT_COLUMNS = ("text", "sentence", "description", "content", "body")
DEFAULT_LABEL_COLUMNS = ("label", "target", "class", "category")
DEFAULT_SEED = 42

BUILTIN_SAMPLE_PLANS = {
    "fast15": {
        "SST-2": 3,
        "Emotion": 1,
        "AG News": 1,
    },
    "full": {
        "SST-2": 100,
        "Emotion": 40,
        "AG News": 50,
        "BANKING77": 2,
    },
}


@dataclass
class UserDatasetConfig:
    path: Path
    dataset_name: str = "uploaded-dataset"
    task_type: str = "Custom"
    text_column: str | None = None
    label_column: str | None = None
    labels: list[str] = field(default_factory=list)
    sample_per_class: int | None = None
    max_samples: int | None = None
    seed: int = DEFAULT_SEED

