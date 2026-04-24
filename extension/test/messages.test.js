import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { createMessage, parseMessage } from "../src/messages.js";

describe("messages", () => {
  it("creates typed messages with payloads", () => {
    assert.deepEqual(createMessage("PLAY", { text: "hello" }), {
      namespace: "kookie",
      type: "PLAY",
      payload: { text: "hello" },
    });
  });

  it("rejects malformed messages", () => {
    assert.throws(() => parseMessage(null), /Invalid message/);
    assert.throws(() => parseMessage({ namespace: "other", type: "PLAY" }), /Invalid message/);
    assert.throws(() => parseMessage({ namespace: "kookie", type: "" }), /Invalid message/);
  });

  it("validates known message payloads", () => {
    assert.throws(() => parseMessage(createMessage("PLAY", {})), /PLAY requires text/);
    assert.throws(() => parseMessage(createMessage("SET_SETTINGS", { rate: "fast" })), /rate must be a number/);
    assert.doesNotThrow(() => parseMessage(createMessage("SET_SETTINGS", { rate: 1.25, volume: 0.8 })));
  });
});
