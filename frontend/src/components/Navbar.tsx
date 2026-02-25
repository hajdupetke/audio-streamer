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
    <nav className="border-b border-border bg-card px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <span className="font-bold text-lg text-foreground">Audiobookshelf</span>
        <div className="flex items-center gap-4">
          <Link
            to="/search"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors [&.active]:text-foreground [&.active]:font-medium"
          >
            Search
          </Link>
          <Link
            to="/library"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors [&.active]:text-foreground [&.active]:font-medium"
          >
            Library
          </Link>
          <Link
            to="/addons"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors [&.active]:text-foreground [&.active]:font-medium"
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
