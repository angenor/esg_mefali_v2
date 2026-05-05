// F52 US7 — Wrapper testable autour de `chrome.notifications`.
// Le service worker `background.js` consomme un payload SSE
// `notification.created` ; lorsqu'il s'agit d'un kind `deadline_j_minus_1`
// nous émettons une notification système et associons un handler de clic
// qui ouvre le `link` dans un nouvel onglet.

export interface NotificationPayload {
  id?: string
  kind: string
  title?: string
  body?: string
  link?: string
}

export interface NotificationOptions {
  type: "basic"
  iconUrl: string
  title: string
  message: string
  priority: number
}

export interface ChromeNotificationsApi {
  create: (id: string, options: NotificationOptions) => void
  onClicked: {
    addListener: (cb: (id: string) => void) => void
  }
}

export interface ChromeTabsApi {
  create: (opts: { url: string }) => void
}

export interface DeadlineNotifierDeps {
  notifications: ChromeNotificationsApi
  tabs?: ChromeTabsApi
  iconUrl?: string
  defaultTitle?: string
  defaultMessage?: string
  now?: () => number
}

const DEFAULT_ICON = "icons/icon128.png"
const DEFAULT_TITLE = "Échéance imminente"
const DEFAULT_MESSAGE = "Une candidature arrive à échéance demain."

export function isDeadlineImminent(payload: NotificationPayload): boolean {
  return payload.kind === "deadline_j_minus_1"
}

export function buildNotificationId(
  payload: NotificationPayload,
  now: () => number
): string {
  return `deadline-${payload.id ?? now()}`
}

export function buildNotificationOptions(
  payload: NotificationPayload,
  iconUrl: string,
  defaultTitle: string,
  defaultMessage: string
): NotificationOptions {
  return {
    type: "basic",
    iconUrl,
    title: payload.title || defaultTitle,
    message: payload.body || defaultMessage,
    priority: 2,
  }
}

export interface DeadlineHandlerResult {
  notified: boolean
  reason?: "wrong_kind" | "missing_chrome_api" | "missing_link"
  notificationId?: string
}

export function handleDeadlineNotification(
  payload: NotificationPayload,
  deps: DeadlineNotifierDeps
): DeadlineHandlerResult {
  if (!isDeadlineImminent(payload)) {
    return { notified: false, reason: "wrong_kind" }
  }
  if (!deps.notifications) {
    return { notified: false, reason: "missing_chrome_api" }
  }
  const now = deps.now ?? Date.now
  const notificationId = buildNotificationId(payload, now)
  const options = buildNotificationOptions(
    payload,
    deps.iconUrl ?? DEFAULT_ICON,
    deps.defaultTitle ?? DEFAULT_TITLE,
    deps.defaultMessage ?? DEFAULT_MESSAGE
  )
  deps.notifications.create(notificationId, options)
  if (payload.link && deps.tabs) {
    const link = payload.link
    deps.notifications.onClicked.addListener((id) => {
      if (id === notificationId) {
        deps.tabs?.create({ url: link })
      }
    })
  }
  return {
    notified: true,
    notificationId,
    reason: payload.link ? undefined : "missing_link",
  }
}
