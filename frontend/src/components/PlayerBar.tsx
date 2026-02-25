import { useRef, useEffect } from "react"
import { usePlayerStore } from "@/stores/playerStore"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"

function formatTime(seconds: number): string {
  const s = Math.floor(seconds)
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}:${rem.toString().padStart(2, "0")}`
}

export function PlayerBar() {
  const store = usePlayerStore()
  const audioRef = useRef<HTMLAudioElement>(null)
  const tokenRef = useRef<string | null>(null)

  const {
    addonId,
    itemId,
    itemTitle,
    coverUrl,
    files,
    currentIndex,
    isPlaying,
    position,
    duration,
    libraryItemId,
    setPlaying,
    setPosition,
    setDuration,
    nextTrack,
    prevTrack,
  } = store

  const currentFile = files[currentIndex] ?? null

  // Load new track when currentIndex or files change
  useEffect(() => {
    if (!currentFile || !addonId || !itemId) return

    async function loadTrack() {
      try {
        const { access_token } = await api.auth.token()
        tokenRef.current = access_token
        if (audioRef.current) {
          audioRef.current.src = api.stream.url(addonId!, itemId!, currentFile!.id, access_token)
          audioRef.current.load()
        }
      } catch {
        // Failed to load token / track
      }
    }

    loadTrack()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex, files])

  // Sync play/pause
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) {
      audio.play().catch(() => setPlaying(false))
    } else {
      audio.pause()
    }
  }, [isPlaying, setPlaying])

  // Progress auto-save every 5 seconds
  useEffect(() => {
    if (!libraryItemId || !currentFile) return

    const interval = setInterval(() => {
      if (isPlaying && libraryItemId && currentFile) {
        api.progress.upsert({
          library_item_id: libraryItemId,
          file_id: currentFile.id,
          position: audioRef.current?.currentTime ?? position,
          duration: audioRef.current?.duration ?? duration,
        }).catch(() => {})
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [isPlaying, libraryItemId, currentFile, position, duration])

  if (files.length === 0) return null

  function handleScrub(e: React.ChangeEvent<HTMLInputElement>) {
    const newPos = Number(e.target.value)
    setPosition(newPos)
    if (audioRef.current) {
      audioRef.current.currentTime = newPos
    }
  }

  function togglePlay() {
    setPlaying(!isPlaying)
  }

  const progressPercent = duration > 0 ? (position / duration) * 100 : 0

  return (
    <div className="fixed bottom-0 left-0 right-0 h-24 bg-card/80 backdrop-blur-md border-t border-border flex items-center px-6 gap-6 z-50 animate-in slide-in-from-bottom-2 duration-300">
      {/* Indigo progress bar at top edge */}
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-border">
        <div
          className="h-full bg-primary transition-all duration-100"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Left: cover art + book/chapter info */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={itemTitle ?? ""}
            className="h-10 w-10 rounded object-cover flex-shrink-0"
          />
        ) : (
          <div className="h-10 w-10 rounded bg-gradient-to-br from-secondary to-muted flex-shrink-0 flex items-center justify-center">
            <svg className="h-5 w-5 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
        )}
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground truncate">{itemTitle}</p>
          <p className="text-xs text-muted-foreground truncate">
            {currentFile?.title ?? ""}
          </p>
        </div>
      </div>

      {/* Center: controls + scrubber */}
      <div className="flex flex-col items-center gap-1.5 flex-shrink-0 w-80">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={prevTrack}
            disabled={currentIndex === 0}
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
              />
            </svg>
          </Button>

          <Button
            variant="default"
            size="icon"
            className="h-10 w-10 rounded-full"
            onClick={togglePlay}
          >
            {isPlaying ? (
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
              </svg>
            ) : (
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={nextTrack}
            disabled={currentIndex >= files.length - 1}
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 5l7 7-7 7M5 5l7 7-7 7"
              />
            </svg>
          </Button>
        </div>

        <div className="flex items-center gap-2 w-full">
          <span className="text-xs text-muted-foreground w-10 text-right tabular-nums">
            {formatTime(position)}
          </span>
          <input
            type="range"
            min={0}
            max={duration || 0}
            value={position}
            onChange={handleScrub}
            className="flex-1 h-1 accent-primary cursor-pointer"
          />
          <span className="text-xs text-muted-foreground w-10 tabular-nums">
            {formatTime(duration)}
          </span>
        </div>
      </div>

      {/* Right: empty space */}
      <div className="flex-1" />

      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        onTimeUpdate={() => setPosition(audioRef.current?.currentTime ?? 0)}
        onLoadedMetadata={() => setDuration(audioRef.current?.duration ?? 0)}
        onEnded={nextTrack}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
      />
    </div>
  )
}
