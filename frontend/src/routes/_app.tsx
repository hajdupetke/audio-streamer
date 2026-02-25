import { useEffect } from "react"
import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router"
import { useAuth } from "@/hooks/useAuth"
import { Navbar } from "@/components/Navbar"
import { PlayerBar } from "@/components/PlayerBar"

export const Route = createFileRoute("/_app")({
  component: AppLayout,
})

function AppLayout() {
  const { isLoading, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate({ to: "/login" })
    }
  }, [isLoading, isAuthenticated, navigate])

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-muted-foreground text-sm">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      <main className="flex-1 pb-24">
        <div className="animate-in fade-in duration-300">
          <Outlet />
        </div>
      </main>
      <PlayerBar />
    </div>
  )
}
