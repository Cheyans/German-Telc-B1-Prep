import { readFileSync, mkdirSync, copyFileSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { tmpdir } from "node:os";
import { chromium, firefox, webkit } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const [name, ...tests] = process.argv.slice(2);
const engines = { firefox: [firefox, {}], webkit: [webkit, {}], chromium: [chromium, {}], chrome: [chromium, { channel: "chrome" }] };
if (!engines[name] || !tests.length) {
  console.log("usage: node run-tests.mjs firefox|chromium|chrome|webkit heute-test.js [more tests]\nset B1_BASE=http://localhost:8000 to test a web server instead of the file");
  process.exit(1);
}
const copyDir = join(tmpdir(), "b1-compat-copy");
mkdirSync(copyDir, { recursive: true });
copyFileSync(join(root, "b1-wortschatz-geschichten.html"), join(copyDir, "B1-Kopie.html"));
globalThis.B1_BASE = (process.env.B1_BASE || pathToFileURL(root).href).replace(/\/$/, "");
globalThis.B1_FILE = globalThis.B1_BASE + "/b1-wortschatz-geschichten.html";
globalThis.B1_COPY = pathToFileURL(join(copyDir, "B1-Kopie.html")).href;
const [type, options] = engines[name];
const browser = await type.launch(options);
let failed = 0;
for (const t of tests) {
  const file = [join(here, t), join(root, "tools", t)].find(f => existsSync(f));
  const context = await browser.newContext();
  const page = await context.newPage();
  let out;
  try {
    out = String(await (0, eval)(readFileSync(file, "utf8"))(page));
  } catch (e) {
    out = "### Error\n" + e.message;
  }
  if (/^(FAIL|### Error)/m.test(out)) failed++;
  console.log(`== ${t} (${name})\n${out}`);
  await context.close();
}
await browser.close();
process.exit(failed ? 1 : 0);
