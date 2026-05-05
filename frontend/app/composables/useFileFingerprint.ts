// F50 T009 — Composable SHA-256 client via Web Crypto API.

const HEX = "0123456789abcdef"

function bufferToHex(buf: ArrayBuffer): string {
  const view = new Uint8Array(buf)
  let out = ""
  for (let i = 0; i < view.length; i++) {
    const b = view[i]!
    out += HEX[(b >> 4) & 0xf] + HEX[b & 0xf]
  }
  return out
}

export function useFileFingerprint() {
  async function computeSha256(file: File): Promise<string> {
    if (typeof crypto === "undefined" || !crypto.subtle) {
      throw new Error("crypto.subtle indisponible")
    }
    const buf = await file.arrayBuffer()
    const digest = await crypto.subtle.digest("SHA-256", buf)
    return bufferToHex(digest)
  }

  return { computeSha256 }
}
