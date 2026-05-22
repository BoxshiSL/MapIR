"""Canvas / SketchLayer — v0.5 user-drawn rough geometry.

Sketch documents live separately from validated IR. The user iterates on the
sketch (district polygons, roads, POIs, scene slots); the generation pipeline
turns the sketch into a ``GeneratedLayout`` and the converter materialises a
WorldIR / SceneIR.
"""
