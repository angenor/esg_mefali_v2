// F33 - Popup login + profile display.
const BACKEND = "http://localhost:8000";

function t(key, fallback) {
  try {
    const m = chrome.i18n.getMessage(key);
    return m || fallback || key;
  } catch (e) {
    return fallback || key;
  }
}

function setStatus(text) {
  const el = document.getElementById("status");
  if (el) el.textContent = text;
}

async function loadJwt() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["jwt"], (r) => resolve(r.jwt || null));
  });
}

async function saveJwt(jwt) {
  return new Promise((resolve) => {
    chrome.storage.local.set({ jwt }, () => resolve());
  });
}

async function clearJwt() {
  return new Promise((resolve) => {
    chrome.storage.local.remove(["jwt"], () => resolve());
  });
}

async function fetchProfile() {
  const jwt = await loadJwt();
  if (!jwt) return null;
  try {
    const r = await fetch(`${BACKEND}/extension/profile-summary`, {
      headers: { Authorization: `Bearer ${jwt}` },
    });
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    return null;
  }
}

function renderLoggedIn(profile) {
  document.getElementById("login-form").hidden = true;
  document.getElementById("profile").hidden = false;
  document.getElementById("company-name").textContent =
    profile?.raison_sociale || "(profil incomplet)";
}

function renderLoggedOut() {
  document.getElementById("login-form").hidden = false;
  document.getElementById("profile").hidden = true;
}

async function init() {
  document.getElementById("title").textContent = t("popupTitle", "ESG Mefali");
  document.getElementById("lbl-email").textContent = t("loginEmail", "Email");
  document.getElementById("lbl-password").textContent = t("loginPassword", "Password");
  document.getElementById("btn-login").textContent = t("loginButton", "Login");
  document.getElementById("btn-refresh").textContent = t("refreshPatterns", "Refresh");
  document.getElementById("btn-logout").textContent = t("logoutButton", "Logout");

  const profile = await fetchProfile();
  if (profile) {
    renderLoggedIn(profile);
  } else {
    renderLoggedOut();
  }
}

document.getElementById("login-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  setStatus("...");
  try {
    const r = await fetch(`${BACKEND}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!r.ok) {
      setStatus(t("loginRequired"));
      return;
    }
    const data = await r.json();
    if (data.access_token) {
      await saveJwt(data.access_token);
      const p = await fetchProfile();
      if (p) renderLoggedIn(p);
      setStatus("");
    }
  } catch (e) {
    setStatus(t("loginRequired"));
  }
});

document.getElementById("btn-refresh").addEventListener("click", async () => {
  chrome.runtime.sendMessage({ type: "patterns:refresh" });
  setStatus("...");
});

document.getElementById("btn-logout").addEventListener("click", async () => {
  await clearJwt();
  renderLoggedOut();
});

init();
