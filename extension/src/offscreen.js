import { AssetManager } from "./assetManager.js";
import { WebAudioSink } from "./audioSink.js";
import { KokoroBrowserBackend } from "./kokoroBackend.js";
import { createMessage, MessageType, parseMessage } from "./messages.js";
import { PlaybackController } from "./playbackController.js";

const assetManager = new AssetManager();
const sink = new WebAudioSink();
const backend = new KokoroBrowserBackend({ assetManager });
const controller = new PlaybackController({
  backend,
  audioSink: sink,
  onEvent: (event) => chrome.runtime.sendMessage(createMessage(MessageType.OFFSCREEN_STATUS, event)),
});

chrome.runtime.onMessage.addListener((raw, _sender, sendResponse) => {
  handleMessage(raw).then(sendResponse, (error) => sendResponse({ ok: false, error: error.message }));
  return true;
});

async function handleMessage(raw) {
  const message = parseMessage(raw);
  const payload = message.payload ?? {};
  if (message.type === MessageType.OFFSCREEN_PLAY) {
    controller.setVolume(payload.volume ?? 1);
    controller.setRate(payload.rate ?? 1);
    const ok = await controller.start(payload.text, payload.voice ?? "af_sarah");
    return { ok, state: controller.state };
  }
  if (message.type === MessageType.OFFSCREEN_PAUSE) {
    return { ok: controller.pause(), state: controller.state };
  }
  if (message.type === MessageType.OFFSCREEN_RESUME) {
    return { ok: controller.resume(), state: controller.state };
  }
  if (message.type === MessageType.OFFSCREEN_STOP) {
    sink.stop();
    return { ok: controller.stop(), state: controller.state };
  }
  if (message.type === MessageType.GET_STATUS) {
    return { ok: true, state: controller.state, progress: controller.progress };
  }
  return { ok: false, error: `Unhandled message: ${message.type}` };
}
