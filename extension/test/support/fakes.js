export function createMemoryChromeStorage(initial = {}) {
  const data = { ...initial };
  return {
    async get(keys) {
      if (keys == null) {
        return { ...data };
      }
      if (typeof keys === "string") {
        return keys in data ? { [keys]: data[keys] } : {};
      }
      if (Array.isArray(keys)) {
        return Object.fromEntries(keys.filter((key) => key in data).map((key) => [key, data[key]]));
      }
      return Object.fromEntries(
        Object.entries(keys).map(([key, defaultValue]) => [key, key in data ? data[key] : defaultValue]),
      );
    },
    async set(values) {
      Object.assign(data, values);
    },
    async remove(keys) {
      for (const key of Array.isArray(keys) ? keys : [keys]) {
        delete data[key];
      }
    },
    snapshot() {
      return { ...data };
    },
  };
}

export function createResponse(value, { ok = true, status = 200 } = {}) {
  const bytes = new TextEncoder().encode(value);
  return {
    ok,
    status,
    headers: new Map([["Content-Length", String(bytes.byteLength)]]),
    async arrayBuffer() {
      return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    },
  };
}
