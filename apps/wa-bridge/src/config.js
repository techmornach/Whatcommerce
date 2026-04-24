export const config = {
  bridgePort: Number(process.env.BRIDGE_PORT || 3001),
  bridgeHost: process.env.BRIDGE_HOST || "0.0.0.0",
  internalSecret: process.env.INTERNAL_SECRET || "change-me-in-dev",
  apiBaseUrl: process.env.API_BASE_URL || "http://127.0.0.1:8000",
  tenantId: process.env.DEFAULT_TENANT_ID || "dev-tenant-1",
  /** Optional: pin Chromium in Docker (e.g. /usr/bin/chromium) */
  puppeteerExecutablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined,
};
