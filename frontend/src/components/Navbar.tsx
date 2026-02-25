import { Link, useNavigate } from "@tanstack/react-router"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"

export function Navbar() {
  const navigate = useNavigate()

  async function handleLogout() {
    await api.auth.logout()
    navigate({ to: "/login" })
  }

  return (
    <nav className="sticky top-0 z-40 border-b border-border bg-card/80 backdrop-blur-md px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2">
          <svg
            className="h-5 w-5 text-primary"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 18v-6a9 9 0 0 1 18 0v6"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"
            />
          </svg>
          <span className="font-bold text-xl tracking-tight text-foreground">Audiobookshelf</span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            to="/search"
            className="text-sm text-muted-foreground hover:text-primary transition-colors pb-0.5 [&.active]:text-foreground [&.active]:font-medium [&.active]:border-b-2 [&.active]:border-primary"
          >
            Search
          </Link>
          <Link
            to="/library"
            className="text-sm text-muted-foreground hover:text-primary transition-colors pb-0.5 [&.active]:text-foreground [&.active]:font-medium [&.active]:border-b-2 [&.active]:border-primary"
          >
            Library
          </Link>
          <Link
            to="/addons"
            className="text-sm text-muted-foreground hover:text-primary transition-colors pb-0.5 [&.active]:text-foreground [&.active]:font-medium [&.active]:border-b-2 [&.active]:border-primary"
          >
            Addons
          </Link>
        </div>
      </div>
      <Button variant="ghost" size="sm" onClick={handleLogout}>
        Logout
      </Button>
    </nav>
  )
}
