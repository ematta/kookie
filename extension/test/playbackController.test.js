import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { PlaybackController, PlaybackState } from "../src/playbackController.js";

describe("PlaybackController", () => {
  it("rejects empty text", async () => {
    const controller = new PlaybackController({ backend: okBackend(), audioSink: fakeSink() });

    assert.equal(await controller.start("   "), false);
    assert.equal(controller.state, PlaybackState.IDLE);
  });

  it("rejects a second start while running", async () => {
    const gate = deferred();
    const controller = new PlaybackController({
      backend: {
        async *synthesizeSentences() {
          await gate.promise;
          yield new Float32Array([0.1, 0.2]);
        },
      },
      audioSink: fakeSink(),
    });

    assert.equal(await controller.start("hello"), true);
    assert.equal(await controller.start("hello again"), false);
    gate.resolve();
    await controller.waitUntilIdle();
  });

  it("plays synthesized chunks and returns to idle", async () => {
    const sink = fakeSink();
    const controller = new PlaybackController({ backend: okBackend(), audioSink: sink });

    assert.equal(await controller.start("one. two."), true);
    await controller.waitUntilIdle();

    assert.equal(controller.state, PlaybackState.IDLE);
    assert.equal(sink.chunks.length, 2);
    assert.equal(controller.progress.playedSamples, 4);
  });

  it("enters error state on synthesis failure", async () => {
    const controller = new PlaybackController({
      backend: {
        async *synthesizeSentences() {
          throw new Error("synthesis exploded");
        },
      },
      audioSink: fakeSink(),
    });

    assert.equal(await controller.start("boom"), true);
    await controller.waitUntilIdle();

    assert.equal(controller.state, PlaybackState.ERROR);
    assert.match(controller.lastError.message, /synthesis exploded/);
  });

  it("clamps volume and rate", () => {
    const controller = new PlaybackController({ backend: okBackend(), audioSink: fakeSink() });

    assert.equal(controller.setVolume(-1), 0);
    assert.equal(controller.setVolume(2), 1);
    assert.equal(controller.setRate(0), 0.5);
    assert.equal(controller.setRate(4), 2);
  });

  it("supports pause, resume, and stop state changes", async () => {
    const gate = deferred();
    const controller = new PlaybackController({
      backend: {
        async *synthesizeSentences() {
          yield new Float32Array([0.1]);
          await gate.promise;
          yield new Float32Array([0.2]);
        },
      },
      audioSink: fakeSink(),
    });

    assert.equal(await controller.start("hello. world."), true);
    assert.equal(controller.pause(), true);
    assert.equal(controller.state, PlaybackState.PAUSED);
    assert.equal(controller.resume(), true);
    assert.equal(controller.stop(), true);
    gate.resolve();
    await controller.waitUntilIdle();
    assert.equal(controller.state, PlaybackState.IDLE);
  });
});

function okBackend() {
  return {
    async *synthesizeSentences(sentences) {
      for (const _sentence of sentences) {
        yield new Float32Array(2).fill(0.1);
      }
    },
  };
}

function fakeSink() {
  return {
    chunks: [],
    async play(chunk, { volume }) {
      this.chunks.push({ chunk, volume });
      return chunk.length;
    },
  };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
