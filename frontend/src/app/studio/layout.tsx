import { Fraunces, Inter, JetBrains_Mono } from "next/font/google"

import "@/features/studio/design/tokens.css"
import "@/features/studio/design/studio.css"

const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"] })
const studioInter = Inter({ variable: "--font-inter", subsets: ["latin"] })
const jetbrainsMono = JetBrains_Mono({ variable: "--font-jetbrains-mono", subsets: ["latin"] })

export const metadata = { title: "Resilience Studio · Home Resilience Passport" }

export default function StudioLayout({ children }: { children: React.ReactNode }) {
  return (
    <div
      className={`studio ${fraunces.variable} ${studioInter.variable} ${jetbrainsMono.variable}`}
    >
      <div className="space-y-6">{children}</div>
      <footer className="s-mono mt-12 border-t pt-4" style={{ borderColor: "var(--s-stone-200)" }}>
        Resilience Studio · estimates are labelled · sources on every page. Flood and postcode data
        © Environment Agency / Ordnance Survey; weather and climate data © Open-Meteo.
      </footer>
    </div>
  )
}
