export const SETTINGS_KEY = "kookieSettings";

export const DEFAULT_SETTINGS = Object.freeze({
  voice: "af_sarah",
  rate: 1,
  volume: 1,
  sampleRate: 24000,
  theme: "system",
});

export async function loadSettings(storage = chrome.storage.local) {
  const result = await storage.get({ [SETTINGS_KEY]: DEFAULT_SETTINGS });
  return sanitizeSettings(result[SETTINGS_KEY]);
}

export async function saveSettings(storage = chrome.storage.local, updates = {}) {
  const current = await loadSettings(storage);
  const next = sanitizeSettings({ ...current, ...updates });
  await storage.set({ [SETTINGS_KEY]: next });
  return next;
}

export function sanitizeSettings(value = {}) {
  const candidate = value && typeof value === "object" ? value : {};
  return {
    voice: sanitizeVoice(candidate.voice),
    rate: clampNumber(candidate.rate, DEFAULT_SETTINGS.rate, 0.5, 2),
    volume: clampNumber(candidate.volume, DEFAULT_SETTINGS.volume, 0, 1),
    sampleRate: candidate.sampleRate === DEFAULT_SETTINGS.sampleRate ? DEFAULT_SETTINGS.sampleRate : 24000,
    theme: ["system", "light", "dark"].includes(candidate.theme) ? candidate.theme : DEFAULT_SETTINGS.theme,
  };
}

function sanitizeVoice(value) {
  const voice = typeof value === "string" ? value.trim() : "";
  return voice || DEFAULT_SETTINGS.voice;
}

function clampNumber(value, fallback, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, number));
}
