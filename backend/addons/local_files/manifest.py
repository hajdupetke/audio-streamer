from app.addons.manifest import AddonManifest

manifest = AddonManifest(
    id="local-files",
    name="Local Files",
    description=(
        "Stream audiobooks from the server's local filesystem. "
        "Set LOCAL_FILES_LIBRARY_PATH in your .env to the directory containing your audiobooks. "
        "Expected layout: Author Name / Book Title / chapter.mp3"
    ),
    version="1.0.0",
    capabilities=["content_source", "stream_resolver"],
    settings_schema=[],  # library_path is a server-side env var, not a per-user setting
)
