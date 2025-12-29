"""Core routines that drive Blender to create procedural renders."""

from __future__ import annotations

from collections.abc import Iterator
import logging
from pathlib import Path

import bpy
from pathvalidate import sanitize_filename

from .config import (
    CameraInstruction,
    CollectionVisibilityOverride,
    NodeInputOverride,
    ObjectTranslation,
    ObjectVisibilityOverride,
    PrimitiveSpec,
    RenderPlan,
    RenderSettings,
    VariationConfig,
)

LOGGER = logging.getLogger(__name__)


def execute_render_plan(plan: RenderPlan, *, dry_run: bool = False) -> None:
    """Apply each variation in the plan and render a still image."""

    _configure_logging()

    if not plan.variations:
        LOGGER.warning("No variations defined; nothing to render.")
        return

    plan.output_dir.mkdir(parents=True, exist_ok=True)

    for variation in plan.variations:
        LOGGER.info("=== Variation: %s ===", variation.name)
        _reload_scene(plan.blend_path, dry_run)
        _apply_node_overrides(variation.node_overrides, dry_run)
        _apply_collection_visibility(variation.collection_visibility, dry_run)
        _apply_visibility_overrides(variation.visibility, dry_run)
        _translate_objects(variation.translations, dry_run)
        _add_primitives(variation.additions, dry_run)

        if variation.camera:
            _configure_camera(plan.camera_object, variation.camera, dry_run)

        render_settings = variation.render_settings or plan.base_render_settings
        render_path = _build_render_path(plan.output_dir, variation.name, render_settings)

        _configure_render_settings(render_settings, render_path, dry_run)
        _perform_render(dry_run)


def _configure_logging() -> None:
    if LOGGER.handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s - %(message)s",
    )


def _reload_scene(blend_path: Path, dry_run: bool) -> None:
    if dry_run:
        LOGGER.info("[dry-run] Would reload %s", blend_path)
        return
    LOGGER.info("Loading blend file %s", blend_path)
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))


def _apply_node_overrides(overrides: list[NodeInputOverride], dry_run: bool) -> None:
    for override in overrides:
        if dry_run:
            LOGGER.info(
                "[dry-run] Override %s/%s.%s -> %s",
                override.material,
                override.node,
                override.socket,
                override.value,
            )
            continue

        material = bpy.data.materials.get(override.material)
        if material is None:
            LOGGER.warning("Material %s not found", override.material)
            continue

        if not material.use_nodes or not material.node_tree:
            LOGGER.warning("Material %s does not use nodes", override.material)
            continue

        node = material.node_tree.nodes.get(override.node)
        if node is None:
            LOGGER.warning("Node %s missing in material %s", override.node, override.material)
            continue

        socket = node.inputs.get(override.socket) or node.outputs.get(override.socket)
        if socket is None:
            LOGGER.warning(
                "Socket %s missing on node %s in material %s",
                override.socket,
                override.node,
                override.material,
            )
            continue

        if not hasattr(socket, "default_value"):
            LOGGER.warning("Socket %s has no default_value attribute", override.socket)
            continue

        value = override.value
        try:
            default_value = socket.default_value
            if isinstance(default_value, (tuple, list)):
                socket.default_value = (
                    tuple(float(v) for v in value)
                    if isinstance(value, (tuple, list))
                    else tuple(float(value) for _ in default_value)
                )
            else:
                socket.default_value = float(value)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error("Failed to override node value: %s", exc, exc_info=True)


def _apply_collection_visibility(
    overrides: list[CollectionVisibilityOverride],
    dry_run: bool,
) -> None:
    for override in overrides:
        target_state = "visible" if override.visible else "hidden"
        if dry_run:
            LOGGER.info(
                "[dry-run] Would set collection %s visibility -> %s",
                override.name,
                target_state,
            )
            continue

        hide = not override.visible
        collection = bpy.data.collections.get(override.name)
        if collection is None:
            LOGGER.warning("Collection %s not found for visibility override", override.name)
        else:
            collection.hide_viewport = hide
            collection.hide_render = hide

        for view_layer in bpy.context.scene.view_layers:
            for layer_collection in _iter_layer_collections(view_layer.layer_collection):
                if layer_collection.collection.name != override.name:
                    continue
                layer_collection.hide_viewport = hide
                layer_collection.exclude = hide
                layer_collection.collection.hide_viewport = hide
                layer_collection.collection.hide_render = hide


def _iter_layer_collections(root: bpy.types.LayerCollection) -> Iterator[bpy.types.LayerCollection]:
    stack = [root]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(current.children)


