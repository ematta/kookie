export const ASSETS_KEY = "kookieAssets";

export const DEFAULT_ASSET_SPECS = Object.freeze([
  {
    name: "model",
    url: "https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main/onnx/model_quantized.onnx",
    filename: "kokoro-v1.0-quantized.onnx",
    sha256: null,
  },
  {
    name: "voices",
    url: "https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main/voices/af_sarah.bin",
    filename: "af_sarah.bin",
    sha256: null,
  },
]);

export class AssetManager {
  constructor({
    storage = chrome.storage.local,
    assetStore = createDefaultAssetStore(),
    fetcher = globalThis.fetch?.bind(globalThis),
    specs = DEFAULT_ASSET_SPECS,
    digest = sha256Hex,
    now = () => new Date().toISOString(),
  } = {}) {
    this.storage = storage;
    this.assetStore = assetStore;
    this.fetcher = fetcher;
    this.specs = specs;
    this.digest = digest;
    this.now = now;
  }

  async getStatus() {
    const stored = await this.#readStoredAssets();
    const errors = [];
    const assets = {};
    for (const spec of this.specs) {
      const asset = stored?.[spec.name];
      if (!asset || !(await this.assetStore.has(spec.name))) {
        errors.push(`${spec.name} missing`);
        continue;
      }
      assets[spec.name] = {
        byteLength: asset.byteLength,
        filename: asset.filename,
        sha256: asset.sha256 ?? null,
        updatedAt: asset.updatedAt ?? null,
      };
    }
    return {
      ready: errors.length === 0,
      assets,
      errors,
    };
  }

  async ensureAssets({ onProgress } = {}) {
    const initial = await this.getStatus();
    if (initial.ready) {
      return initial;
    }

    const downloaded = {};
    const errors = [];
    try {
      for (const spec of this.specs) {
        onProgress?.({ name: spec.name, phase: "downloading" });
        const bytes = await this.#download(spec);
        const sha256 = await this.digest(bytes);
        if (spec.sha256 && sha256.toLowerCase() !== spec.sha256.toLowerCase()) {
          throw new Error(`${spec.name} checksum mismatch: expected ${spec.sha256}, got ${sha256}`);
        }
        downloaded[spec.name] = {
          filename: spec.filename,
          url: spec.url,
          sha256,
          updatedAt: this.now(),
          byteLength: bytes.byteLength,
        };
        await this.assetStore.put(spec.name, bytes);
        onProgress?.({ name: spec.name, phase: "complete", byteLength: bytes.byteLength });
      }
      await this.storage.set({ [ASSETS_KEY]: downloaded });
    } catch (error) {
      await this.storage.remove(ASSETS_KEY);
      await this.assetStore.clear();
      errors.push(error instanceof Error ? error.message : String(error));
      return {
        ready: false,
        assets: {},
        errors,
      };
    }
    return this.getStatus();
  }

  async loadAssetBytes(name) {
    const stored = await this.#readStoredAssets();
    const asset = stored?.[name];
    if (!asset || !(await this.assetStore.has(name))) {
      throw new Error(`${name} missing`);
    }
    return this.assetStore.get(name);
  }

  async #download(spec) {
    if (typeof this.fetcher !== "function") {
      throw new Error("fetch is unavailable");
    }
    const response = await this.fetcher(spec.url);
    if (!response?.ok) {
      throw new Error(`${spec.name} download failed: HTTP ${response?.status ?? "unknown"}`);
    }
    return response.arrayBuffer();
  }

  async #readStoredAssets() {
    const result = await this.storage.get(ASSETS_KEY);
    return result[ASSETS_KEY] && typeof result[ASSETS_KEY] === "object" ? result[ASSETS_KEY] : {};
  }
}

export class MemoryAssetStore {
  #items = new Map();

  async has(name) {
    return this.#items.has(name);
  }

  async get(name) {
    const value = this.#items.get(name);
    if (!value) {
      throw new Error(`${name} missing`);
    }
    return value.slice(0);
  }

  async put(name, bytes) {
    this.#items.set(name, bytes.slice(0));
  }

  async clear() {
    this.#items.clear();
  }
}

export class IndexedDbAssetStore {
  constructor({ databaseName = "kookie-assets", storeName = "assets" } = {}) {
    this.databaseName = databaseName;
    this.storeName = storeName;
  }

  async has(name) {
    try {
      await this.get(name);
      return true;
    } catch {
      return false;
    }
  }

  async get(name) {
    const db = await this.#open();
    return new Promise((resolve, reject) => {
      const request = db.transaction(this.storeName, "readonly").objectStore(this.storeName).get(name);
      request.onsuccess = () => {
        const value = request.result?.bytes;
        if (!value) {
          reject(new Error(`${name} missing`));
          return;
        }
        resolve(value);
      };
      request.onerror = () => reject(request.error);
    });
  }

  async put(name, bytes) {
    const db = await this.#open();
    return new Promise((resolve, reject) => {
      const request = db.transaction(this.storeName, "readwrite").objectStore(this.storeName).put({ name, bytes });
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async clear() {
    const db = await this.#open();
    return new Promise((resolve, reject) => {
      const request = db.transaction(this.storeName, "readwrite").objectStore(this.storeName).clear();
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async #open() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.databaseName, 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName, { keyPath: "name" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
}

function createDefaultAssetStore() {
  return typeof indexedDB === "undefined" ? new MemoryAssetStore() : new IndexedDbAssetStore();
}

export async function sha256Hex(arrayBuffer) {
  const digest = await crypto.subtle.digest("SHA-256", arrayBuffer);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function arrayBufferToBase64(arrayBuffer) {
  const bytes = new Uint8Array(arrayBuffer);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

export function base64ToArrayBuffer(value) {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes.buffer;
}
