from app.addons.manifest import AddonManifest

manifest = AddonManifest(
    id="librivox",
    name="LibriVox",
    description=(
        "Free public-domain audiobooks recorded by volunteers at LibriVox.org. "
        "No account or configuration required."
    ),
    version="1.0.0",
    capabilities=["content_source", "stream_resolver"],
    settings_schema=[],  # Public API — no credentials needed
    author="LibriVox",
)
