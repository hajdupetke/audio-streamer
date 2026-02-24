"""
AddonRegistry — module-level singleton that holds bundled addon implementations.

The registry only knows about *bundled* addons (Python classes on the server).
Remote addons (future: user-linked manifest URLs) are dispatched by the addon
service at request time — the registry is not involved in that path.
"""
import logging
from typing import Any

from app.addons.base import ContentSource, StreamResolver
from app.addons.manifest import AddonManifest

logger = logging.getLogger(__name__)


class AddonRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, AddonManifest] = {}
        self._content_source_classes: dict[str, type[ContentSource]] = {}
        self._stream_resolver_classes: dict[str, type[StreamResolver]] = {}

    def register(
        self,
        manifest: AddonManifest,
        content_source: type[ContentSource] | None = None,
        stream_resolver: type[StreamResolver] | None = None,
    ) -> None:
        self._manifests[manifest.id] = manifest
        if content_source is not None:
            self._content_source_classes[manifest.id] = content_source
        if stream_resolver is not None:
            self._stream_resolver_classes[manifest.id] = stream_resolver
        logger.info(
            "Registered addon %r v%s caps=%s",
            manifest.id,
            manifest.version,
            manifest.capabilities,
        )

    def get_manifest(self, addon_id: str) -> AddonManifest | None:
        return self._manifests.get(addon_id)

    @property
    def all_manifests(self) -> dict[str, AddonManifest]:
        return dict(self._manifests)

    @property
    def bundled_addon_ids(self) -> list[str]:
        return list(self._manifests.keys())

    def make_content_source(self, addon_id: str, settings: dict[str, Any]) -> ContentSource | None:
        cls = self._content_source_classes.get(addon_id)
        return cls(settings) if cls is not None else None

    def make_stream_resolver(self, addon_id: str, settings: dict[str, Any]) -> StreamResolver | None:
        cls = self._stream_resolver_classes.get(addon_id)
        return cls(settings) if cls is not None else None


# Module-level singleton — import this everywhere you need the registry
registry = AddonRegistry()
