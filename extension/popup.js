const DEFAULT_BACKEND = "http://localhost:8000";

const el = (id) => document.getElementById(id);

function extractVideoId(url) {
  if (!url) return null;
  try {
    const u = new URL(url);
    if (u.hostname === "youtu.be") return u.pathname.slice(1, 12) || null;
    if (u.hostname.endsWith("youtube.com")) {
      if (u.pathname === "/watch") return u.searchParams.get("v");
      if (u.pathname.startsWith("/shorts/")) return u.pathname.split("/")[2];
    }
  } catch (_) {}
  return null;
}

async function getBackendUrl() {
  const { backendUrl } = await chrome.storage.sync.get("backendUrl");
  return backendUrl || DEFAULT_BACKEND;
}

async function api(path, body) {
  const backend = await getBackendUrl();
  const res = await fetch(`${backend}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

async function getTranscriptFromPage(tabId) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, { type: "GET_TRANSCRIPT" }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error("Couldn't reach the page -- try reloading the YouTube tab."));
        return;
      }
      if (!response?.ok) {
        reject(new Error(response?.error || "Could not read the transcript from this page"));
        return;
      }
      resolve(response.text);
    });
  });
}

let currentVideoId = null;
let currentTabId = null;

async function init() {
  el("backendUrl").value = await getBackendUrl();

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  currentVideoId = extractVideoId(tab?.url);
  currentTabId = tab?.id;

  if (!currentVideoId) {
    el("notYoutube").classList.remove("hidden");
    el("loadState").classList.add("hidden");
    return;
  }

  el("videoLabel").textContent = `Video: ${currentVideoId}`;
  el("loadButton").disabled = false;
}

el("settingsToggle").addEventListener("click", () => {
  el("settingsPanel").classList.toggle("hidden");
});

el("saveSettings").addEventListener("click", async () => {
  await chrome.storage.sync.set({ backendUrl: el("backendUrl").value.trim() });
  el("settingsPanel").classList.add("hidden");
});

el("loadButton").addEventListener("click", async () => {
  el("loadButton").disabled = true;
  el("loadStatus").textContent = "Reading transcript from the page…";
  try {
    const transcript = await getTranscriptFromPage(currentTabId);
    el("loadStatus").textContent = "Indexing transcript…";
    const result = await api("/ingest", { video_id: currentVideoId, transcript });
    el("loadStatus").textContent = result.already_indexed
      ? "Already indexed -- ready."
      : `Indexed ${result.chunks_indexed} chunks -- ready.`;
    el("loadState").classList.add("hidden");
    el("qaState").classList.remove("hidden");
    el("readyLabel").textContent = `Ready: ${currentVideoId}`;
  } catch (err) {
    el("loadStatus").textContent = `Error: ${err.message}`;
    el("loadButton").disabled = false;
  }
});

el("askButton").addEventListener("click", async () => {
  const question = el("question").value.trim();
  if (!question) return;
  el("askButton").disabled = true;
  el("askButton").textContent = "Thinking…";
  try {
    const result = await api("/query", { video_id: currentVideoId, question });
    el("answerText").textContent = result.answer;
    el("sourcesList").innerHTML = result.sources
      .map((s) => `<li>${s.replace(/</g, "&lt;")}</li>`)
      .join("");
    el("answerBox").classList.remove("hidden");
  } catch (err) {
    el("answerText").textContent = `Error: ${err.message}`;
    el("answerBox").classList.remove("hidden");
  } finally {
    el("askButton").disabled = false;
    el("askButton").textContent = "Ask";
  }
});

init();
