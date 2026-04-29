import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { createMemoryChromeStorage } from "./support/fakes.js";
import { DEFAULT_SETTINGS, loadSettings, saveSettings } from "../src/settingsStore.js";

describe("settingsStore", () => {
  it("returns stable defaults when storage is empty", async () => {
    const storage = createMemoryChromeStorage();

    assert.deepEqual(await loadSettings(storage), DEFAULT_SETTINGS);
  });

  it("sanitizes saved settings and preserves supported values", async () => {
    const storage = createMemoryChromeStorage({
      kookieSettings: {
        voice: "af_bella",
        rate: 4,
        volume: -2,
        sampleRate: 48000,
        theme: "unexpected",
      },
    });

    assert.deepEqual(await loadSettings(storage), {
      ...DEFAULT_SETTINGS,
      voice: "af_bella",
      rate: 2,
      volume: 0,
      sampleRate: 24000,
    });
  });

  it("writes sanitized settings back to chrome storage", async () => {
    const storage = createMemoryChromeStorage();

    const saved = await saveSettings(storage, { voice: " ", rate: 0.1, volume: 0.4 });

    assert.equal(saved.voice, DEFAULT_SETTINGS.voice);
    assert.equal(saved.rate, 0.5);
    assert.equal(saved.volume, 0.4);
    assert.deepEqual(await loadSettings(storage), saved);
  });
});
