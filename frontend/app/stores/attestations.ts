// F49 T016 — Store Pinia useAttestationsStore.

import { defineStore } from "pinia"
import { attestationsApi } from "~/services/api/reports"
import type { Attestation, RevokeReason } from "~/types/attestations"

interface AttestationsStoreState {
  attestations: Attestation[]
  loading: boolean
  error: string | null
}

interface RuntimeConfigShape {
  public?: { apiBase?: string; appUrl?: string }
}

function appBaseUrl(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g = globalThis as any
  const cfg =
    (g.useRuntimeConfig?.() as RuntimeConfigShape | undefined) ??
    (g.useNuxtApp?.()?.$config as RuntimeConfigShape | undefined)
  const base = cfg?.public?.appUrl ?? cfg?.public?.apiBase ?? ""
  if (typeof window !== "undefined" && !cfg?.public?.appUrl) {
    return window.location.origin
  }
  return String(base).replace(/\/$/, "")
}

export const useAttestationsStore = defineStore("attestations", {
  state: (): AttestationsStoreState => ({
    attestations: [],
    loading: false,
    error: null,
  }),

  getters: {
    activeOnly(state): Attestation[] {
      return state.attestations.filter((a) => a.status === "active")
    },
    byId: (state) => (id: string) =>
      state.attestations.find((a) => a.id === id) ?? null,
  },

  actions: {
    async fetchAll(): Promise<void> {
      this.loading = true
      this.error = null
      try {
        this.attestations = await attestationsApi.fetchAll()
      } catch (err: unknown) {
        this.error =
          err instanceof Error
            ? err.message
            : "attestations.errors.fetch_failed"
      } finally {
        this.loading = false
      }
    },

    async revoke(id: string, reason: RevokeReason): Promise<void> {
      const updated = await attestationsApi.revoke(id, reason)
      const idx = this.attestations.findIndex((a) => a.id === id)
      if (idx >= 0) {
        const arr = [...this.attestations]
        arr[idx] = updated
        this.attestations = arr
      }
    },

    buildVerifyUrl(publicId: string): string {
      const base = appBaseUrl()
      return `${base}/verify/${publicId}`
    },

    async buildQrPng(publicId: string): Promise<Blob> {
      // Lib `qrcode` chargée à la demande pour ne pas peser sur le bundle initial.
      const qrcode = await import("qrcode")
      const url = this.buildVerifyUrl(publicId)
      const dataUrl = await qrcode.toDataURL(url, {
        errorCorrectionLevel: "H",
        width: 256,
        margin: 2,
      })
      // Convertit data URL → Blob
      const res = await fetch(dataUrl)
      return await res.blob()
    },
  },
})
