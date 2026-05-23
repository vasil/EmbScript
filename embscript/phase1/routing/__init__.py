"""Routing method registry.

Drop a new module in this package, implement `RoutingMethod`, and add an entry here.
The CLI exposes any registered method automatically.
"""

from __future__ import annotations

from embscript.phase1.routing.attractor import StrangeAttractor
from embscript.phase1.routing.base import RoutingMethod
from embscript.phase1.routing.brick import BrickFill
from embscript.phase1.routing.brownian import BrownianWalk
from embscript.phase1.routing.gradient import GradientFlow
from embscript.phase1.routing.hilbert import HilbertCurve
from embscript.phase1.routing.levy import LevyFlight
from embscript.phase1.routing.perlin import PerlinFlow

METHODS: dict[str, type[RoutingMethod]] = {
    "brownian": BrownianWalk,
    "brick": BrickFill,
    "perlin": PerlinFlow,
    "levy": LevyFlight,
    "gradient": GradientFlow,
    "attractor": StrangeAttractor,
    "hilbert": HilbertCurve,
}
