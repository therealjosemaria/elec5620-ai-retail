// Explicit, manual acceptance check. Never part of npm test or the fixture suite.
// Requires a separately running live server. Makes at most TWO model submissions.
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir } from "node:fs/promises";

const conflictOnly = process.env.LIVE_CASE === "conflict";
const plannedCalls = conflictOnly ? 1 : 2;
if (process.env.CONFIRM_LIVE_CALLS !== String(plannedCalls)) {
  throw new Error(`Opt in explicitly with CONFIRM_LIVE_CALLS=${plannedCalls}`);
}
const base = process.env.LIVE_TEST_URL || "http://127.0.0.1:8002";
const status = await (await fetch(`${base}/api/status`)).json();
assert.equal(status.mode, "live");
assert.ok(status.live_configured, "Backend key missing");
assert.ok(status.local_daily_limit - status.live_attempts_today >= plannedCalls, "Insufficient local allowance");
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(e.message));
  await page.goto(base + "/#assistant");
  const cases = [
    {
      text: "I need dry red wine for a birthday for six people, under fifty dollars, no sweet drinks.",
      check(body) {
        assert.equal(body.needs.budget, "50");
        assert.equal(body.needs.party_size, 6);
        assert.match(body.needs.occasion, /birthday/);
        assert.match(body.needs.taste_preferences.join(" "), /red wine/);
        assert.match(body.needs.constraints.join(" "), /sweet/);
        assert.deepEqual(body.missing_fields, []);
      },
    },
    {
      text: "I want red wine. My budget is either $20 or $40; I have not decided which.",
      check(body) {
        assert.equal(body.needs.budget, null);
        assert.equal(body.needs.party_size, null);
        assert.equal(body.needs.occasion, null);
        assert.ok(body.missing_fields.includes("budget"));
        assert.match(body.needs.taste_preferences.join(" "), /red wine/);
      },
    },
  ];
  await mkdir("test-results", { recursive: true });
  for (let i = conflictOnly ? 1 : 0; i < cases.length; i++) {
    await page.getByLabel("What are you looking for?").fill(cases[i].text);
    const started = Date.now();
    const responsePromise = page.waitForResponse(r =>
      r.url().endsWith("/api/requests") && r.request().method() === "POST", { timeout: 45000 });
    await page.getByRole("button", { name: "Capture and save" }).click();
    const response = await responsePromise;
    assert.equal(response.status(), 201, "Stop on first failure; no automatic retry");
    const body = await response.json();
    cases[i].check(body);
    assert.equal(body.needs.status, "RequestConfirmed");
    await page.getByRole("heading", { name: "Saved in SQLite" }).waitFor();
    await page.reload();
    await page.getByRole("heading", { name: "Saved in SQLite" }).waitFor();
    const reread = await (await fetch(`${base}/api/requests/${body.request_id}`)).json();
    assert.deepEqual(reread, body);
    await page.screenshot({ path: `test-results/live-uc1-${i + 1}.png`, fullPage: true });
    console.log(JSON.stringify({case: i + 1, request_id: body.request_id, elapsed_ms: Date.now() - started,
      needs: body.needs, missing_fields: body.missing_fields}));
  }
  assert.deepEqual(errors, []);
} finally {
  await browser.close();
}
