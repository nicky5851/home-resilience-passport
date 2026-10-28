// Copy docs/privacy.md into the front end for the /privacy page (spec L13), the same way
// mocks-sync.mjs copies the demo fixtures. Next.js cannot import files outside frontend/, so
// `pnpm dev`, `build`, `typecheck` and `test` run this first. The output file is git-ignored.
import { copyFileSync, mkdirSync, existsSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const src = join(here, "..", "..", "docs", "privacy.md")
const outDir = join(here, "..", "src", "content")
const out = join(outDir, "privacy.md")

mkdirSync(outDir, { recursive: true })
if (existsSync(src)) {
  copyFileSync(src, out)
  console.log("privacy:sync copied docs/privacy.md")
} else {
  writeFileSync(out, "# Privacy notice\n\nThis page is not available yet.\n")
  console.warn("privacy:sync: docs/privacy.md not found, wrote a placeholder")
}
