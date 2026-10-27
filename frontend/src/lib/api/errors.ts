import type { ErrorBody, ErrorCode } from "@/lib/api/types"

/** Every failed API call becomes one of these (CONTRACT §3). */
export class ApiError extends Error {
  readonly status: number
  readonly code: ErrorCode
  readonly detail: string

  constructor(status: number, code: ErrorCode, detail: string) {
    super(detail)
    this.name = "ApiError"
    this.status = status
    this.code = code
    this.detail = detail
  }

  /** Build from any error response body, even one that is not the contract shape. */
  static from(status: number, body: unknown): ApiError {
    const b = (body ?? {}) as Partial<ErrorBody>
    const code: ErrorCode =
      typeof b.code === "string" ? b.code : status >= 500 ? "internal" : "validation"
    const detail =
      typeof b.detail === "string" ? b.detail : "Something went wrong. Please try again."
    return new ApiError(status, code, detail)
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError
}
