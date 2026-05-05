// F33 - Content script : detection + bandeau + observation SPA (squelette).
(function () {
  let currentBanner = null;

  function t(key, fallback) {
    try {
      return chrome.i18n.getMessage(key) || fallback || key;
    } catch (e) {
      return fallback || key;
    }
  }

  function wildcardToRegex(pattern) {
    let re = "";
    for (const ch of pattern) {
      if (ch === "*") re += ".*";
      else re += ch.replace(/[.+?^${}()|[\]\\]/g, "\\$&");
    }
    return new RegExp("^" + re + "$", "i");
  }

  function matches(url, p) {
    try {
      if (p.pattern_type === "regex") return new RegExp(p.pattern, "i").test(url);
      return wildcardToRegex(p.pattern).test(url);
    } catch (e) {
      return false;
    }
  }

  function showBanner(label) {
    if (currentBanner) currentBanner.remove();
    const div = document.createElement("div");
    div.id = "esg-mefali-banner";
    div.textContent = `${t("offerDetected", "Offer detected")} : ${label}`;
    Object.assign(div.style, {
      position: "fixed",
      top: "0",
      left: "0",
      right: "0",
      zIndex: "2147483647",
      background: "#0b6e4f",
      color: "white",
      padding: "8px 16px",
      fontFamily: "system-ui, sans-serif",
      fontSize: "14px",
      boxShadow: "0 2px 8px rgba(0,0,0,0.12)",
    });
    document.documentElement.appendChild(div);
    currentBanner = div;
  }

  function clearBanner() {
    if (currentBanner) {
      currentBanner.remove();
      currentBanner = null;
    }
  }

  async function detect() {
    const url = window.location.href;
    chrome.runtime.sendMessage({ type: "patterns:get" }, (resp) => {
      const patterns = (resp && resp.patterns) || [];
      const hit = patterns.find((p) => matches(url, p));
      if (hit) {
        showBanner(hit.offre_label || hit.pattern || "");
        // F52 US4 — signaler le match au background pour ouvrir le sidepanel.
        // Aucun payload tenant transmis : seuls host/path/pattern_id partent.
        try {
          const u = new URL(url);
          chrome.runtime.sendMessage({
            type: "URL_DETECTED",
            payload: {
              host: u.host,
              path: u.pathname + (u.search || ""),
              pattern_id: hit.id || null,
            },
          });
        } catch (_e) {
          // ignore parsing errors
        }
      } else {
        clearBanner();
      }
    });
  }

  // SPA observation
  const _push = history.pushState;
  history.pushState = function () {
    const r = _push.apply(this, arguments);
    setTimeout(detect, 50);
    return r;
  };
  const _replace = history.replaceState;
  history.replaceState = function () {
    const r = _replace.apply(this, arguments);
    setTimeout(detect, 50);
    return r;
  };
  window.addEventListener("popstate", () => setTimeout(detect, 50));

  let debounce;
  const obs = new MutationObserver(() => {
    clearTimeout(debounce);
    debounce = setTimeout(detect, 300);
  });
  try {
    obs.observe(document.documentElement, { childList: true, subtree: true });
  } catch (e) {
    // pre-page DOM unavailable
  }

  detect();
})();
