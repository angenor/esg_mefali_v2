// F52 US7 — Tests unitaires du wrapper background-helpers/notifications.ts
// (mock `chrome.notifications` et `chrome.tabs`).
import { describe, expect, it, vi } from "vitest"
import {
  buildNotificationId,
  buildNotificationOptions,
  handleDeadlineNotification,
  isDeadlineImminent,
  type ChromeNotificationsApi,
  type ChromeTabsApi,
} from "../../background-helpers/notifications"

function makeNotificationsMock(): {
  api: ChromeNotificationsApi
  create: ReturnType<typeof vi.fn>
  listeners: Array<(id: string) => void>
} {
  const create = vi.fn()
  const listeners: Array<(id: string) => void> = []
  const api: ChromeNotificationsApi = {
    create,
    onClicked: {
      addListener: (cb) => {
        listeners.push(cb)
      },
    },
  }
  return { api, create, listeners }
}

function makeTabsMock(): { api: ChromeTabsApi; create: ReturnType<typeof vi.fn> } {
  const create = vi.fn()
  return { api: { create }, create }
}

describe("isDeadlineImminent", () => {
  it("est vrai uniquement pour kind=deadline_j_minus_1", () => {
    expect(isDeadlineImminent({ kind: "deadline_j_minus_1" })).toBe(true)
    expect(isDeadlineImminent({ kind: "deadline_j_minus_7" })).toBe(false)
    expect(isDeadlineImminent({ kind: "system" })).toBe(false)
  })
})

describe("buildNotificationId", () => {
  it("utilise l'id du payload quand fourni", () => {
    const id = buildNotificationId(
      { kind: "deadline_j_minus_1", id: "abc" },
      () => 1
    )
    expect(id).toBe("deadline-abc")
  })

  it("retombe sur le timestamp via la callback now()", () => {
    const id = buildNotificationId({ kind: "deadline_j_minus_1" }, () => 12345)
    expect(id).toBe("deadline-12345")
  })
})

describe("buildNotificationOptions", () => {
  it("respecte les defaults si payload incomplet", () => {
    const opts = buildNotificationOptions(
      { kind: "deadline_j_minus_1" },
      "icons/icon128.png",
      "Default title",
      "Default message"
    )
    expect(opts).toEqual({
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "Default title",
      message: "Default message",
      priority: 2,
    })
  })

  it("utilise title/body du payload quand fournis", () => {
    const opts = buildNotificationOptions(
      { kind: "deadline_j_minus_1", title: "Custom", body: "Body" },
      "icons/icon128.png",
      "DT",
      "DM"
    )
    expect(opts.title).toBe("Custom")
    expect(opts.message).toBe("Body")
  })
})

describe("handleDeadlineNotification", () => {
  it("ignore les autres kinds", () => {
    const { api, create } = makeNotificationsMock()
    const res = handleDeadlineNotification(
      { kind: "deadline_j_minus_7" },
      { notifications: api }
    )
    expect(res).toEqual({ notified: false, reason: "wrong_kind" })
    expect(create).not.toHaveBeenCalled()
  })

  it("crée la notification système quand kind=deadline_j_minus_1", () => {
    const { api, create } = makeNotificationsMock()
    const res = handleDeadlineNotification(
      {
        kind: "deadline_j_minus_1",
        id: "n-1",
        title: "Demain",
        body: "Échéance imminente",
        link: "https://app.example/candidatures/c-1",
      },
      { notifications: api, tabs: makeTabsMock().api, now: () => 0 }
    )
    expect(res.notified).toBe(true)
    expect(res.notificationId).toBe("deadline-n-1")
    expect(create).toHaveBeenCalledWith("deadline-n-1", {
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: "Demain",
      message: "Échéance imminente",
      priority: 2,
    })
  })

  it("ouvre le lien dans un nouvel onglet sur clic", () => {
    const { api, listeners } = makeNotificationsMock()
    const tabs = makeTabsMock()
    handleDeadlineNotification(
      {
        kind: "deadline_j_minus_1",
        id: "n-2",
        link: "https://app.example/candidatures/c-2",
      },
      { notifications: api, tabs: tabs.api }
    )
    expect(listeners.length).toBe(1)
    listeners[0]("deadline-n-2")
    expect(tabs.create).toHaveBeenCalledWith({
      url: "https://app.example/candidatures/c-2",
    })
  })

  it("n'enregistre pas de listener si link absent", () => {
    const { api, listeners } = makeNotificationsMock()
    const res = handleDeadlineNotification(
      { kind: "deadline_j_minus_1", id: "n-3" },
      { notifications: api, tabs: makeTabsMock().api }
    )
    expect(res.notified).toBe(true)
    expect(res.reason).toBe("missing_link")
    expect(listeners.length).toBe(0)
  })

  it("ignore le clic sur une autre notification", () => {
    const { api, listeners } = makeNotificationsMock()
    const tabs = makeTabsMock()
    handleDeadlineNotification(
      {
        kind: "deadline_j_minus_1",
        id: "n-4",
        link: "https://app.example/candidatures/c-4",
      },
      { notifications: api, tabs: tabs.api }
    )
    listeners[0]("deadline-other")
    expect(tabs.create).not.toHaveBeenCalled()
  })
})
