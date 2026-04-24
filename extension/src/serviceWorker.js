import { AssetManager } from "./assetManager.js";
import { createMessage, MessageType, parseMessage } from "./messages.js";
import { loadSettings, saveSettings } from "./settingsStore.js";

const OFFSCREEN_URL = "offscreen.html";
const assetManager = new AssetManager();
let lastPlaybackStatus = { state: "idle", message: "", progress: { playedSamples: 0, synthesizedSamples: 0 } };

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "kookie-read-selection",
    title: "Read with Kookie",
    contexts: ["selection", "page"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab?.id) {
    return;
  }
  const text = info.selectionText?.trim() || (await extractTextFromTab(tab.id));
  if (text) {
    await playText(text);
  }
});

chrome.runtime.onMessage.addListener((raw, sender, sendResponse) => {
  handleMessage(raw, sender).then(sendResponse, (error) => sendResponse({ ok: false, error: error.message }));
  return true;
});

async function handleMessage(raw, sender) {
  const message = parseMessage(raw);
  if (message.type === MessageType.OFFSCREEN_STATUS) {
    lastPlaybackStatus = message.payload;
    return { ok: true };
  }
  if (message.type === MessageType.ASSET_STATUS) {
    return { ok: true, status: await assetManager.getStatus() };
  }
  if (message.type === MessageType.ENSURE_ASSETS) {
    return { ok: true, status: await assetManager.ensureAssets() };
  }
  if (message.type === MessageType.GET_SETTINGS) {
    return { ok: true, settings: await loadSettings() };
  }
  if (message.type === MessageType.SET_SETTINGS) {
    return { ok: true, settings: await saveSettings(chrome.storage.local, message.payload) };
  }
  if (message.type === MessageType.GET_STATUS) {
    return { ok: true, status: lastPlaybackStatus };
  }
  if (message.type === MessageType.PLAY) {
    return playText(message.payload.text, message.payload);
  }
  if (message.type === MessageType.PAUSE) {
    return sendOffscreen(MessageType.OFFSCREEN_PAUSE);
  }
  if (message.type === MessageType.RESUME) {
    return sendOffscreen(MessageType.OFFSCREEN_RESUME);
  }
  if (message.type === MessageType.STOP) {
    return sendOffscreen(MessageType.OFFSCREEN_STOP);
  }
  if (message.type === MessageType.EXTRACT_SELECTION) {
    const tabId = sender.tab?.id ?? (await activeTabId());
    const text = tabId ? await extractTextFromTab(tabId) : "";
    return { ok: true, text };
  }
  return { ok: false, error: `Unhandled message: ${message.type}` };
}

async function playText(text, overrides = {}) {
  const settings = await loadSettings();
  await assetManager.ensureAssets();
  return sendOffscreen(MessageType.OFFSCREEN_PLAY, {
    text,
    voice: overrides.voice ?? settings.voice,
    rate: overrides.rate ?? settings.rate,
    volume: overrides.volume ?? settings.volume,
  });
}

async function extractTextFromTab(tabId) {
  const [response] = await chrome.tabs.sendMessage(tabId, createMessage(MessageType.EXTRACT_SELECTION)).then(
    (value) => [value],
    async () => {
      await chrome.scripting.executeScript({ target: { tabId }, files: ["src/contentScript.js"] });
      return [await chrome.tabs.sendMessage(tabId, createMessage(MessageType.EXTRACT_SELECTION))];
    },
  );
  return response?.ok ? response.text : "";
}

async function activeTabId() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab?.id;
}

async function sendOffscreen(type, payload = {}) {
  await ensureOffscreenDocument();
  return chrome.runtime.sendMessage(createMessage(type, payload));
}

async function ensureOffscreenDocument() {
  const offscreenUrl = chrome.runtime.getURL(OFFSCREEN_URL);
  const contexts = await chrome.runtime.getContexts({
    contextTypes: ["OFFSCREEN_DOCUMENT"],
    documentUrls: [offscreenUrl],
  });
  if (contexts.length > 0) {
    return;
  }
  await chrome.offscreen.createDocument({
    url: OFFSCREEN_URL,
    reasons: ["AUDIO_PLAYBACK", "WORKERS", "BLOBS"],
    justification: "Kookie synthesizes local speech with ONNX and plays generated audio.",
  });
}
