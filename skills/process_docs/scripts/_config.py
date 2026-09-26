#!/usr/bin/env python3
"""Validated workspace configuration. No personal paths or implicit write root."""
import json
import os
from pathlib import Path
import shutil
import sys

import yaml

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULTS_PATH = SKILL_DIR / "config.defaults.yaml"
PATH_KEYS = ("SYSTEM_DIR", "INPUT_DIR", "WORK_DIR", "CATALOG", "TRASH_DIR", "DRAFT_DIR")


class ConfigError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys instead of silently choosing one."""


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ConfigError(f"Configuration key is invalid or duplicated: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _read(path):
    try:
        value = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=UniqueLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot read configuration {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigError(f"Configuration must be a mapping: {path}")
    return value


def discover():
    explicit = os.environ.get("KB_CONFIG")
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise ConfigError(f"KB_CONFIG does not point to a file: {path}")
        return path
    for parent in SKILL_DIR.parents:
        if parent.name == ".kbkit":
            candidate = parent.parent / "kb.config.yaml"
            if candidate.is_file():
                return candidate
            raise ConfigError(f"Installed workspace configuration is missing: {candidate}")
    for parent in (Path.cwd(), *Path.cwd().parents):
        candidate = parent / "kb.config.yaml"
        if candidate.is_file():
            return candidate
    raise ConfigError("No kb.config.yaml found. Initialize a workspace, cd into it, or set KB_CONFIG.")


def load(config_path=None):
    config_path = Path(config_path).expanduser().resolve() if config_path else discover()
    cfg = _read(DEFAULTS_PATH)
    overrides = _read(config_path)
    unknown = set(overrides) - set(cfg)
    if unknown:
        raise ConfigError("Unknown configuration keys: " + ", ".join(sorted(unknown)))
    cfg.update(overrides)
    for key, value in cfg.items():
        if isinstance(value, (dict, list)):
            raise ConfigError(f"{key} must be a scalar; use a comma-separated format list")
    if not isinstance(cfg["KB_ROOT"], str) or not cfg["KB_ROOT"].strip():
        raise ConfigError("KB_ROOT must be a nonempty path")
    root = Path(cfg["KB_ROOT"]).expanduser()
    root = (config_path.parent / root).resolve() if not root.is_absolute() else root.resolve()
    cfg["KB_ROOT"] = str(root)
    for key in PATH_KEYS:
        raw = cfg[key]
        if not isinstance(raw, str) or not raw.strip() or Path(raw).is_absolute():
            raise ConfigError(f"{key} must be a nonempty KB-relative path")
        resolved = (root / raw).resolve()
        if not resolved.is_relative_to(root) or resolved == root:
            raise ConfigError(f"{key} must stay inside KB_ROOT and cannot be its root")
        cfg[key + "_ABS"] = str(resolved)
    if cfg["OUTPUT_LANGUAGE"] not in ("en", "zh-CN"):
        raise ConfigError("OUTPUT_LANGUAGE must be en or zh-CN")
    if cfg["RMD_WHEN_NO_RENDER"] != "ask":
        raise ConfigError("Rmd execution cannot be enabled in configuration")
    for key in ("WORKER_TIMEOUT", "SHARD_THRESHOLD", "LARGE_FILE_WARN_MB", "MAX_CATEGORY_DEPTH", "RELATED_PREFILTER_MIN", "MAX_IMAGE_MB"):
        if type(cfg[key]) is not int or cfg[key] <= 0:
            raise ConfigError(f"{key} must be a positive integer")
    if type(cfg["RENDER_ALL_PAGES"]) is not bool:
        raise ConfigError("RENDER_ALL_PAGES must be a boolean")
    for key in ("CLAUDE_CLI", "CODEX_CLI", "PYTHON"):
        if not isinstance(cfg[key], str) or not cfg[key]:
            raise ConfigError(f"{key} must be auto or an executable path")
    for key in ("WORKER_MODEL", "CODEX_WORKER_MODEL", "CODEX_WORKER_REASONING_EFFORT"):
        if cfg[key] is not None and (not isinstance(cfg[key], str) or not cfg[key].strip()):
            raise ConfigError(f"{key} must be null or a nonempty string")
    if cfg["CODEX_WORKER_REASONING_EFFORT"] not in (None, "minimal", "low", "medium", "high", "xhigh"):
        raise ConfigError("Unsupported CODEX_WORKER_REASONING_EFFORT")
    supported_exts(cfg)
    cfg["PYTHON"] = sys.executable if cfg["PYTHON"] == "auto" else (shutil.which(os.path.expanduser(cfg["PYTHON"])) or cfg["PYTHON"])
    cfg["CONFIG_PATH"] = str(config_path)
    cfg["SKILL_ROOT_ABS"] = str(SKILL_DIR)
    cfg["SKILL_ROOT"] = os.path.relpath(SKILL_DIR, root)
    cfg["READER_SKILL"] = str(SKILL_DIR.parent / "kb")
    return cfg


def supported_exts(cfg=None):
    cfg = load() if cfg is None else cfg
    raw = cfg.get("SUPPORTED_FORMATS")
    if not isinstance(raw, str):
        raise ConfigError("SUPPORTED_FORMATS must be a comma-separated string")
    values = tuple(dict.fromkeys(x.strip().lower() for x in raw.split(",")))
    if not values or any(not x.startswith(".") or not x[1:].isalnum() for x in values):
        raise ConfigError("SUPPORTED_FORMATS contains an invalid extension")
    return values


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config")
    args = parser.parse_args()
    try:
        print(json.dumps(load(args.config), indent=2, ensure_ascii=False))
    except ConfigError as exc:
        parser.exit(2, f"Configuration error: {exc}\n")
