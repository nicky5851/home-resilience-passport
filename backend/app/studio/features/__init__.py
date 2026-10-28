"""One subpackage per feature: `s01_retrofit_sandbox`, `s02_street_proof`, ...

Each subpackage exposes `meta.py` (a `FeatureMeta`) and `router.py` (an `APIRouter`);
`app.studio.router` discovers and mounts them automatically.
"""
