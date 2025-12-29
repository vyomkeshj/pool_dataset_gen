# LaserGrid Procedural Renderer

This project automates rendering multiple variants of `cube_diorama.blend` by
editing node parameters, translating objects, spawning primitives, and shifting
the camera between each render.

## Environment Setup

```bash
cd /home/vk/Documents/LaserGrid
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

The dependency `fake-bpy-module` is included for type checking outside Blender.
Actual renders still need to run inside Blender so the real `bpy` module is
available.

## Project Layout

- `pyproject.toml` / `requirements.txt` – packaging metadata & dependencies
- `src/lasergrid_render/` – package source
  - `config.py` – data classes + YAML loader for render plans
  - `render_pipeline.py` – functions that mutate the scene and trigger renders
  - `cli.py` – command-line entrypoint (supports `--dry-run`)
  - `configs/cube_diorama.yaml` – sample plan (update names to your scene)
- `render_output/` – default folder for generated frames (created on demand)

## Running a Dry-Run (no Blender required)

```bash
source .venv/bin/activate
python -m lasergrid_render.cli --dry-run
```

Dry runs validate the YAML, resolve paths, and log the actions that would be
sent to Blender without touching any `.blend` files.

## Rendering Inside Blender

1. Ensure the `PYTHONPATH` includes the `src` directory so Blender can resolve
   the `lasergrid_render` package, or run one of the helper scripts under
   `scripts/` which adds it automatically.
2. Launch Blender in background mode and point it to the CLI script:

```bash
cd /home/vk/Documents/LaserGrid
PYTHONPATH=$PWD/src \
  /path/to/blender --background \
  --python src/lasergrid_render/cli.py -- \
  --plan src/lasergrid_render/configs/cube_diorama.yaml
```

Use `--blend` or `--output` to override the plan defaults. Customize
`configs/cube_diorama.yaml` to match your material, node, object, and camera
names. Each variation reloads the `.blend` file to ensure a clean baseline.

### Laser grid on/off renders

To capture a shot from the default `Camera` with the `Laser Grid.001` light
enabled and disabled, run:

```bash
cd /home/vk/Documents/LaserGrid
/snap/blender/current/blender --background \
  --python scripts/render_lasergrid_toggle.py -- \
  --samples 32 --resolution-x 1024 --resolution-y 1024
```

This writes two PNGs (`lasergrid_on.png`, `lasergrid_off.png`) into
`render_output/lasergrid_toggle`. Adjust `--blend`, `--output`, or `--light-name`
to match your scene, and pass `--dry-run` for a quick log-only verification.

## Next Steps

- Duplicate the sample YAML variation entries to cover every render you need.
- Expand `render_pipeline.py` with additional operations (e.g., modifier tweaks,
  collection visibility) as your workflow evolves.
- Integrate the CLI with Blender's `--python-expr` or asset manager scripts if
  you prefer running everything from inside a `.blend` file.
