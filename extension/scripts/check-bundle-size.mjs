#!/usr/bin/env node
// F52 — Vérifie la taille gzip des bundles JS du sidepanel.
// Échoue si le total dépasse 200 kB (NFR-002).
import { readFileSync, readdirSync, statSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("../dist/sidepanel/assets", import.meta.url));
const LIMIT_BYTES = 200 * 1024;

function listJs(dir) {
  let files = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) files = files.concat(listJs(full));
    else if (entry.endsWith(".js")) files.push(full);
  }
  return files;
}

let total = 0;
const detail = [];
try {
  for (const file of listJs(ROOT)) {
    const raw = readFileSync(file);
    const gz = gzipSync(raw).length;
    total += gz;
    detail.push({ file: file.replace(`${ROOT}/`, ""), gz });
  }
} catch (err) {
  if (err.code === "ENOENT") {
    console.error("[bundle-size] dist/sidepanel/assets introuvable — lancez build:sidepanel d'abord.");
    process.exit(1);
  }
  throw err;
}

for (const { file, gz } of detail) {
  console.log(`  ${file}\t${(gz / 1024).toFixed(1)} kB gzip`);
}
console.log(`Total gzip : ${(total / 1024).toFixed(1)} kB / ${LIMIT_BYTES / 1024} kB`);
if (total > LIMIT_BYTES) {
  console.error("[bundle-size] dépasse la cible 200 kB gzip (NFR-002).");
  process.exit(1);
}
