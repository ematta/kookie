export const MESSAGE_NAMESPACE = "kookie";

export const MessageType = Object.freeze({
  ASSET_STATUS: "ASSET_STATUS",
  ENSURE_ASSETS: "ENSURE_ASSETS",
  GET_SETTINGS: "GET_SETTINGS",
  SET_SETTINGS: "SET_SETTINGS",
  GET_STATUS: "GET_STATUS",
  PLAY: "PLAY",
  PAUSE: "PAUSE",
  RESUME: "RESUME",
  STOP: "STOP",
  EXTRACT_SELECTION: "EXTRACT_SELECTION",
  OFFSCREEN_PLAY: "OFFSCREEN_PLAY",
  OFFSCREEN_PAUSE: "OFFSCREEN_PAUSE",
  OFFSCREEN_RESUME: "OFFSCREEN_RESUME",
  OFFSCREEN_STOP: "OFFSCREEN_STOP",
  OFFSCREEN_STATUS: "OFFSCREEN_STATUS",
});

export function createMessage(type, payload = {}) {
  return {
    namespace: MESSAGE_NAMESPACE,
    type,
    payload,
  };
}

export function parseMessage(message) {
  if (!message || message.namespace !== MESSAGE_NAMESPACE || typeof message.type !== "string" || !message.type) {
    throw new Error("Invalid message");
  }
  validatePayload(message.type, message.payload ?? {});
  return message;
}

function validatePayload(type, payload) {
  if (!payload || typeof payload !== "object") {
    throw new Error(`${type} payload must be an object`);
  }
  if ((type === MessageType.PLAY || type === MessageType.OFFSCREEN_PLAY) && typeof payload.text !== "string") {
    throw new Error(`${type} requires text`);
  }
  if (type === MessageType.SET_SETTINGS || type === MessageType.PLAY || type === MessageType.OFFSCREEN_PLAY) {
    for (const key of ["rate", "volume"]) {
      if (payload[key] !== undefined && typeof payload[key] !== "number") {
        throw new Error(`${key} must be a number`);
      }
    }
  }
}
