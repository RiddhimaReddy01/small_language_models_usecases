import json
import os
import hashlib


def load_model_registry(config_path):
    with open(config_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_model_config(config_path, model_name):
    registry = load_model_registry(config_path)
    if model_name not in registry:
        available = ", ".join(sorted(registry))
        raise KeyError(f"Unknown model '{model_name}'. Available models: {available}")

    model_config = dict(registry[model_name])
    model_config["model_name"] = model_name
    return model_config


def list_models(config_path):
    registry = load_model_registry(config_path)
    return sorted(registry.keys())


def resolve_model_path(base_dir, model_path, fallback_base_dir=None):
    if os.path.isabs(model_path):
        return model_path
    primary = os.path.normpath(os.path.join(base_dir, model_path))
    if os.path.exists(primary) or fallback_base_dir is None:
        return primary
    fallback = os.path.normpath(os.path.join(fallback_base_dir, model_path))
    return fallback


def file_metadata(path, digest_bytes=1024 * 1024):
    metadata = {
        "path": path,
        "exists": os.path.exists(path),
    }
    if not metadata["exists"]:
        return metadata

    metadata["size_bytes"] = os.path.getsize(path)
    if os.path.isfile(path) and metadata["size_bytes"] > 0:
        hasher = hashlib.sha256()
        with open(path, "rb") as handle:
            remaining = digest_bytes
            while remaining > 0:
                chunk = handle.read(min(65536, remaining))
                if not chunk:
                    break
                hasher.update(chunk)
                remaining -= len(chunk)
        metadata["sha256_prefix"] = hasher.hexdigest()
        metadata["sha256_prefix_bytes"] = digest_bytes
    return metadata
