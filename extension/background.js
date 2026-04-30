// F33 - Service worker background : fetch patterns + auth refresh.
const BACKEND = "http://localhost:8000";
const REFRESH_INTERVAL_MS = 60 * 60 * 1000; // 1h

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
  } catch (e) {
    // network or CORS issue, silent
  }
}

chrome.runtime.onInstalled.addListener(() => {
  fetchPatterns();
});

chrome.runtime.onStartup?.addListener(() => {
  fetchPatterns();
});

setInterval(fetchPatterns, REFRESH_INTERVAL_MS);

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
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
});
