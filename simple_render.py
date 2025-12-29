#!/usr/bin/env python3
"""Simple script to render from the Camera and save images.

Usage:
    blender --background cube_diorama.blend --python simple_render.py
"""

import bpy
from pathlib import Path

# Configuration
OUTPUT_DIR = Path(__file__).parent / "render_output" / "simple"
CAMERA_NAME = "Camera"
SAMPLES = 64
RESOLUTION_X = 1024
RESOLUTION_Y = 1024


def setup_render():
    """Configure render settings."""
    scene = bpy.context.scene
    render = scene.render
    
    # Basic render settings - use EEVEE for faster preview
    render.engine = 'BLENDER_EEVEE_NEXT'
    render.resolution_x = RESOLUTION_X
    render.resolution_y = RESOLUTION_Y
    render.image_settings.file_format = 'PNG'
    render.image_settings.color_mode = 'RGB'
    
    # EEVEE settings
    if hasattr(scene, 'eevee'):
        scene.eevee.taa_render_samples = SAMPLES
    
    # Set camera
    camera = bpy.data.objects.get(CAMERA_NAME)
    if camera and camera.type == 'CAMERA':
        scene.camera = camera
        print(f"Using camera: {CAMERA_NAME}")
    else:
        print(f"ERROR: Camera '{CAMERA_NAME}' not found!")
        return False
    
    return True


def enable_scene_content():
    """Make sure scene content is visible."""
    # Enable Demo Assets collection which contains most furniture
    demo_assets = bpy.data.collections.get("Demo Assets")
    if demo_assets:
        demo_assets.hide_viewport = False
        demo_assets.hide_render = False
        print("Enabled Demo Assets collection")
    
    # Enable it in view layer too
    for view_layer in bpy.context.scene.view_layers:
        for layer_collection in view_layer.layer_collection.children:
            if layer_collection.collection.name == "Demo Assets":
                layer_collection.exclude = False
                layer_collection.hide_viewport = False
                print("Enabled Demo Assets in view layer")
    
    # Disable compositor (it might have issues)
    bpy.context.scene.use_nodes = False
    print("Disabled compositor")
    
    # List what's visible
    visible_count = len([obj for obj in bpy.context.view_layer.objects])
    print(f"Visible objects in view layer: {visible_count}")


def render_image(name: str):
    """Render and save a single image."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{name}.png"
    
    bpy.context.scene.render.filepath = str(output_path)
    
    print(f"Rendering {name}...")
    bpy.ops.render.render(write_still=True)
    print(f"Saved: {output_path}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("Simple Blender Render Script")
    print("=" * 60)
    
    # Setup
    if not setup_render():
        return 1
    
    enable_scene_content()
    
    # Render base scene
    render_image("test_render")
    
    print("\nDone!")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

