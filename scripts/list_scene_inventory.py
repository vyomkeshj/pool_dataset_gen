"""Emit a JSON inventory of all objects inside a Blender scene.

Usage from the repo root (assuming Blender is installed on PATH)::

    blender -b cube_diorama.blend -P scripts/list_scene_inventory.py -- --output scene.json

This script must run under Blender's embedded Python because it depends on ``bpy``.
Outside Blender you can still import the helpers for typing/tests thanks to
fake-bpy-module.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Iterable

import bpy


def _format_vector(values: Iterable[float]) -> list[float]:
    return [round(float(component), 5) for component in values]


def _ensure_blend_loaded(blend_path: Path | None) -> None:
    if blend_path is None:
        return

    blend_path = blend_path.expanduser().resolve()
    current_path = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None

    if current_path != blend_path:
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))


def _collect_inventory(include_hidden: bool) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []

    for obj in bpy.data.objects:
        if not include_hidden and obj.hide_get():
            continue

        inventory.append(
            {
                "name": obj.name,
                "type": obj.type,
                "location": _format_vector(obj.location),
                "rotation": _format_vector(obj.rotation_euler),
                "scale": _format_vector(obj.scale),
            }
        )

    return inventory


def _extract_argv(argv: list[str] | None) -> list[str]:
    if argv is not None:
        return argv

    raw_args = sys.argv[1:]
    if "--" in raw_args:
        dash_index = raw_args.index("--")
        return raw_args[dash_index + 1 :]

    return raw_args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dump Blender scene inventory as JSON.")
    parser.add_argument(
        "--blend",
        type=Path,
        default=None,
        help="Optional path to a .blend file to open before dumping inventory.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include objects that are hidden in the viewport.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional file path to receive the JSON output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(_extract_argv(argv))

    _ensure_blend_loaded(args.blend)
    inventory = _collect_inventory(include_hidden=args.include_hidden)

    payload = json.dumps({"objects": inventory}, indent=2)

    if args.output:
        args.output.expanduser().resolve().write_text(payload, encoding="utf-8")
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

