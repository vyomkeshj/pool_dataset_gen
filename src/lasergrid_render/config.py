"""Typed configuration helpers for render automation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

try:  # pragma: no cover - optional dependency under Blender
    import yaml
except ModuleNotFoundError:  # pragma: no cover - Blender runtime may skip PyYAML
    yaml = None  # type: ignore[assignment]


class PlanValidationError(ValueError):
    """Raised when a render plan file cannot be parsed."""


@dataclass(slots=True)
class NodeInputOverride:
    """Represents a single material node socket override."""

    material: str
    node: str
    socket: str
    value: Any


@dataclass(slots=True)
class ObjectTranslation:
    """Translates an existing object by an offset."""

    name: str
    offset: tuple[float, float, float]


@dataclass(slots=True)
class PrimitiveSpec:
    """Adds a primitive mesh to the scene."""

    primitive: str
    name: str | None
    location: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    material: str | None = None


@dataclass(slots=True)
class ObjectVisibilityOverride:
    """Toggles viewport/render visibility for a named object."""

    name: str
    visible: bool = True


@dataclass(slots=True)
class CollectionVisibilityOverride:
    """Toggles render visibility for a collection."""

    name: str
    visible: bool = True


@dataclass(slots=True)
class CameraInstruction:
    """Explicit camera transform overrides."""

    location: tuple[float, float, float] | None = None
    rotation_euler: tuple[float, float, float] | None = None
    lens_mm: float | None = None


@dataclass(slots=True)
class RenderSettings:
    """Subset of render settings that can be overridden."""

    engine: str = "CYCLES"
    samples: int = 128
    resolution_x: int = 1024
    resolution_y: int = 1024
    use_denoise: bool = True
    file_format: str = "PNG"
    color_mode: str = "RGB"


DEFAULT_RENDER_SETTINGS = RenderSettings()


@dataclass(slots=True)
class VariationConfig:
    """A single render variation that mutates the scene before rendering."""

    name: str
    node_overrides: list[NodeInputOverride] = field(default_factory=list)
    translations: list[ObjectTranslation] = field(default_factory=list)
    additions: list[PrimitiveSpec] = field(default_factory=list)
    collection_visibility: list[CollectionVisibilityOverride] = field(default_factory=list)
    visibility: list[ObjectVisibilityOverride] = field(default_factory=list)
    camera: CameraInstruction | None = None
    render_settings: RenderSettings | None = None


@dataclass(slots=True)
class RenderPlan:
    """Top-level execution config."""

    blend_path: Path
    output_dir: Path
    base_render_settings: RenderSettings
    camera_object: str = "Camera"
    variations: list[VariationConfig] = field(default_factory=list)


def load_plan_from_file(
    plan_path: str | Path,
    *,
    blend_override: str | Path | None = None,
    output_override: str | Path | None = None,
) -> RenderPlan:
    """Load a YAML plan into strongly typed dataclasses."""

    path = Path(plan_path).expanduser().resolve()
    if not path.exists():
        raise PlanValidationError(f"Plan file does not exist: {path}")

    if yaml is None:
        raise PlanValidationError(
            "PyYAML is required to load render plans. Install PyYAML in the current "
            "Python environment or run inside the configured virtualenv."
        )

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise PlanValidationError("Top-level plan must be a mapping")

    blend_path = Path(blend_override or raw.get("blend_path", "")).expanduser()
    if not blend_path.is_absolute():
        blend_path = (path.parent / blend_path).resolve()

    if not blend_path.exists():
        raise PlanValidationError(f"Blend file cannot be found: {blend_path}")

    output_dir = Path(output_override or raw.get("output_dir", "render_output")).expanduser()
    if not output_dir.is_absolute():
        output_dir = (path.parent / output_dir).resolve()

    base_render_settings = _build_render_settings(raw.get("render_settings", {}))
    camera_object = raw.get("camera_object", "Camera")
    variations = [
        _build_variation(entry, idx)
        for idx, entry in enumerate(raw.get("variations", []))
    ]

    return RenderPlan(
        blend_path=blend_path,
        output_dir=output_dir,
        base_render_settings=base_render_settings,
        camera_object=camera_object,
        variations=variations,
    )


def _build_render_settings(payload: dict[str, Any]) -> RenderSettings:
    if not isinstance(payload, dict):
        raise PlanValidationError("render_settings must be a mapping")

    defaults = DEFAULT_RENDER_SETTINGS
    return RenderSettings(
        engine=payload.get("engine", defaults.engine),
        samples=int(payload.get("samples", defaults.samples)),
        resolution_x=int(payload.get("resolution_x", defaults.resolution_x)),
        resolution_y=int(payload.get("resolution_y", defaults.resolution_y)),
        use_denoise=bool(payload.get("use_denoise", defaults.use_denoise)),
        file_format=payload.get("file_format", defaults.file_format),
        color_mode=payload.get("color_mode", defaults.color_mode),
    )


def _build_variation(payload: dict[str, Any], idx: int) -> VariationConfig:
    if not isinstance(payload, dict):
        raise PlanValidationError(f"variation #{idx} must be a mapping")

    name = payload.get("name") or f"variation_{idx:03d}"

    node_overrides = [
        NodeInputOverride(
            material=entry["material"],
            node=entry["node"],
            socket=entry["socket"],
            value=entry["value"],
        )
        for entry in _as_list(payload.get("node_overrides", []))
    ]

    translations = [
        ObjectTranslation(
            name=entry["name"],
            offset=_as_tuple(entry.get("offset", (0, 0, 0))),
        )
        for entry in _as_list(payload.get("translations", []))
    ]

    additions = [
        PrimitiveSpec(
            primitive=entry.get("primitive", "cube"),
            name=entry.get("name"),
            location=_as_tuple(entry.get("location", (0, 0, 0))),
            rotation=_as_tuple(entry.get("rotation", (0, 0, 0))),
            scale=_as_tuple(entry.get("scale", (1, 1, 1))),
            material=entry.get("material"),
        )
        for entry in _as_list(payload.get("additions", []))
    ]

    collection_visibility = [
        CollectionVisibilityOverride(
            name=entry["name"],
            visible=bool(entry.get("visible", True)),
        )
        for entry in _as_list(payload.get("collection_visibility", []))
    ]

    visibility = [
        ObjectVisibilityOverride(
            name=entry["name"],
            visible=bool(entry.get("visible", True)),
        )
        for entry in _as_list(payload.get("visibility", []))
    ]

    camera = None
    if payload.get("camera"):
        camera_payload = payload["camera"]
        if not isinstance(camera_payload, dict):
            raise PlanValidationError(f"camera override in {name} must be a mapping")
        camera = CameraInstruction(
            location=_as_tuple(camera_payload.get("location"))
            if camera_payload.get("location") is not None
            else None,
            rotation_euler=_as_tuple(camera_payload.get("rotation_euler"))
            if camera_payload.get("rotation_euler") is not None
            else None,
            lens_mm=float(camera_payload["lens_mm"])
            if camera_payload.get("lens_mm") is not None
            else None,
        )

    render_settings = (
        _build_render_settings(payload["render_settings"])
        if payload.get("render_settings")
        else None
    )

    return VariationConfig(
        name=name,
        node_overrides=node_overrides,
        translations=translations,
        additions=additions,
        collection_visibility=collection_visibility,
        visibility=visibility,
        camera=camera,
        render_settings=render_settings,
    )


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, Iterable):
        return list(value)
    raise PlanValidationError("Expected list-compatible value")


def _as_tuple(value: Sequence[float] | None, size: int = 3) -> tuple[float, float, float]:
    if value is None:
        raise PlanValidationError("Expected tuple, got None")
    if len(value) != size:
        raise PlanValidationError(f"Expected {size} values, received {len(value)}")
    return tuple(float(v) for v in value)

