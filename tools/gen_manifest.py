"""Generate the offline manifest from the importable Python package.

Usage::

    python tools/gen_manifest.py
    python tools/gen_manifest.py --out custom/path.json
    python tools/gen_manifest.py --print

The script imports ``houdini_bridge`` from ``plugin/python/`` *without*
Houdini, so it can run on any vanilla Python 3.9+ install.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = REPO_ROOT / "plugin" / "python"
DEFAULT_OUT = REPO_ROOT / "agent" / "skills" / "houdini-bridge" / "manifest" / "houdini_bridge_manifest.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Where to write the manifest JSON")
    parser.add_argument("--print", action="store_true", help="Print the manifest to stdout instead of writing")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(PACKAGE_ROOT))
    import houdini_bridge  # noqa: WPS433 — intentional late import

    registry = houdini_bridge.get_registry()
    manifest = registry.to_manifest()
    blob = json.dumps(manifest, ensure_ascii=False, indent=2)

    if args.print:
        sys.stdout.write(blob + "\n")
        return 0

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(blob, encoding="utf-8")

    libs = manifest.get("libraries", {})
    total = sum(len(funcs) for funcs in libs.values())
    print(f"manifest written to {out_path}")
    print(f"  libraries: {len(libs)}  functions: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
