import { normalizeText, splitSentences } from "./textProcessing.js";

export const PlaybackState = Object.freeze({
  IDLE: "idle",
  SYNTHESIZING: "synthesizing",
  PLAYING: "playing",
  PAUSED: "paused",
  STOPPING: "stopping",
  ERROR: "error",
});

export class PlaybackController {
  constructor({ backend, audioSink, onEvent, normalizer = normalizeText, chunker = splitSentences } = {}) {
    this.backend = backend;
    this.audioSink = audioSink;
    this.onEvent = onEvent;
    this.normalizer = normalizer;
    this.chunker = chunker;
    this.state = PlaybackState.IDLE;
    this.lastError = null;
    this.volume = 1;
    this.rate = 1;
    this.progress = { playedSamples: 0, synthesizedSamples: 0 };
    this.#running = null;
    this.#stopRequested = false;
  }

  #running;
  #stopRequested;
  #pauseResolvers = [];

  async start(text, voice = "af_sarah") {
    const normalized = this.normalizer(text);
    if (!normalized) {
      return false;
    }
    if (this.#running) {
      return false;
    }

    const sentences = this.chunker(normalized);
    if (sentences.length === 0) {
      return false;
    }

    this.lastError = null;
    this.progress = { playedSamples: 0, synthesizedSamples: 0 };
    this.#stopRequested = false;
    this.#setState(PlaybackState.SYNTHESIZING);
    this.#running = this.#run(sentences, voice).finally(() => {
      this.#running = null;
    });
    return true;
  }

  stop() {
    if (!this.#running && this.state === PlaybackState.IDLE) {
      return false;
    }
    this.#stopRequested = true;
    this.#releasePauseWaiters();
    if (this.state !== PlaybackState.ERROR) {
      this.#setState(PlaybackState.STOPPING);
    }
    return true;
  }

  pause() {
    if (!this.#running || this.state === PlaybackState.PAUSED || this.state === PlaybackState.ERROR) {
      return false;
    }
    this.#setState(PlaybackState.PAUSED);
    return true;
  }

  resume() {
    if (this.state !== PlaybackState.PAUSED) {
      return false;
    }
    this.#setState(PlaybackState.PLAYING);
    this.#releasePauseWaiters();
    return true;
  }

  setVolume(value) {
    this.volume = clamp(Number(value), 0, 1);
    return this.volume;
  }

  setRate(value) {
    this.rate = clamp(Number(value), 0.5, 2);
    return this.rate;
  }

  async waitUntilIdle() {
    if (this.#running) {
      await this.#running;
    }
  }

  async #run(sentences, voice) {
    try {
      const generator = this.backend.synthesizeSentences(sentences, voice, { rate: this.rate });
      for await (const chunk of generator) {
        if (this.#stopRequested) {
          break;
        }
        await this.#waitWhilePaused();
        if (this.#stopRequested) {
          break;
        }
        const audio = chunk instanceof Float32Array ? chunk : new Float32Array(chunk);
        this.progress.synthesizedSamples += audio.length;
        this.#setState(PlaybackState.PLAYING);
        const played = await this.audioSink.play(audio, { volume: this.volume, rate: this.rate });
        this.progress.playedSamples += Math.max(0, Number(played) || audio.length);
      }
      if (this.state !== PlaybackState.ERROR) {
        this.#setState(PlaybackState.IDLE);
      }
    } catch (error) {
      this.lastError = error instanceof Error ? error : new Error(String(error));
      this.#setState(PlaybackState.ERROR, this.lastError.message);
    }
  }

  async #waitWhilePaused() {
    while (this.state === PlaybackState.PAUSED && !this.#stopRequested) {
      await new Promise((resolve) => {
        this.#pauseResolvers.push(resolve);
      });
    }
  }

  #releasePauseWaiters() {
    for (const resolve of this.#pauseResolvers.splice(0)) {
      resolve();
    }
  }

  #setState(state, message = "") {
    this.state = state;
    this.onEvent?.({ state, message, progress: { ...this.progress } });
  }
}

function clamp(value, min, max) {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, value));
}
