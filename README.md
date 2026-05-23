# EmbScript

**EmbScript** is a Linux command-line pipeline that turns a raster image into a file an embroidery machine can stitch. It is an embroidery-specific take on the PostScript page-description model: the image is decomposed into colored layers, each layer is routed as a single continuous self-avoiding path, and the result is written first as an intermediate SVG and then as a `.DST` (or `.JEF` / `.PES` / `.EXP` / `.VP3`) machine file.

## Why

Most desktop embroidery software hides the digitization process behind a GUI. EmbScript exposes the whole pipeline as plain CLI tools so the output is reproducible, scriptable, and inspectable — every intermediate stage is a file you can read.

## The two stages

1. **`embscript-raster`** — image → color-layered SVG.
   Quantizes the image into N color masks, builds a per-mask density field, then routes one continuous polyline per color whose length is constrained to a target stitch count.
2. **`embscript-stitch`** — SVG → embroidery machine file.
   Parses the layered SVG and replays each polyline through `pyembroidery` to emit `.DST` (default) and other brand formats.

## Install

```
pip install -e .[dev]
```

## Usage

```
embscript-raster --image input.png --stitches 5000 --colors 3 \
                 --method brownian --overlap-tolerance 0.5 \
                 --output design.svg

embscript-stitch --svg design.svg --format dst --output design.dst
```

## Routing methods

The path through each color layer can be drawn by any of these methods (`--method <name>`):

| Method | Character | Good for |
|---|---|---|
| `brownian` | Density-weighted random walk, self-avoiding | General-purpose shading; organic textures |
| `brick` | Serpentine rows with brick offset | Dense, even fills (logos, flat color) |
| `perlin` | Walk follows a Perlin noise field | Soft directional flow; clouds, hair, fur |
| `levy` | Lévy flight — heavy-tailed step lengths | Wide, disconnected subjects (full coverage on legs/limbs) |
| `gradient` | Walks along image-edge contours (perpendicular to gradient) | Portraits, anything where the form should be sculpted by edges |
| `attractor` | De Jong strange-attractor flow field | Decorative, swirly, art-poster effects |
| `hilbert` | Hilbert space-filling curve | Maximum even coverage; deterministic; no randomness |

All chaotic methods share a `field_walk` helper that gives them density-weighted seeding, spatial-hash self-avoidance, and a saturation-aware stopping rule.

## Color separation modes

`--separation <mode>`:

- **`kmeans`** (default) — KMeans clustering in Lab color space; picks N representative colors from the image.
- **`cmyk`** — fixed four-layer Cyan / Magenta / Yellow / Black separation.
- **`palette`** — quantize to a fixed natural-color palette so output reuses real thread colors.

## Stitch length and coverage controls

- `--max-stitch-mm` (default **3.0**) — caps the distance between consecutive stitches; longer hops are subdivided.
- `--thread-width-mm` (default **0.4**) — informs auto-coverage math.
- `--opacity` — if given, the target stitch count is computed from `effective_area_mm² × opacity / (max_stitch_mm × thread_width_mm)`, so coverage scales naturally with thread weight.
- `--travel-close-px` — bridges small gaps in the union mask used for inter-region travel (kills "flying lines" across blank fabric).
- `--min-density` — discard pixels below this brightness threshold (raises contrast).
- `--width` / `--height` — final embroidery dimensions in millimetres.

## Live animation

`examples/animate.html` is a standalone JS page that loads any output SVG and animates each polyline being drawn from first stitch to last. Useful for previewing the path order — open it in a browser and pick an SVG.

## Project layout

```
embscript/
├── cli/                 # entry points
├── phase1/
│   ├── color_separation.py
│   ├── density_map.py
│   ├── stitch_budget.py
│   ├── svg_writer.py
│   └── routing/         # one file per routing method
└── phase2/
    ├── svg_parser.py
    └── stitch_writer.py
examples/
├── animate.html         # browser-based draw-order animation
└── output/              # generated SVGs (gitignored)
tests/
```

## Status

Active. Tagged releases:

- **v0.5.0** — Perlin, Lévy, gradient, attractor, Hilbert routing methods; JS animation page.
- **v0.4.0** — Brick fill driven by thread width and opacity.
- **v0.3.0** — Palette separation mode.
- **v0.2.0** — Chaotic goal-walk travel + opacity-driven auto stitch count.

See `CLAUDE.md` for the architectural contract and conventions.
