import { isApiError } from "@/lib/api/errors"

const MESSAGE: Record<string, string> = {
  not_found: "We couldn't find that home.",
  unauthorised: "Please sign in to see this.",
  validation: "Something about that request wasn't right.",
  rate_limited: "Too many requests — please wait a moment and try again.",
  upstream_unavailable: "That live data source isn't answering right now.",
  internal: "Something went wrong. Please try again.",
}

export function ErrorState({ error }: { error: unknown }) {
  const detail = isApiError(error) ? (MESSAGE[error.code] ?? error.detail) : "Something went wrong."
  return (
    <div className="s-card" role="alert">
      <p>{detail}</p>
    </div>
  )
}
