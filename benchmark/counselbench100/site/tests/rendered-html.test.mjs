import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the complete benchmark page", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /CounselBench-100/);
  assert.match(html, /Long-horizon legal work/);
  assert.match(html, /9,700/);
  assert.match(html, /69–97/);
  assert.match(html, /1,500/);
  assert.match(html, /100\/100/);
  assert.match(html, /exact-release score/);
  assert.doesNotMatch(html, /\b0\/10\b|GPT-5\.6-sol/);
  assert.match(html, /Harbor dataset/);
  assert.match(html, /Hugging Face/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|SkeletonPreview/);
});

test("release links and metadata remain pinned", async () => {
  const [page, layout, css] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);

  assert.match(page, /datasets\/blobfishai\/counselbench-100/);
  assert.match(page, /1,500/);
  assert.match(page, /Clio Manage v4/);
  assert.match(page, /v3\.2\.0/);
  assert.doesNotMatch(page, /filesystem MCP|v1\.0\.0/);
  assert.match(page, /CC BY 4\.0/);
  assert.match(layout, /og\.png/);
  assert.match(css, /--ink:\s*#0a1b2d/i);
  assert.match(css, /prefers-reduced-motion/);
});