def _apply_visibility_overrides(
    overrides: list[ObjectVisibilityOverride],
    dry_run: bool,
) -> None:
    for override in overrides:
        target_state = "visible" if override.visible else "hidden"
        if dry_run:
            LOGGER.info("[dry-run] Would set %s visibility -> %s", override.name, target_state)
            continue

        obj = bpy.data.objects.get(override.name)
        if obj is None:
            LOGGER.warning("Object %s not found for visibility override", override.name)
            continue

        hide = not override.visible
        obj.hide_render = hide
        obj.hide_viewport = hide
        try:
            obj.hide_set(hide)
        except AttributeError:
            obj.hide_viewport = hide


def _translate_objects(translations: list[ObjectTranslation], dry_run: bool) -> None:
    for translation in translations:
        if dry_run:
            LOGGER.info("[dry-run] Would translate %s by %s", translation.name, translation.offset)
            continue

        obj = bpy.data.objects.get(translation.name)
        if obj is None:
            LOGGER.warning("Object %s not found", translation.name)
            continue

        for axis, delta in zip("xyz", translation.offset):
            setattr(obj.location, axis, getattr(obj.location, axis) + delta)


def _add_primitives(additions: list[PrimitiveSpec], dry_run: bool) -> None:
    for addition in additions:
        if dry_run:
            LOGGER.info(
                "[dry-run] Would add %s named %s at %s",
                addition.primitive,
                addition.name,
                addition.location,
            )
            continue

        operator_name = f"primitive_{addition.primitive.lower()}_add"
        operator = getattr(bpy.ops.mesh, operator_name, None)
        if operator is None:
            LOGGER.warning("Unsupported primitive type: %s", addition.primitive)
            continue

        operator(location=addition.location)  # type: ignore[operator]
        new_object = bpy.context.active_object
        if new_object is None:
            LOGGER.warning("Primitive %s did not create an active object", addition.primitive)
            continue

        if addition.name:
            new_object.name = addition.name
        new_object.rotation_euler = addition.rotation
        new_object.scale = addition.scale

        if addition.material:
            material = bpy.data.materials.get(addition.material)
            if material is None:
                LOGGER.warning("Material %s not found for new object", addition.material)
            else:
                if new_object.data.materials:
                    new_object.data.materials[0] = material
                else:
                    new_object.data.materials.append(material)


def _configure_camera(camera_name: str, instruction: CameraInstruction, dry_run: bool) -> None:
    if dry_run:
        LOGGER.info("[dry-run] Would update camera %s with %s", camera_name, instruction)
        return

    camera_obj = bpy.data.objects.get(camera_name)
    if camera_obj is None:
        LOGGER.warning("Camera object %s not found", camera_name)
        return

    if instruction.location:
        camera_obj.location = instruction.location
    if instruction.rotation_euler:
        camera_obj.rotation_euler = instruction.rotation_euler
    if instruction.lens_mm and camera_obj.type == "CAMERA" and camera_obj.data:
        camera_obj.data.lens = instruction.lens_mm


def _configure_render_settings(
    settings: RenderSettings,
    render_path: Path,
    dry_run: bool,
) -> None:
    if dry_run:
        LOGGER.info("[dry-run] Would render to %s with %s", render_path, settings)
        return

    scene = bpy.context.scene
    render = scene.render

    render.engine = settings.engine
    render.filepath = str(render_path)
    render.image_settings.file_format = settings.file_format
    render.image_settings.color_mode = settings.color_mode
    render.resolution_x = settings.resolution_x
    render.resolution_y = settings.resolution_y

    if settings.engine == "CYCLES" and hasattr(scene, "cycles"):
        scene.cycles.samples = settings.samples
        scene.cycles.use_denoising = settings.use_denoise
    elif settings.engine == "BLENDER_EEVEE" and hasattr(scene, "eevee"):
        scene.eevee.taa_samples = settings.samples


def _perform_render(dry_run: bool) -> None:
    if dry_run:
        LOGGER.info("[dry-run] Skipping Blender render call")
        return
    bpy.ops.render.render(write_still=True)


def _build_render_path(
    output_dir: Path,
    variation_name: str,
    settings: RenderSettings,
) -> Path:
    sanitized = sanitize_filename(variation_name, replacement_text="_")
    extension = settings.file_format.lower()
    suffix = ".png"
    if extension in {"png", "jpeg", "jpg", "tiff", "open_exr", "exr"}:
        suffix = ".exr" if extension in {"open_exr", "exr"} else f".{extension}"
    return output_dir / f"{sanitized}{suffix}"

