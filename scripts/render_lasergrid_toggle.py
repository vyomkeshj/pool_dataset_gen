"""Blender entrypoint to render laser grid on/off variations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_import_paths() -> None:
    root = _project_root()
    src_path = root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    venv_lib = root / ".venv" / "lib"
    if venv_lib.exists():
        for site_packages in venv_lib.glob("python*/site-packages"):
            site_str = str(site_packages)
            if site_str not in sys.path:
                sys.path.insert(0, site_str)


def _extract_argv(explicit: list[str] | None = None) -> list[str]:
    if explicit is not None:
        return explicit
    raw = sys.argv[1:]
    if "--" in raw:
        idx = raw.index("--")
        return raw[idx + 1 :]
    return raw


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render the cube diorama with the laser grid toggled.",
    )
    parser.add_argument("--blend", type=Path, default=None, help="Path to cube_diorama.blend.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Folder for rendered PNG frames (defaults under render_output/lasergrid_toggle).",
    )
    parser.add_argument("--samples", type=int, default=32, help="Samples per pixel.")
    parser.add_argument("--resolution-x", type=int, default=1024, help="Horizontal resolution.")
    parser.add_argument("--resolution-y", type=int, default=1024, help="Vertical resolution.")
    parser.add_argument("--engine", default="CYCLES", help="Blender render engine.")
    parser.add_argument("--file-format", default="PNG", help="Image format (PNG, EXR, ...).")
    parser.add_argument("--color-mode", default="RGB", help="Render color mode.")
    parser.add_argument(
        "--light-name",
        default="Laser Grid.001",
        help="Name of the laser grid light object to toggle.",
    )
    parser.add_argument("--camera", default="Camera", help="Camera object name.")
    parser.add_argument("--no-denoise", action="store_true", help="Disable Cycles denoiser.")
    parser.add_argument("--dry-run", action="store_true", help="Skip Blender operations.")
    return parser


def main(argv: list[str] | None = None) -> int:
    _ensure_import_paths()
    from lasergrid_render.scenes import lasergrid_toggle

    parser = build_parser()
    args = parser.parse_args(_extract_argv(argv))

    lasergrid_toggle.run(
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


if __name__ == "__main__":
    raise SystemExit(main())

