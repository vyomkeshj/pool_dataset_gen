"""Command line interface for the render automation helpers."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import PlanValidationError, load_plan_from_file
from .render_pipeline import execute_render_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lasergrid_render.cli",
        description="Batch renderer for cube diorama variations",
    )
    parser.add_argument(
        "--plan",
        default="src/lasergrid_render/configs/cube_diorama.yaml",
        help="Path to the YAML plan file.",
    )
    parser.add_argument(
        "--blend",
        default=None,
        help="Optional override for the .blend file path.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional override for the render output directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log planned changes without touching Blender.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        plan = load_plan_from_file(
            args.plan,
            blend_override=args.blend,
            output_override=args.output,
        )
    except PlanValidationError as exc:
        logging.error("Failed to load plan: %s", exc)
        return 2

    execute_render_plan(plan, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())

