import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useLibrary } from "@/hooks/useLibrary"
import { BookCard } from "@/components/BookCard"
import { Skeleton } from "@/components/ui/skeleton"

export const Route = createFileRoute("/_app/library")({
  component: LibraryPage,
})

function LibraryPage() {
  const navigate = useNavigate()
  const { data: library, isLoading } = useLibrary()

  return (
    <div className="container mx-auto px-6 py-8 max-w-7xl">
      <h1 className="text-2xl font-bold mb-6">My Library</h1>

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
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
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
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg mb-2">Your library is empty</p>
          <p className="text-sm">Search for audiobooks and add them to your library</p>
        </div>
      )}
    </div>
  )
}
