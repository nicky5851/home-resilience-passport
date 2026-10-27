import type { Metadata } from "next"
import { Inter } from "next/font/google"

import { SiteFooter } from "@/components/app-shell/site-footer"
import { SiteHeader } from "@/components/app-shell/site-header"

import "./globals.css"

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Home Resilience Passport",
  description:
    "See your home's climate risks today and in 2050, your Resilience Score, and a costed plan to improve it.",
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en-GB" className={inter.variable}>
      <body className="flex min-h-dvh flex-col antialiased">
        <SiteHeader />
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>
        <SiteFooter />
      </body>
    </html>
  )
}
