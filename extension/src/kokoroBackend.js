const VOCAB = Object.freeze({
  ";": 1,
  ":": 2,
  ",": 3,
  ".": 4,
  "!": 5,
  "?": 6,
  "\"": 11,
  "(": 12,
  ")": 13,
  " ": 16,
  A: 24,
  I: 25,
  O: 31,
  S: 35,
  T: 36,
  W: 39,
  Y: 41,
  a: 43,
  b: 44,
  c: 45,
  d: 46,
  e: 47,
  f: 48,
  h: 50,
  i: 51,
  j: 52,
  k: 53,
  l: 54,
  m: 55,
  n: 56,
  o: 57,
  p: 58,
  q: 59,
  r: 60,
  s: 61,
  t: 62,
  u: 63,
  v: 64,
  w: 65,
  x: 66,
  y: 67,
  z: 68,
});

export class KokoroBrowserBackend {
  constructor({ assetManager, ortModuleLoader = defaultOrtModuleLoader } = {}) {
    this.assetManager = assetManager;
    this.ortModuleLoader = ortModuleLoader;
    this.sampleRate = 24000;
    this.#session = null;
    this.#voiceStyles = new Map();
  }

  #session;
  #ort;
  #voiceStyles;

  async listVoices() {
    return ["af_sarah"];
  }

  async validateVoice(voice) {
    const voices = await this.listVoices();
    if (!voices.includes(voice)) {
      throw new Error(`Unknown voice: ${voice}`);
    }
  }

  async *synthesizeSentences(sentences, voice = "af_sarah", { rate = 1 } = {}) {
    await this.validateVoice(voice);
    await this.#ensureLoaded(voice);

    for (const sentence of sentences) {
      const tokens = tokenizeForKokoro(sentence);
      if (tokens.length === 0) {
        continue;
      }
      const inputIds = BigInt64Array.from([0n, ...tokens.map((token) => BigInt(token)), 0n]);
      const style = this.#styleForVoice(voice, tokens.length);
      const feeds = {
        input_ids: new this.#ort.Tensor("int64", inputIds, [1, inputIds.length]),
        style: new this.#ort.Tensor("float32", style, [1, 256]),
        speed: new this.#ort.Tensor("float32", Float32Array.of(Number(rate) || 1), [1]),
      };
      const output = await this.#session.run(feeds);
      yield extractAudio(output);
    }
  }

  async #ensureLoaded(voice) {
    if (!this.#ort) {
      this.#ort = await this.ortModuleLoader();
      this.#ort.env.wasm.numThreads = 1;
    }
    if (!this.#session) {
      const modelBytes = await this.assetManager.loadAssetBytes("model");
      this.#session = await this.#ort.InferenceSession.create(modelBytes, {
        executionProviders: ["wasm"],
      });
    }
    if (!this.#voiceStyles.has(voice)) {
      const voiceBytes = await this.assetManager.loadAssetBytes("voices");
      this.#voiceStyles.set(voice, new Float32Array(voiceBytes));
    }
  }

  #styleForVoice(voice, tokenLength) {
    const styles = this.#voiceStyles.get(voice);
    if (!styles || styles.length < 256) {
      throw new Error(`Voice asset is invalid: ${voice}`);
    }
    const rowCount = Math.floor(styles.length / 256);
    const row = Math.min(Math.max(0, tokenLength), rowCount - 1);
    return styles.slice(row * 256, row * 256 + 256);
  }
}

export function tokenizeForKokoro(text) {
  const tokens = [];
  for (const char of text.slice(0, 510)) {
    const token = VOCAB[char] ?? VOCAB[char.toLowerCase()];
    if (token) {
      tokens.push(token);
    }
  }
  return tokens.slice(0, 510);
}

async function defaultOrtModuleLoader() {
  return import("../vendor/onnxruntime-web/ort.wasm.bundle.min.mjs");
}

function extractAudio(output) {
  const first = Object.values(output)[0];
  if (!first?.data) {
    throw new Error("Kokoro did not return audio");
  }
  return first.data instanceof Float32Array ? first.data : new Float32Array(first.data);
}
