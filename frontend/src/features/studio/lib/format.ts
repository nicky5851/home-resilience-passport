/** Pure formatting helpers used across every Studio feature (no React, easy to unit-test). */

export function formatGbp(amount: number): string {
  const sign = amount < 0 ? "-" : ""
  return `${sign}£${Math.round(Math.abs(amount)).toLocaleString("en-GB")}`
}

export function formatNumber(value: number, options?: Intl.NumberFormatOptions): string {
  return new Intl.NumberFormat("en-GB", options).format(value)
}

/** 'YYYY-MM-DD' or an ISO timestamp -> '28 Oct 2026'. */
export function formatDate(iso: string): string {
  const d = new Date(iso)
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(d)
}

export function formatTime(iso: string): string {
  const d = new Date(iso)
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/London",
  }).format(d)
}
