// Runs on youtube.com pages. Reads the video's own caption track directly
// from the page, so transcript fetching happens over the user's own
// network instead of a server's -- YouTube blocks most cloud-provider IPs
// from its transcript/timedtext endpoint, but not regular browser traffic.

function findPlayerResponse() {
  for (const script of document.querySelectorAll("script")) {
    const text = script.textContent || "";
    const idx = text.indexOf("ytInitialPlayerResponse");
    if (idx === -1) continue;

    const start = text.indexOf("{", idx);
    let depth = 0;
    for (let i = start; i < text.length; i++) {
      if (text[i] === "{") depth++;
      else if (text[i] === "}") {
        depth--;
        if (depth === 0) {
          try {
            return JSON.parse(text.slice(start, i + 1));
          } catch (_) {
            return null;
          }
        }
      }
    }
  }
  return null;
}

async function extractTranscript() {
  const playerResponse = findPlayerResponse();
  const tracks = playerResponse?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
  if (!tracks || tracks.length === 0) {
    throw new Error("No captions available for this video");
  }

  const track = tracks.find((t) => t.languageCode?.startsWith("en")) || tracks[0];
  const res = await fetch(`${track.baseUrl}&fmt=json3`);
  if (!res.ok) throw new Error(`Could not load captions (${res.status})`);
  const data = await res.json();

  return (data.events || [])
    .flatMap((e) => e.segs || [])
    .map((s) => s.utf8 || "")
    .join("")
    .replace(/\s+/g, " ")
    .trim();
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== "GET_TRANSCRIPT") return false;
  extractTranscript()
    .then((text) => sendResponse({ ok: true, text }))
    .catch((err) => sendResponse({ ok: false, error: err.message }));
  return true; // keep the message channel open for the async response
});
