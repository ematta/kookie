import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { AssetManager, DEFAULT_ASSET_SPECS, MemoryAssetStore } from "../src/assetManager.js";
import { createMemoryChromeStorage, createResponse } from "./support/fakes.js";

describe("AssetManager", () => {
  it("reports missing assets before first download", async () => {
    const manager = new AssetManager({ storage: createMemoryChromeStorage() });

    assert.deepEqual(await manager.getStatus(), {
      ready: false,
      assets: {},
      errors: ["model missing", "voices missing"],
    });
  });

  it("downloads missing assets, stores bytes, and records a manifest", async () => {
    const calls = [];
    const manager = new AssetManager({
      storage: createMemoryChromeStorage(),
      fetcher: async (url) => {
        calls.push(url);
        return createResponse(url.includes("voices") ? "voices-data" : "model-data");
      },
      specs: [
        { ...DEFAULT_ASSET_SPECS[0], sha256: "78af4dc485eb32a809e795bfca78a4f5313401b58d9bc81cc4d1b89445b97333" },
        { ...DEFAULT_ASSET_SPECS[1], sha256: "aaa1aa15401af660b4e3b2a590116df79e4ae3d264d8b5c35d897f4d2ca12490" },
      ],
    });

    const status = await manager.ensureAssets();

    assert.equal(status.ready, true);
    assert.equal(calls.length, 2);
    assert.equal(status.assets.model.byteLength, "model-data".length);
    assert.equal(status.assets.voices.byteLength, "voices-data".length);
  });

  it("does not refetch assets when the stored manifest is reusable", async () => {
    const storage = createMemoryChromeStorage();
    const assetStore = new MemoryAssetStore();
    const first = new AssetManager({
      storage,
      assetStore,
      fetcher: async (url) => createResponse(url.includes("voices") ? "voices-data" : "model-data"),
    });
    await first.ensureAssets();

    const second = new AssetManager({
      storage,
      assetStore,
      fetcher: async () => {
        throw new Error("fetch should not be called");
      },
    });

    assert.equal((await second.ensureAssets()).ready, true);
  });

  it("rejects checksum mismatches without storing partial assets", async () => {
    const storage = createMemoryChromeStorage();
    const manager = new AssetManager({
      storage,
      fetcher: async () => createResponse("bad-data"),
      specs: [{ ...DEFAULT_ASSET_SPECS[0], sha256: "0000" }, DEFAULT_ASSET_SPECS[1]],
    });

    const status = await manager.ensureAssets();

    assert.equal(status.ready, false);
    assert.match(status.errors.join("\n"), /checksum mismatch/);
    assert.equal((await storage.get("kookieAssets")).kookieAssets, undefined);
  });
});
