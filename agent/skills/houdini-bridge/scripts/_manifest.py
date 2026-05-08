"""Manifest loader used by the CLI for preflight + the ``libraries`` command."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class Manifest:
    raw: Dict[str, Any]

    @property
    def libraries(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        libs = self.raw.get("libraries", {})
        if not isinstance(libs, dict):
            return {}
        return libs

    def function(self, library: str, name: str) -> Optional[Dict[str, Any]]:
        return self.libraries.get(library, {}).get(name)

    def function_names(self, library: str) -> list:
        return sorted(self.libraries.get(library, {}).keys())

    def library_names(self) -> list:
        return sorted(self.libraries.keys())


def load_manifest(path: Path, *, optional: bool = False) -> Optional[Manifest]:
    if not Path(path).exists():
        if optional:
            return None
        raise FileNotFoundError(
            f"manifest not found at {path}. Run `python tools/gen_manifest.py` first."
        )
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return Manifest(raw=raw)
