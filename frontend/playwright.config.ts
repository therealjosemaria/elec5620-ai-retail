import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:8001", browserName: "chromium" },
  webServer: {
    command: "MODEL_MODE=fixture LIVE_DAILY_LIMIT=5 DATABASE_PATH=../data/e2e.sqlite3 ../.venv/bin/python -m uvicorn backend.main:app --app-dir .. --host 127.0.0.1 --port 8001",
    url: "http://127.0.0.1:8001/api/status",
    reuseExistingServer: false,
  },
});
