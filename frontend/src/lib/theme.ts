// Brand colours (spec L1). Tailwind classes use the same tokens from globals.css
// (bg-deep, text-green, bg-mint, text-warning, text-risk); this file is for charts and maps.
export const brand = {
  deep: "#0B3D3A",
  green: "#1E9E6A",
  mint: "#E6F4EE",
  warning: "#F2A35E",
  risk: "#D9534F",
} as const

export type Level = "low" | "medium" | "high"

const levelColours: Record<Level, string> = {
  low: brand.green,
  medium: brand.warning,
  high: brand.risk,
}

export function levelColour(level: Level): string {
  return levelColours[level]
}

export const levelLabel: Record<Level, string> = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
}
