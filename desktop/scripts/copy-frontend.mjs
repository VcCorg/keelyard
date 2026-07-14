// Copy the built Vite SPA into desktop/resources/frontend for electron-builder.
// Run after `npm --prefix ../dashboard/frontend run build`.
import { cp, rm, mkdir, access } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.resolve(here, "..", "..", "dashboard", "frontend", "dist");
const dest = path.resolve(here, "..", "resources", "frontend");

try {
  await access(src);
} catch {
  console.error(`Frontend build not found at ${src}. Run the frontend build first.`);
  process.exit(1);
}

await rm(dest, { recursive: true, force: true });
await mkdir(dest, { recursive: true });
await cp(src, dest, { recursive: true });
console.log(`Copied frontend -> ${dest}`);
