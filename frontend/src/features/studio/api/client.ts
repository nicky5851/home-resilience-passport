import createClient, { type Client } from "openapi-fetch"

import { ApiError } from "@/lib/api/errors"

import type { paths } from "@/features/studio/api/schema"

export type StudioClient = Client<paths>

/** Studio's own typed client, generated from its own OpenAPI snapshot (docs/openapi-studio.json).
 * Same relative-URL / Next.js-rewrite setup as the main client; Studio has no mock mode. */
export function makeStudioClient(): StudioClient {
  return createClient<paths>({ baseUrl: "" })
}

export const studioApi = makeStudioClient()

type Result<T> = { data?: T; error?: unknown; response: Response }

export function unwrap<T>({ data, error, response }: Result<T>): T {
  if (error !== undefined || !response.ok) throw ApiError.from(response.status, error)
  return data as T
}
