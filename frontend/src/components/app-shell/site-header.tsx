"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"

import { api, logout } from "@/lib/api/client"
import { useUser } from "@/lib/auth/use-user"

export function SiteHeader() {
  const router = useRouter()
  const user = useUser()

  async function onLogout() {
    await logout(api)
    await user.refresh()
    router.push("/")
  }

  return (
    <header className="bg-deep text-white">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <Link
          href="/"
          className="rounded-sm font-semibold tracking-tight focus-visible:ring-2 focus-visible:ring-white focus-visible:outline-none"
        >
          Home Resilience Passport
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          {user.status === "authenticated" ? (
            <>
              <Link href="/homes" className="hover:underline">
                My homes
              </Link>
              <Link href="/account" className="hover:underline">
                Account
              </Link>
              <button type="button" onClick={onLogout} className="hover:underline">
                Log out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="hover:underline">
                Log in
              </Link>
              <Link href="/signup" className="hover:underline">
                Sign up
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
