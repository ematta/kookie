import { createMessage, MessageType } from "./messages.js";
import { DEFAULT_SETTINGS } from "./settingsStore.js";

const elements = {
  statusText: document.querySelector("#statusText"),
  assetStatus: document.querySelector("#assetStatus"),
  readerText: document.querySelector("#readerText"),
  voiceSelect: document.querySelector("#voiceSelect"),
  rateInput: document.querySelector("#rateInput"),
  rateValue: document.querySelector("#rateValue"),
  volumeInput: document.querySelector("#volumeInput"),
  volumeValue: document.querySelector("#volumeValue"),
  assetButton: document.querySelector("#assetButton"),
  playButton: document.querySelector("#playButton"),
  pauseButton: document.querySelector("#pauseButton"),
  resumeButton: document.querySelector("#resumeButton"),
  stopButton: document.querySelector("#stopButton"),
  importButton: document.querySelector("#importButton"),
};

await initialize();

elements.assetButton.addEventListener("click", ensureAssets);
elements.playButton.addEventListener("click", play);
elements.pauseButton.addEventListener("click", () => send(MessageType.PAUSE));
elements.resumeButton.addEventListener("click", () => send(MessageType.RESUME));
elements.stopButton.addEventListener("click", () => send(MessageType.STOP));
elements.importButton.addEventListener("click", importPageText);
elements.rateInput.addEventListener("input", persistSettings);
elements.volumeInput.addEventListener("input", persistSettings);
elements.voiceSelect.addEventListener("change", persistSettings);

async function initialize() {
  const settingsResponse = await send(MessageType.GET_SETTINGS);
  const settings = settingsResponse.settings ?? DEFAULT_SETTINGS;
  elements.voiceSelect.value = settings.voice;
  elements.rateInput.value = settings.rate;
  elements.volumeInput.value = settings.volume;
  renderSliderValues();
  await refreshAssets();
  await refreshStatus();
}

async function refreshAssets() {
  const response = await send(MessageType.ASSET_STATUS);
  renderAssetStatus(response.status);
}

async function ensureAssets() {
  elements.assetStatus.textContent = "Downloading assets...";
  const response = await send(MessageType.ENSURE_ASSETS);
  renderAssetStatus(response.status);
}

async function refreshStatus() {
  const response = await send(MessageType.GET_STATUS);
  const state = response.status?.state ?? "idle";
  elements.statusText.textContent = state;
}

async function importPageText() {
  const response = await send(MessageType.EXTRACT_SELECTION);
  if (response.ok && response.text) {
    elements.readerText.value = response.text;
    elements.statusText.textContent = "Imported page text";
  } else {
    elements.statusText.textContent = response.error || "No readable page text";
  }
}

async function play() {
  const text = elements.readerText.value;
  if (!text.trim()) {
    elements.statusText.textContent = "Enter text first";
    return;
  }
  await persistSettings();
  const response = await send(MessageType.PLAY, {
    text,
    voice: elements.voiceSelect.value,
    rate: Number(elements.rateInput.value),
    volume: Number(elements.volumeInput.value),
  });
  elements.statusText.textContent = response.ok ? response.state ?? "Playing" : response.error;
  await refreshAssets();
}

async function persistSettings() {
  renderSliderValues();
  await send(MessageType.SET_SETTINGS, {
    voice: elements.voiceSelect.value,
    rate: Number(elements.rateInput.value),
    volume: Number(elements.volumeInput.value),
  });
}

function renderSliderValues() {
  elements.rateValue.textContent = `${Number(elements.rateInput.value).toFixed(2)}x`;
  elements.volumeValue.textContent = `${Math.round(Number(elements.volumeInput.value) * 100)}%`;
}

function renderAssetStatus(status) {
  if (!status) {
    elements.assetStatus.textContent = "Assets unknown";
    return;
  }
  elements.assetStatus.textContent = status.ready ? "Assets ready" : status.errors.join("; ");
}

async function send(type, payload = {}) {
  return chrome.runtime.sendMessage(createMessage(type, payload));
}
