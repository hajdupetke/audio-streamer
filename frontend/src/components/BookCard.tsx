import type { AudiobookResult, LibraryItem } from "@/types"
import { Badge } from "@/components/ui/badge"

interface BookCardProps {
  book: AudiobookResult | LibraryItem
  onClick: () => void
}

export function BookCard({ book, onClick }: BookCardProps) {
  return (
    <div
      onClick={onClick}
      className="cursor-pointer group rounded-lg overflow-hidden bg-card border border-border hover:border-primary/50 transition-all hover:shadow-lg"
    >
      <div className="aspect-square bg-muted relative overflow-hidden">
        {book.cover_url ? (
          <img
            src={book.cover_url}
            alt={book.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-muted">
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
      </div>
      <div className="p-3 space-y-1">
        <p className="font-medium text-sm text-foreground line-clamp-2 leading-tight">
          {book.title}
        </p>
        <p className="text-xs text-muted-foreground line-clamp-1">{book.author}</p>
        <Badge variant="secondary" className="text-xs mt-1">
          {book.addon_id}
        </Badge>
      </div>
    </div>
  )
}
