import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { normalizeText, splitSentences } from "../src/textProcessing.js";

describe("textProcessing", () => {
  it("collapses whitespace and removes non-printing characters", () => {
    const raw = "  Hello\t\tworld\n\nfrom\u0000 PDF\u200b copy   ";

    assert.equal(normalizeText(raw), "Hello world from PDF copy");
  });

  it("splits sentence boundaries in order", () => {
    assert.deepEqual(splitSentences("Hello world! This is a test. Final question?", 120), [
      "Hello world!",
      "This is a test.",
      "Final question?",
    ]);
  });

  it("chunks long text deterministically without exceeding max characters", () => {
    const text = Array.from({ length: 40 }, () => "word").join(" ");
    const chunksOne = splitSentences(text, 35);
    const chunksTwo = splitSentences(text, 35);

    assert.deepEqual(chunksOne, chunksTwo);
    assert.ok(chunksOne.every((chunk) => chunk.length <= 35));
    assert.equal(chunksOne.join(" ").replace(/\s+/g, " ").trim(), text);
  });

  it("splits oversized words", () => {
    assert.deepEqual(splitSentences("abcdefghij", 4), ["abcd", "efgh", "ij"]);
  });

  it("rejects non-positive max characters", () => {
    assert.throws(() => splitSentences("hello", 0), /maxChars must be greater than zero/);
    assert.throws(() => splitSentences("hello", -1), /maxChars must be greater than zero/);
  });
});
