/**
 * Whatcommerce platform bot — onboarding, billing, account help.
 * Run: npm run start:whatcommerce (from whatsapp/) or node whatcommerce/index.mjs
 */
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { startWorker } from "../shared/bridge.mjs";

const workerRoot = dirname(fileURLToPath(import.meta.url));

startWorker({
  workerRoot,
  channel: "whatcommerce",
  label: "Whatcommerce",
});
