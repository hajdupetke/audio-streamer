"""
Scan backend/addons/*/ for addon packages and register them with the global registry.

Each addon directory must contain:
  manifest.py  — exposes a module-level `manifest: AddonManifest`
  addon.py     — exposes `ContentSourceImpl` and/or `StreamResolverImpl` classes

Directories starting with "_" are skipped (useful for __pycache__, _disabled/, etc.).
"""
import importlib
import logging
from pathlib import Path

from app.addons.manifest import AddonManifest
from app.addons.registry import registry

logger = logging.getLogger(__name__)

# backend/addons/ — two levels up from this file (app/addons/loader.py)
_DEFAULT_ADDONS_PATH = Path(__file__).parent.parent.parent / "addons"


def load_bundled_addons(addons_path: Path | None = None) -> None:
    path = addons_path or _DEFAULT_ADDONS_PATH

    if not path.exists():
        logger.warning("Addons directory not found: %s — no bundled addons loaded", path)
        return

    for addon_dir in sorted(path.iterdir()):
        if not addon_dir.is_dir() or addon_dir.name.startswith("_"):
            continue
        if not (addon_dir / "manifest.py").exists():
            logger.debug("Skipping %s — no manifest.py", addon_dir.name)
            continue

        package = f"addons.{addon_dir.name}"
        try:
            manifest_mod = importlib.import_module(f"{package}.manifest")
            addon_mod = importlib.import_module(f"{package}.addon")
        except ImportError as exc:
            logger.warning("Could not import addon %r: %s", addon_dir.name, exc)
            continue
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error loading addon %r: %s", addon_dir.name, exc)
            continue

        manifest: AddonManifest = manifest_mod.manifest
        content_source_cls = getattr(addon_mod, "ContentSourceImpl", None)
        stream_resolver_cls = getattr(addon_mod, "StreamResolverImpl", None)

        if content_source_cls is None and stream_resolver_cls is None:
            logger.warning(
                "Addon %r has no ContentSourceImpl or StreamResolverImpl — skipping",
                addon_dir.name,
            )
            continue

        registry.register(manifest, content_source_cls, stream_resolver_cls)
