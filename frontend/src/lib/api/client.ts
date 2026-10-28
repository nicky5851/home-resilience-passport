import createClient, { type Client } from "openapi-fetch"

import { ApiError } from "@/lib/api/errors"
import type { paths } from "@/lib/api/schema"
import { mockFetch } from "@/mocks/handler"

export const MOCK_MODE = process.env.NEXT_PUBLIC_API_MOCK === "1"

export type ApiClient = Client<paths>

/**
 * Typed client. The browser always calls relative /api/v1/...; Next.js rewrites it to the API,
 * so requests are same-origin and the browser sends Origin and the hrp_auth cookie itself.
 * In mock mode (NEXT_PUBLIC_API_MOCK=1) requests are answered from the demo fixtures.
 */
export function makeClient(options: { baseUrl?: string; fetch?: typeof fetch } = {}): ApiClient {
  return createClient<paths>({
    baseUrl: options.baseUrl ?? "",
    fetch: options.fetch ?? (MOCK_MODE ? mockFetch : (input) => globalThis.fetch(input)),
  })
}

export const api = makeClient()

type Result<T> = { data?: T; error?: unknown; response: Response }

/** Return the data, or throw an ApiError built from the contract error body. */
export function unwrap<T>({ data, error, response }: Result<T>): T {
  if (error !== undefined || !response.ok) throw ApiError.from(response.status, error)
  return data as T
}

/** Login is form-encoded (CONTRACT §4). */
export async function login(client: ApiClient, email: string, password: string): Promise<void> {
  unwrap(
    await client.POST("/api/v1/auth/login", {
      body: { username: email, password },
      bodySerializer: (body) => new URLSearchParams(body as Record<string, string>),
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  )
}

export async function logout(client: ApiClient): Promise<void> {
  unwrap(await client.POST("/api/v1/auth/logout"))
}
