import { readFileSync } from "node:fs"
import { join } from "node:path"

import { marked } from "marked"

export const metadata = { title: "Privacy notice · Home Resilience Passport" }

// `pnpm privacy:sync` copies docs/privacy.md here at dev/build time (see scripts/privacy-sync.mjs).
function readPrivacyMarkdown(): string {
  try {
    return readFileSync(join(process.cwd(), "src", "content", "privacy.md"), "utf8")
  } catch {
    return "# Privacy notice\n\nThis page is not available yet."
  }
}

export default function PrivacyPage() {
  const html = marked.parse(readPrivacyMarkdown(), { async: false })
  return (
    <section
      className="prose max-w-2xl [&_h1]:text-deep [&_h1]:text-2xl [&_h1]:font-semibold [&_h2]:text-deep [&_h2]:mt-6 [&_h2]:text-lg [&_h2]:font-semibold [&_li]:ml-4 [&_ul]:list-disc [&_p]:my-3"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
