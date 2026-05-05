// F33 + F52 — Service worker background.
// F33 : fetch url-patterns, auth refresh, banner relay.
// F52 US4 : heartbeat ping toutes les 30 min, validation sender.tab.url,
// fetch /me/extension/sidepanel-context, push CONTEXT_READY au sidepanel.
// F52 US7 : abonnement EventSource sur deadline_j_minus_1 -> chrome.notifications.

const BACKEND = "http://localhost:8010";
const REFRESH_INTERVAL_MS = 60 * 60 * 1000; // 1h
const PING_INTERVAL_MS = 30 * 60 * 1000; // 30 min
const SIDEPANEL_PATH = "dist/sidepanel/index.html";

function getExtensionVersion() {
  try {
    return chrome.runtime.getManifest().version || "0.0.0";
  } catch (_e) {
    return "0.0.0";
  }
}

function getUserAgentSummary() {
  try {
    const ua = self.navigator?.userAgent || "";
    return ua.length > 200 ? ua.slice(0, 200) : ua;
  } catch (_e) {
    return "unknown";
  }
}

async function getJwt() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["jwt"], (r) => resolve(r.jwt || null));
  });
}

async function setPatterns(patterns) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ patterns, patterns_at: Date.now() }, () => resolve());
  });
}

async function fetchPatterns() {
  const jwt = await getJwt();
  if (!jwt) return;
  try {
    const r = await fetch(`${BACKEND}/extension/url-patterns`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    if (r.status === 401) {
      chrome.runtime.sendMessage({ type: "auth:expired" });
      return;
    }
    if (!r.ok) return;
    const body = await r.json();
    await setPatterns(body.items || []);
  } catch (_e) {
    // network or CORS issue, silent
  }
}

// ---------------------------------------------------------------------------
// F52 — Heartbeat ping
// ---------------------------------------------------------------------------

async function postPing() {
  try {
    const res = await fetch(`${BACKEND}/me/extension/ping`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        extension_version: getExtensionVersion(),
        user_agent_summary: getUserAgentSummary(),
      }),
    });
    if (res.status === 401) {
      chrome.runtime.sendMessage({
        type: "AUTH_REQUIRED",
        payload: { login_url: "https://app.esg-mefali.example/login" },
      });
    }
  } catch (_e) {
    // silent
  }
}

setInterval(fetchPatterns, REFRESH_INTERVAL_MS);
setInterval(postPing, PING_INTERVAL_MS);

chrome.runtime.onInstalled.addListener(() => {
  fetchPatterns();
  postPing();
});

chrome.runtime.onStartup?.addListener(() => {
  fetchPatterns();
  postPing();
});

// ---------------------------------------------------------------------------
// F52 — Sidepanel context fetching + push CONTEXT_READY
// ---------------------------------------------------------------------------

