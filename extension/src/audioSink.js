export class WebAudioSink {
  constructor({ sampleRate = 24000 } = {}) {
    this.sampleRate = sampleRate;
    this.context = null;
    this.currentSource = null;
  }

  async play(chunk, { volume = 1 } = {}) {
    const context = await this.#context();
    const audio = chunk instanceof Float32Array ? chunk : new Float32Array(chunk);
    const buffer = context.createBuffer(1, audio.length, this.sampleRate);
    buffer.copyToChannel(audio.map((sample) => sample * volume), 0);

    await new Promise((resolve, reject) => {
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(context.destination);
      source.onended = () => {
        if (this.currentSource === source) {
          this.currentSource = null;
        }
        resolve();
      };
      try {
        this.currentSource = source;
        source.start();
      } catch (error) {
        reject(error);
      }
    });
    return audio.length;
  }

  stop() {
    if (this.currentSource) {
      try {
        this.currentSource.stop();
      } catch {
        // The source may already have ended.
      }
      this.currentSource = null;
    }
  }

  async #context() {
    if (!this.context) {
      const AudioContextCtor = globalThis.AudioContext || globalThis.webkitAudioContext;
      if (!AudioContextCtor) {
        throw new Error("Web Audio is unavailable");
      }
      this.context = new AudioContextCtor({ sampleRate: this.sampleRate });
    }
    if (this.context.state === "suspended") {
      await this.context.resume();
    }
    return this.context;
  }
}
