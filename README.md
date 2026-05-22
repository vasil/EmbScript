# EmbScript

A two-stage Linux CLI Python pipeline that turns a raster image into an embroidery machine file.

1. **Phase 1** — `embscript-raster`: image → color-layered SVG, with one continuous path per color routed by either a stochastic Brownian walk or a brick-fill method. Path length is constrained to a target stitch count.
2. **Phase 2** — `embscript-stitch`: SVG → Tajima `.DST` (or other brand formats) via `pyembroidery`.

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

See `CLAUDE.md` for architecture details.
# EmbScript
