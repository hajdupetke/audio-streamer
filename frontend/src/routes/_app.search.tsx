import { useState } from "react"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useSearch } from "@/hooks/useSearch"
import { useAddons } from "@/hooks/useAddons"
import { BookCard } from "@/components/BookCard"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export const Route = createFileRoute("/_app/search")({
  component: SearchPage,
})

function SearchPage() {
  const navigate = useNavigate()
  const [inputValue, setInputValue] = useState("")
  const [query, setQuery] = useState("")
  const [selectedAddon, setSelectedAddon] = useState<string>("all")

  const { data: addons } = useAddons()
  const contentSourceAddons = (addons ?? []).filter(
    (a) => a.enabled && a.capabilities.includes("content_source")
  )

  const addonIdParam = selectedAddon === "all" ? undefined : selectedAddon
  const { data, isLoading, isFetching } = useSearch(query, addonIdParam)

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setQuery(inputValue.trim())
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-7xl">
      <h1 className="text-2xl font-bold mb-6">Search Audiobooks</h1>

      <form onSubmit={handleSearch} className="flex gap-3 mb-6">
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Search for audiobooks..."
          className="max-w-md"
        />
        {contentSourceAddons.length > 0 && (
          <Select value={selectedAddon} onValueChange={setSelectedAddon}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="All addons" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All addons</SelectItem>
              {contentSourceAddons.map((addon) => (
                <SelectItem key={addon.id} value={addon.id}>
                  {addon.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Button type="submit" disabled={isLoading || isFetching}>
          {isFetching ? "Searching..." : "Search"}
        </Button>
      </form>

      {query && data && (
        <p className="text-sm text-muted-foreground mb-4">
          {data.results.length} result{data.results.length !== 1 ? "s" : ""} for &ldquo;{data.query}&rdquo;
        </p>
      )}

      {data && data.results.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {data.results.map((book) => (
            <BookCard
              key={`${book.addon_id}-${book.id}`}
              book={book}
              onClick={() =>
                navigate({
                  to: "/book/$addonId/$itemId",
                  params: { addonId: book.addon_id, itemId: book.id },
                })
              }
            />
          ))}
        </div>
      )}

      {query && data && data.results.length === 0 && !isFetching && (
        <div className="text-center py-16 text-muted-foreground">
          No results found for &ldquo;{data.query}&rdquo;
        </div>
      )}

      {!query && (
        <div className="text-center py-16 text-muted-foreground">
          Enter a search query to find audiobooks
        </div>
      )}
    </div>
  )
}
