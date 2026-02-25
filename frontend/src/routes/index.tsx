import { createFileRoute, redirect } from "@tanstack/react-router"
import { api } from "@/lib/api"

export const Route = createFileRoute("/")({
  beforeLoad: async () => {
    try {
      await api.auth.me()
      throw redirect({ to: "/search" })
    } catch (err) {
      // Re-throw TanStack Router redirect objects
      if (
        err !== null &&
        typeof err === "object" &&
        "isRedirect" in err
      ) {
        throw err
      }
      // Auth failed — redirect to login
      throw redirect({ to: "/login" })
    }
  },
  component: () => null,
})
