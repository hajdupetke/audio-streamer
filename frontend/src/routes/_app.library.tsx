import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useLibrary } from "@/hooks/useLibrary"
import { BookCard } from "@/components/BookCard"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/_app/library")({
  component: LibraryPage,
})

function LibraryPage() {
  const navigate = useNavigate()
  const { data: library, isLoading } = useLibrary()

  return (
    <div className="container mx-auto px-6 py-8 max-w-7xl">
      <h1 className="text-3xl font-bold tracking-tight mb-2">My Library</h1>
      <p className="text-sm text-muted-foreground mb-6">Your saved audiobooks</p>

      {isLoading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="aspect-square w-full rounded-lg" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      )}

      {!isLoading && library && library.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 animate-in fade-in duration-300">
          {library.map((item) => (
            <BookCard
              key={item.id}
              book={item}
              onClick={() =>
                navigate({
                  to: "/book/$addonId/$itemId",
                  params: { addonId: item.addon_id, itemId: item.external_id },
                })
              }
            />
          ))}
        </div>
      )}

      {!isLoading && library && library.length === 0 && (
        <div className="text-center py-16 flex flex-col items-center gap-4">
          <svg className="h-16 w-16 text-primary/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          <div className="space-y-1">
            <p className="font-medium text-foreground">Your library is empty</p>
            <p className="text-sm text-muted-foreground">Search for audiobooks and add them to your library</p>
          </div>
          <Button onClick={() => navigate({ to: "/search" })}>
            Search for books
          </Button>
        </div>
      )}
    </div>
  )
}
