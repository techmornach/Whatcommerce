/**
 * Tenant store-manager bot — catalog, orders, customers (API wiring next).
 * One deployment typically maps to one tenant session; scale-out = more processes.
 * Run: npm run start:store-manager (from whatsapp/) or node store-manager/index.mjs
 */
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { startWorker } from "../shared/bridge.mjs";

const workerRoot = dirname(fileURLToPath(import.meta.url));

startWorker({
  workerRoot,
  channel: "store_manager",
  label: "Store manager",
});
