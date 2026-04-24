chrome.runtime.onMessage.addListener((raw, _sender, sendResponse) => {
  try {
    if (!raw || raw.namespace !== "kookie" || raw.type !== "EXTRACT_SELECTION") {
      return false;
    }
    sendResponse({ ok: true, text: extractReadableText() });
  } catch (error) {
    sendResponse({ ok: false, error: error.message });
  }
  return true;
});

function extractReadableText(documentRef = document) {
  const selected = String(globalThis.getSelection?.() ?? "").trim();
  if (selected) {
    return selected;
  }
  const article = documentRef.querySelector("article, main");
  const source = article || documentRef.body;
  return source?.innerText?.replace(/\n{3,}/g, "\n\n").trim() ?? "";
}
