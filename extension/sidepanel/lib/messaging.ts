// F52 US4 — Wrapper typé autour de chrome.runtime.sendMessage.
// Cf. contracts/extension-messaging.md.

import type { SidepanelContext } from "./api"

export type ContentToBackgroundMessage =
  | { type: "URL_DETECTED"; payload: { host: string; path: string; pattern_id?: string } }
  | { type: "PANEL_DISMISS"; payload: Record<string, never> }

export type BackgroundToSidepanelMessage =
  | { type: "CONTEXT_READY"; payload: SidepanelContext }
  | { type: "AUTH_REQUIRED"; payload: { login_url: string } }

export type SidepanelToBackgroundMessage =
  | { type: "OPEN_CANDIDATURE"; payload: { id: string } }
  | { type: "OPEN_MATCHING"; payload: { offer_id: string } }
  | { type: "FORCE_PING"; payload: Record<string, never> }

type AnyMessage =
  | ContentToBackgroundMessage
  | BackgroundToSidepanelMessage
  | SidepanelToBackgroundMessage

declare const chrome: {
  runtime?: {
    sendMessage: (msg: unknown) => Promise<unknown>
    onMessage: {
      addListener: (
        cb: (msg: unknown, sender: unknown, sendResponse: (r?: unknown) => void) => boolean | void
      ) => void
      removeListener: (
        cb: (msg: unknown, sender: unknown, sendResponse: (r?: unknown) => void) => boolean | void
      ) => void
    }
  }
}

export async function sendToBackground(msg: SidepanelToBackgroundMessage): Promise<unknown> {
  if (typeof chrome === "undefined" || !chrome.runtime) {
    throw new Error("chrome.runtime indisponible")
  }
  return chrome.runtime.sendMessage(msg)
}

export type IncomingHandler = (msg: BackgroundToSidepanelMessage) => void

export function onIncoming(handler: IncomingHandler): () => void {
  if (typeof chrome === "undefined" || !chrome.runtime) {
    return () => undefined
  }
  const wrapped = (raw: unknown): boolean | void => {
    if (!raw || typeof raw !== "object") return
    const m = raw as { type?: string }
    if (m.type === "CONTEXT_READY" || m.type === "AUTH_REQUIRED") {
      handler(raw as BackgroundToSidepanelMessage)
    }
  }
  chrome.runtime.onMessage.addListener(wrapped)
  return () => {
    if (chrome.runtime?.onMessage?.removeListener) {
      chrome.runtime.onMessage.removeListener(wrapped)
    }
  }
}

export type { AnyMessage }
