import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it } from "node:test";

const root = resolve(import.meta.dirname, "..", "..");

describe("repo shape", () => {
  it("does not keep the retired Python desktop app tree", () => {
    for (const path of ["kookie", "tests", "packaging", "scripts", "pyproject.toml", "uv.lock", "main.py"]) {
      assert.equal(existsSync(resolve(root, path)), false, `${path} should be removed`);
    }
  });

  it("documents the extension as the only supported app", () => {
    const readme = readFileSync(resolve(root, "README.md"), "utf8");

    assert.match(readme, /Chrome extension/);
    assert.match(readme, /Load unpacked/);
    assert.doesNotMatch(readme, /uv run kookie/);
    assert.doesNotMatch(readme, /PyInstaller|PyQt|uv run|pytest/);
  });

  it("runs extension checks from the root Makefile", () => {
    const makefile = readFileSync(resolve(root, "Makefile"), "utf8");

    assert.match(makefile, /npm --prefix extension test/);
    assert.match(makefile, /npm --prefix extension run vendor/);
    assert.doesNotMatch(makefile, /uv run/);
  });
});
