// F50 T089 — useFileFingerprint : SHA-256 client via Web Crypto.
import { beforeEach, describe, expect, it, vi } from "vitest"

import { useFileFingerprint } from "../../../app/composables/useFileFingerprint"

function setSubtle(digest: (alg: string, data: ArrayBuffer) => Promise<ArrayBuffer>): void {
  ;(globalThis as { crypto?: unknown }).crypto = { subtle: { digest } } as Crypto
}

describe("useFileFingerprint (F50 T009/T089)", () => {
  beforeEach(() => {
    delete (globalThis as { crypto?: unknown }).crypto
  })

  it("calcule un hex SHA-256 depuis un File", async () => {
    // Digest stubbé : 32 octets nuls → 64 zéros hex.
    setSubtle(async () => new ArrayBuffer(32))
    const f = new File([new Uint8Array([1, 2, 3])], "x.bin", { type: "application/octet-stream" })
    const { computeSha256 } = useFileFingerprint()
    const hex = await computeSha256(f)
    expect(hex).toBe("0".repeat(64))
    expect(hex).toHaveLength(64)
  })

  it("encode correctement les octets non nuls (boundaries 0x00..0xff)", async () => {
    const out = new Uint8Array(32)
    for (let i = 0; i < 32; i++) out[i] = i * 8 // 0,8,16,...,248
    setSubtle(async () => out.buffer)
    const { computeSha256 } = useFileFingerprint()
    const hex = await computeSha256(new File([new Uint8Array([])], "y.bin"))
    // 0 → "00", 8 → "08", 16 → "10", … 248 → "f8"
    expect(hex.startsWith("000810")).toBe(true)
    expect(hex.endsWith("f8")).toBe(true)
    expect(/^[0-9a-f]{64}$/.test(hex)).toBe(true)
  })

  it("lève une erreur explicite si crypto.subtle est indisponible", async () => {
    // crypto undefined.
    const { computeSha256 } = useFileFingerprint()
    await expect(
      computeSha256(new File([new Uint8Array([])], "z.bin")),
    ).rejects.toThrow(/crypto.subtle/)
  })

  it("propage les erreurs de subtle.digest", async () => {
    setSubtle(async () => {
      throw new Error("boom")
    })
    const { computeSha256 } = useFileFingerprint()
    await expect(computeSha256(new File([new Uint8Array([1])], "z.bin"))).rejects.toThrow("boom")
  })
})
