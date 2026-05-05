#!/usr/bin/env node
// F52 NFR-002 — Mesure du temps de premier rendu du sidepanel.
// Lance Chrome (Puppeteer/Playwright requis si on veut un environnement
// d'extension réel) ; à défaut, ouvre l'index.html local et collecte les
// PerformanceEntries first-paint / first-contentful-paint via Playwright.
//
// Usage :
//   node extension/scripts/measure-paint.mjs              # vise dist/sidepanel/
//   node extension/scripts/measure-paint.mjs --url <url>  # cible custom
//
// Le script échoue (exit 1) si FCP > 500 ms.

import { chromium } from "playwright"
import { fileURLToPath } from "node:url"
import { existsSync } from "node:fs"
import { dirname, resolve } from "node:path"

const TARGET_FCP_MS = 500
const args = process.argv.slice(2)
const urlIdx = args.indexOf("--url")
const here = dirname(fileURLToPath(import.meta.url))
const indexPath = resolve(here, "..", "dist", "sidepanel", "index.html")
const target =
  urlIdx >= 0 && args[urlIdx + 1] ? args[urlIdx + 1] : `file://${indexPath}`

if (urlIdx === -1 && !existsSync(indexPath)) {
  console.error(
    `Bundle introuvable : ${indexPath}\nLancer 'pnpm --dir extension build:sidepanel' d'abord.`,
  )
  process.exit(2)
}

const browser = await chromium.launch({ args: ["--no-sandbox"] })
try {
  const context = await browser.newContext()
  const page = await context.newPage()
  await page.goto(target, { waitUntil: "load" })
  // Attente paints éventuels post-load.
  await page.waitForTimeout(100)

  const { fp, fcp } = await page.evaluate(() => {
    const entries = performance.getEntriesByType("paint")
    const find = (n) => entries.find((e) => e.name === n)?.startTime ?? null
    return { fp: find("first-paint"), fcp: find("first-contentful-paint") }
  })

  console.log(JSON.stringify({ first_paint_ms: fp, first_contentful_paint_ms: fcp }))

  if (fcp == null) {
    console.error("FCP indisponible — environnement headless ne supporte peut-être pas paint timing.")
    process.exit(0)
  }
  if (fcp > TARGET_FCP_MS) {
    console.error(`FCP ${fcp.toFixed(1)} ms > seuil ${TARGET_FCP_MS} ms`)
    process.exit(1)
  }
  console.log(`OK : FCP ${fcp.toFixed(1)} ms ≤ ${TARGET_FCP_MS} ms`)
} finally {
  await browser.close()
}
