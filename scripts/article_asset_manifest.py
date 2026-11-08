#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from article_repo_layout import MANIFEST_FILENAME, build_layout


def load_manifest(article_root: Path) -> dict[str, Any]:
    path = build_layout(article_root).manifest_path
    return json.loads(path.read_text())


def manifest_path(article_root: Path) -> Path:
    return build_layout(article_root).manifest_path
