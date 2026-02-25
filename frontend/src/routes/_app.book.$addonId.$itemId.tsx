import { createFileRoute } from "@tanstack/react-router"
import { useBook } from "@/hooks/useBook"
import { useLibrary, useSaveBook, useRemoveBook } from "@/hooks/useLibrary"
import { usePlayerStore } from "@/stores/playerStore"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { toast } from "sonner"
import type { ChapterFile } from "@/types"

export const Route = createFileRoute("/_app/book/$addonId/$itemId")({
  component: BookDetailPage,
})

function formatDuration(seconds: number): string {
  const s = Math.floor(seconds)
  const m = Math.floor(s / 60)
  const h = Math.floor(m / 60)
  if (h > 0) {
    return `${h}h ${m % 60}m`
  }
  return `${m}m ${s % 60}s`
}

function BookDetailPage() {
  const { addonId, itemId } = Route.useParams()
  const loadBook = usePlayerStore((s) => s.loadBook)

  const { data: book, isLoading: bookLoading } = useBook(addonId, itemId)
  const { data: library, isLoading: libraryLoading } = useLibrary()
  const saveBook = useSaveBook()
  const removeBook = useRemoveBook()

  const libraryItem = library?.find(
    (item) => item.addon_id === addonId && item.external_id === itemId
  ) ?? null

  const isSaved = libraryItem !== null

  async function handleSave() {
    if (!book) return
    try {
      await saveBook.mutateAsync({
        addon_id: addonId,
        external_id: itemId,
        title: book.title,
        author: book.author,
        cover_url: book.cover_url,
        metadata: book.extra ?? {},
      })
      toast.success("Added to library")
    } catch {
      toast.error("Failed to add to library")
    }
  }

  async function handleRemove() {
    if (!libraryItem) return
    try {
      await removeBook.mutateAsync(libraryItem.id)
      toast.success("Removed from library")
    } catch {
      toast.error("Failed to remove from library")
    }
  }

  async function handlePlayTrack(index: number) {
    if (!book) return

    let libItemId: string | null = libraryItem?.id ?? null

    // If not in library, auto-save first
    if (!libItemId) {
      try {
        const saved = await saveBook.mutateAsync({
          addon_id: addonId,
          external_id: itemId,
          title: book.title,
          author: book.author,
          cover_url: book.cover_url,
          metadata: book.extra ?? {},
        })
        libItemId = saved.id
      } catch {
        // Continue without library item id
      }
    }

    loadBook(addonId, itemId, book.title, book.files as ChapterFile[], libItemId, book.cover_url ?? null, index)
  }

  if (bookLoading || libraryLoading) {
    return (
      <div className="container mx-auto px-6 py-8 max-w-6xl">
        <div className="flex gap-8">
          <Skeleton className="w-64 h-64 flex-shrink-0 rounded-lg" />
          <div className="flex-1 space-y-3">
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-5 w-1/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-4/6" />
          </div>
        </div>
      </div>
    )
  }

  if (!book) {
    return (
      <div className="container mx-auto px-6 py-8">
        <div className="text-center py-16 text-muted-foreground">
          Book not found
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-6xl animate-in fade-in duration-300">
      <div className="flex gap-8 mb-8">
        {/* Left: Cover + metadata */}
        <div className="flex-shrink-0 w-56 space-y-4">
          {book.cover_url ? (
            <img
              src={book.cover_url}
              alt={book.title}
              className="w-full rounded-lg object-cover shadow-2xl ring-1 ring-white/10"
            />
          ) : (
            <div className="w-full aspect-square rounded-lg bg-gradient-to-br from-secondary to-muted flex items-center justify-center shadow-2xl ring-1 ring-white/10">
              <svg
                className="w-16 h-16 text-muted-foreground"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                />
              </svg>
            </div>
          )}
          <Badge className="bg-primary/15 text-primary border border-primary/20 hover:bg-primary/20">{addonId}</Badge>
        </div>

        {/* Right: Info + actions */}
        <div className="flex-1 min-w-0 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold leading-tight">{book.title}</h1>
              <p className="text-muted-foreground mt-1">{book.author}</p>
            </div>
            <div className="flex-shrink-0">
              {isSaved ? (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleRemove}
                  disabled={removeBook.isPending}
                >
                  {removeBook.isPending ? "Removing..." : "Remove from Library"}
                </Button>
              ) : (
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSave}
                  disabled={saveBook.isPending}
                >
                  {saveBook.isPending ? "Adding..." : "Add to Library"}
                </Button>
              )}
            </div>
          </div>

          {book.description && (
            <p className="text-sm text-muted-foreground leading-relaxed line-clamp-5">
              {book.description}
            </p>
          )}

          <div className="text-sm text-muted-foreground">
            {book.files.length} chapter{book.files.length !== 1 ? "s" : ""}
          </div>
        </div>
      </div>

      <Separator className="mb-6" />

      {/* Chapter list */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Chapters</h2>
        <ScrollArea className="h-[calc(100vh-20rem)]">
          <div className="space-y-1">
            {book.files.map((file, index) => (
              <div
                key={file.id}
                className="flex items-center gap-4 px-3 py-2.5 rounded-md hover:bg-primary/10 group transition-colors"
              >
                <span className="text-xs text-muted-foreground w-6 text-right flex-shrink-0">
                  {file.track_number}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground truncate">{file.title}</p>
                </div>
                <span className="text-xs text-muted-foreground flex-shrink-0">
                  {formatDuration(file.duration)}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 hover:text-primary"
                  onClick={() => handlePlayTrack(index)}
                >
                  <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </Button>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}
