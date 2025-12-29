"""Helpers to render cube_diorama with the laser grid effect on/off."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from ..config import (
    CollectionVisibilityOverride,
    ObjectVisibilityOverride,
    RenderPlan,
    RenderSettings,
    VariationConfig,
)
from ..render_pipeline import execute_render_plan

LASERGRID_LIGHT_NAME = "Laser Grid.001"


def _project_root() -> Path:
    # scenes/ -> lasergrid_render/ -> src/ -> repo root
    return Path(__file__).resolve().parents[3]


def _default_blend_path() -> Path:
    return _project_root() / "cube_diorama.blend"


def _default_output_dir() -> Path:
    return _project_root() / "render_output" / "lasergrid_toggle"


def build_variations(light_name: str = LASERGRID_LIGHT_NAME) -> list[VariationConfig]:
    """Create the on/off variations for the requested laser grid light."""

    return [
        VariationConfig(
            name="lasergrid_on",
            collection_visibility=[
                CollectionVisibilityOverride(name="Lighting", visible=True),
                CollectionVisibilityOverride(name="Demo Assets", visible=True),
            ],
            visibility=[
                ObjectVisibilityOverride(name=light_name, visible=True),
            ],
        ),
        VariationConfig(
            name="lasergrid_off",
            collection_visibility=[
                CollectionVisibilityOverride(name="Lighting", visible=True),
                CollectionVisibilityOverride(name="Demo Assets", visible=True),
            ],
            visibility=[
                ObjectVisibilityOverride(name=light_name, visible=False),
            ],
        ),
    ]


def build_plan(
    blend_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    *,
    engine: str = "CYCLES",
    samples: int = 64,
    resolution_x: int = 1024,
    resolution_y: int = 1024,
    use_denoise: bool = True,
    file_format: str = "PNG",
    color_mode: str = "RGB",
    light_name: str = LASERGRID_LIGHT_NAME,
    camera_object: str = "Camera",
) -> RenderPlan:
    """Build a RenderPlan that toggles the named laser grid light."""

    blend = Path(blend_path).expanduser().resolve() if blend_path else _default_blend_path()
    output = Path(output_dir).expanduser().resolve() if output_dir else _default_output_dir()

    base_settings = RenderSettings(
        engine=engine,
        samples=samples,
        resolution_x=resolution_x,
        resolution_y=resolution_y,
        use_denoise=use_denoise,
        file_format=file_format,
        color_mode=color_mode,
    )

    return RenderPlan(
        blend_path=blend,
        output_dir=output,
        base_render_settings=base_settings,
        camera_object=camera_object,
        variations=build_variations(light_name),
    )


def run(
    *,
    blend_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    engine: str = "CYCLES",
    samples: int = 64,
    resolution_x: int = 1024,
    resolution_y: int = 1024,
    use_denoise: bool = True,
    file_format: str = "PNG",
    color_mode: str = "RGB",
    light_name: str = LASERGRID_LIGHT_NAME,
    camera_object: str = "Camera",
    dry_run: bool = False,
) -> RenderPlan:
    """Create the plan and run it through the render pipeline."""

    plan = build_plan(
        blend_path=blend_path,
        output_dir=output_dir,
        engine=engine,
        samples=samples,
        resolution_x=resolution_x,
        resolution_y=resolution_y,
        use_denoise=use_denoise,
        file_format=file_format,
        color_mode=color_mode,
        light_name=light_name,
        camera_object=camera_object,
    )
    execute_render_plan(plan, dry_run=dry_run)
    return plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lasergrid_render.scenes.lasergrid_toggle",
        description="Render the cube diorama with the laser grid turned on and off.",
    )
    parser.add_argument("--blend", type=Path, default=None, help="Override the .blend path.")
    parser.add_argument("--output", type=Path, default=None, help="Override render output dir.")
    parser.add_argument("--samples", type=int, default=64, help="Samples per pixel.")
    parser.add_argument("--resolution-x", type=int, default=1024, help="Horizontal resolution.")
    parser.add_argument("--resolution-y", type=int, default=1024, help="Vertical resolution.")
    parser.add_argument("--engine", default="CYCLES", help="Blender render engine.")
    parser.add_argument("--file-format", default="PNG", help="Image format (PNG, EXR, ...).")
    parser.add_argument("--color-mode", default="RGB", help="Render color mode.")
    parser.add_argument("--no-denoise", action="store_true", help="Disable denoiser for Cycles.")
    parser.add_argument("--light-name", default=LASERGRID_LIGHT_NAME, help="Light object to toggle.")
    parser.add_argument("--camera", default="Camera", help="Camera object name.")
    parser.add_argument("--dry-run", action="store_true", help="Skip Blender side-effects.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    run(
        blend_path=args.blend,
        output_dir=args.output,
        engine=args.engine,
        samples=args.samples,
        resolution_x=args.resolution_x,
        resolution_y=args.resolution_y,
        use_denoise=not args.no_denoise,
        file_format=args.file_format,
        color_mode=args.color_mode,
        light_name=args.light_name,
        camera_object=args.camera,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry
    raise SystemExit(main())