async function fetchSidepanelContext(host, path) {
  try {
    const url = new URL(`${BACKEND}/me/extension/sidepanel-context`);
    url.searchParams.set("host", host);
    url.searchParams.set("path", path);
    const res = await fetch(url.toString(), {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (res.status === 401) {
      chrome.runtime.sendMessage({
        type: "AUTH_REQUIRED",
        payload: { login_url: "https://app.esg-mefali.example/login" },
      });
      return null;
    }
    if (!res.ok) return null;
    return await res.json();
  } catch (_e) {
    return null;
  }
}

async function openSidepanelForTab(tabId, host, path) {
  try {
    if (chrome.sidePanel && chrome.sidePanel.setOptions) {
      await chrome.sidePanel.setOptions({
        tabId,
        path: `${SIDEPANEL_PATH}?host=${encodeURIComponent(host)}&path=${encodeURIComponent(path)}`,
        enabled: true,
      });
    }
    const ctx = await fetchSidepanelContext(host, path);
    if (ctx) {
      chrome.runtime.sendMessage({ type: "CONTEXT_READY", payload: ctx });
    }
  } catch (_e) {
    // silent
  }
}

// Validation : sender.tab.url doit matcher au moins un pattern actif.
function urlMatchesAnyPattern(url, patterns) {
  if (!url || !Array.isArray(patterns)) return false;
  return patterns.some((p) => {
    try {
      if (p.pattern_type === "regex") return new RegExp(p.pattern, "i").test(url);
      const re = "^" +
        p.pattern.replace(/[.+?^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*") +
        "$";
      return new RegExp(re, "i").test(url);
    } catch {
      return false;
    }
  });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "patterns:refresh") {
    fetchPatterns().then(() => sendResponse({ ok: true }));
    return true;
  }
  if (msg && msg.type === "patterns:get") {
    chrome.storage.local.get(["patterns"], (r) =>
      sendResponse({ patterns: r.patterns || [] }),
    );
    return true;
  }
  if (msg && msg.type === "URL_DETECTED") {
    const tabId = sender?.tab?.id;
    const senderUrl = sender?.tab?.url || "";
    chrome.storage.local.get(["patterns"], (r) => {
      const patterns = r.patterns || [];
      if (!urlMatchesAnyPattern(senderUrl, patterns)) {
        sendResponse({ ok: false, reason: "url_not_matched" });
        return;
      }
      const { host, path } = msg.payload || {};
      if (tabId && host && path) {
        openSidepanelForTab(tabId, host, path);
      }
      sendResponse({ ok: true });
    });
    return true;
  }
  if (msg && msg.type === "FORCE_PING") {
    postPing().then(() => sendResponse({ ok: true }));
    return true;
  }
  if (msg && msg.type === "OPEN_CANDIDATURE") {
    const id = msg.payload?.id;
    if (id) {
      chrome.tabs.create({
        url: `https://app.esg-mefali.example/candidatures/${id}`,
      });
    }
    return false;
  }
  if (msg && msg.type === "OPEN_MATCHING") {
    const offerId = msg.payload?.offer_id;
    if (offerId) {
      chrome.tabs.create({
        url: `https://app.esg-mefali.example/matching?offer=${offerId}`,
      });
    }
    return false;
  }
});

// ---------------------------------------------------------------------------
// F52 US7 — chrome.notifications sur deadline_j_minus_1 (P2).
// Le wrapper testable vit dans background-helpers/notifications.ts et
// est dupliqué ici en JS vanille car le service worker MV3 n'utilise
// pas de bundler. Tout changement dans la logique doit rester aligné
// avec les tests Vitest correspondants.
// ---------------------------------------------------------------------------

let notifSource = null;
const notifLinkRegistry = new Map();
let notifClickListenerInstalled = false;

function ensureNotificationClickListener() {
  if (notifClickListenerInstalled || !chrome.notifications?.onClicked) return;
  chrome.notifications.onClicked.addListener((id) => {
    const link = notifLinkRegistry.get(id);
    if (link && chrome.tabs) chrome.tabs.create({ url: link });
  });
  notifClickListenerInstalled = true;
}

function emitDeadlineNotification(data) {
  if (!data || data.kind !== "deadline_j_minus_1" || !chrome.notifications) {
    return;
  }
  const notifId = `deadline-${data.id || Date.now()}`;
  chrome.notifications.create(notifId, {
    type: "basic",
    iconUrl: "icons/icon128.png",
    title: data.title || "Échéance imminente",
    message: data.body || "Une candidature arrive à échéance demain.",
    priority: 2,
  });
  if (data.link) {
    notifLinkRegistry.set(notifId, data.link);
    ensureNotificationClickListener();
  }
}

function startNotificationStream() {
  if (notifSource) return;
  try {
    notifSource = new EventSource(`${BACKEND}/me/notifications/stream`, {
      withCredentials: true,
    });
    notifSource.addEventListener("notification.created", (evt) => {
      try {
        emitDeadlineNotification(JSON.parse(evt.data || "{}"));
      } catch {
        // payload mal formé — ignoré
      }
    });
    notifSource.onerror = () => {
      try {
        notifSource.close();
      } catch {
        // ignore
      }
      notifSource = null;
    };
  } catch (_e) {
    notifSource = null;
  }
}

chrome.runtime.onInstalled.addListener(() => startNotificationStream());
chrome.runtime.onStartup?.addListener(() => startNotificationStream());
