const SENTENCE_BOUNDARY = /(?<=[.!?])\s+/u;
const WHITESPACE = /\s+/gu;

export function normalizeText(text) {
  if (!text) {
    return "";
  }
  return Array.from(String(text).replace(/\u00a0/gu, " ").replace(/\u200b/gu, ""))
    .map((char) => (isPrintableOrWhitespace(char) ? char : " "))
    .join("")
    .replace(WHITESPACE, " ")
    .trim();
}

export function splitSentences(text, maxChars = 280) {
  if (maxChars <= 0) {
    throw new ValueError("maxChars must be greater than zero");
  }

  const normalized = normalizeText(text);
  if (!normalized) {
    return [];
  }

  const chunks = [];
  for (const segment of normalized.split(SENTENCE_BOUNDARY)) {
    const stripped = segment.trim();
    if (!stripped) {
      continue;
    }
    if (stripped.length <= maxChars) {
      chunks.push(stripped);
    } else {
      chunks.push(...chunkLongSegment(stripped, maxChars));
    }
  }
  return chunks;
}

function chunkLongSegment(segment, maxChars) {
  const chunks = [];
  let current = "";
  for (const word of segment.split(" ")) {
    if (!word) {
      continue;
    }
    if (word.length > maxChars) {
      if (current) {
        chunks.push(current);
        current = "";
      }
      chunks.push(...splitOversizedWord(word, maxChars));
      continue;
    }

    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxChars) {
      current = candidate;
      continue;
    }
    if (current) {
      chunks.push(current);
    }
    current = word;
  }
  if (current) {
    chunks.push(current);
  }
  return chunks;
}

function splitOversizedWord(word, maxChars) {
  const chunks = [];
  for (let index = 0; index < word.length; index += maxChars) {
    chunks.push(word.slice(index, index + maxChars));
  }
  return chunks;
}

function isPrintableOrWhitespace(char) {
  return /\s/u.test(char) || (!/\p{C}/u.test(char) && char.length > 0);
}

class ValueError extends Error {}
