# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

EmbScript is a two-stage Linux command-line Python pipeline for embroidery digitization, conceptually framed as an embroidery-specific extension of the PostScript page-description model.

- **Phase 1** (`raster → SVG`): Quantize an image into N color layers, build a tonal density field per layer, route a single continuous self-avoiding path per layer whose length is constrained to a target stitch count. Output is a color-layered SVG treated as the intermediate "embscript page description".
- **Phase 2** (`SVG → machine file`): Parse the SVG, replay per-layer paths through `pyembroidery` as stitch sequences, write Tajima `.DST` (primary) plus other brand formats.

## Common commands

Editable install (run once in a fresh venv):

```
pip install -e .[dev]
```

Phase 1 — raster to SVG:

```
embscript-raster --image IN.png --stitches 5000 --colors 3 \
                 --method brownian --overlap-tolerance 0.5 \
                 --output design.svg
```

Phase 2 — SVG to stitch file:

```
embscript-stitch --svg design.svg --format dst --output design.dst
```

Tests:

```
pytest                            # full suite
pytest tests/test_brownian.py     # one file
pytest -k brick                   # by keyword
```

## Architecture

### Package layout

```
embscript/
├── cli/
│   ├── raster_to_svg.py    # Phase 1 entry point (console_scripts: embscript-raster)
│   └── svg_to_stitch.py    # Phase 2 entry point (console_scripts: embscript-stitch)
├── phase1/
│   ├── color_separation.py # k-means in Lab → N boolean masks
│   ├── density_map.py      # per-mask × inverse luminance → 0..1 field
│   ├── stitch_budget.py    # allocate budget across layers, iterate path params to hit target ±tolerance
│   ├── svg_writer.py       # write one <g id="layer-N" stroke="#RRGGBB"> per color
│   └── routing/
│       ├── base.py         # RoutingMethod protocol
│       ├── brownian.py     # stochastic self-avoiding walk, spatial-hash neighbour check
│       └── brick.py        # serpentine masonry fill with offset rows
└── phase2/
    ├── svg_parser.py       # read SVG layers → list[(color, polyline)]
    └── stitch_writer.py    # pyembroidery EmbPattern → write_dst/_jef/_pes/...
```

### Big-picture dataflow

```
raster image
    │
    ▼  color_separation (k-means)
N boolean masks ── density_map ──► N density fields (0..1)
    │                                     │
    │                                     ▼  stitch_budget allocates total --stitches across layers
    ▼
routing.<method>(mask, density, target_stitches, **opts) ──► polyline (list[(x,y)])
    │
    ▼  svg_writer
color-layered SVG (the "embscript page")
    │
    ▼  svg_parser
list[(color, polyline)]
    │
    ▼  stitch_writer (pyembroidery)
.DST / .JEF / .PES / ...
```

### Key contracts

- **Routing methods** all conform to the `RoutingMethod` protocol in `embscript/phase1/routing/base.py`. To add a new method (`tsp`, `hilbert`, etc.), drop a file in `routing/`, implement the protocol, and register it in `routing/__init__.py`'s method registry — the CLI exposes it automatically.
- **SVG as IR**: Phase 2 only consumes the SVG. It must remain a faithful description of the stitch path — no decorative SVG features (filters, gradients, clip paths). One `<g>` per color, polylines only, coordinates in millimetres.
- **Stitch budget tolerance**: `--stitches` is treated as a target. The pipeline iterates the routing method's step/pitch parameter until the realised count lands within ±5 % of the target. Document the achieved count in stderr.

### Routing method notes

- **brownian**: density-weighted random walk seeded inside the mask. Self-avoidance enforced by a spatial hash keyed on a min-distance derived from `--overlap-tolerance` (0 = strict self-avoid, 1 = unrestricted overlap). Step length modulated by local density to match brightness.
- **brick**: scan the mask in horizontal strips at a pitch derived from the density field; alternate rows are offset by half a brick to break the grid; rows are joined by short verticals to keep the path continuous. Within-row stitch pitch shortens in dark regions, lengthens in light ones.

## Conventions

- All geometry inside the package uses millimetres and a y-down coordinate system (matches SVG and most embroidery machines).
- Public functions take and return plain `numpy` arrays or `list[tuple[float, float]]` for polylines — no custom classes in the inter-module surface.
- New routing methods or output formats are added behind their respective registries; do not edit the CLI argparse choices manually.
