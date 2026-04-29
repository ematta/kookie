import { mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(root, "..");
const dist = resolve(repoRoot, "dist");
const output = resolve(dist, "kookie-extension.zip");

await mkdir(dist, { recursive: true });
await rm(output, { force: true });

await run("zip", [
  "-r",
  output,
  "manifest.json",
  "popup.html",
  "offscreen.html",
  "src",
  "vendor",
]);

console.log(`Wrote ${output}`);

function run(command, args) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, {
      cwd: root,
      stdio: "inherit",
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolvePromise();
        return;
      }
      reject(new Error(`${command} exited with ${code}`));
    });
  });
}
