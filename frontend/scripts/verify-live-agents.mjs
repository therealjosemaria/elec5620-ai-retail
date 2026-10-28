// Manual only. Never included in normal npm tests or CI.
import assert from "node:assert/strict";
import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const existingId = process.env.LIVE_EXISTING_REQUEST_ID;
const plannedCalls = existingId ? 0 : 2;
if (process.env.CONFIRM_LIVE_CALLS !== String(plannedCalls)) throw new Error(`Opt in with CONFIRM_LIVE_CALLS=${plannedCalls}`);
const base = process.env.LIVE_TEST_URL || "http://127.0.0.1:8005";
async function read(path, options) {
  const response = await fetch(base + path, options);
  assert.ok(response.ok, `HTTP ${response.status}; stop, no automatic retry`);
  return response.json();
}
const before = await read("/api/status");
assert.equal(before.mode, "live");
assert.ok(before.live_configured);
assert.ok(before.local_daily_limit - before.live_attempts_today >= plannedCalls);
const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.goto(base + "/#assistant");
  let request;
  if (existingId) {
    // Prove a usable cache exists before permitting a workflow POST.
    const cached = await read(`/api/requests/${existingId}/recommendations`);
    assert.equal(cached.cache_hit, true);
    assert.equal(cached.mode, "live");
    request = await read(`/api/requests/${existingId}`);
    await page.evaluate(id => localStorage.setItem("lastRequestId", id), existingId);
    await page.reload();
  } else {
    await page.getByLabel("What are you looking for?").fill(before.sample);
    const captureResponse = page.waitForResponse(r => r.url().endsWith("/api/requests") && r.request().method() === "POST", {timeout: 45000});
    await page.getByRole("button", {name: "Capture and save"}).click();
    const captured = await captureResponse;
    assert.equal(captured.status(), 201);
    request = await captured.json();
  }
  await page.getByRole("heading", {name: "Saved in SQLite"}).waitFor();
  const workflowResponse = page.waitForResponse(r => r.url().endsWith(`/api/requests/${request.request_id}/workflow`) && r.request().method() === "POST", {timeout: 45000});
  await page.getByRole("button", {name: "Run agent workflow"}).click();
  const response = await workflowResponse;
  assert.equal(response.status(), 200);
  const report = await response.json();
  assert.ok(["complete", "partial", "no_match"].includes(report.outcome));
  assert.equal(report.recommendations.mode, "live");
  assert.equal(report.recommendations.method, "campus_qwen_catalogue_recommendation");
  assert.equal(report.recommendations.cache_hit, Boolean(existingId));
  assert.equal(report.recommendations.outcome, "complete");
  assert.ok(report.recommendations.recommendations.length);
  const saved = await read(`/api/requests/${request.request_id}/recommendations`);
  assert.equal(saved.cache_hit, true);
  assert.deepEqual(saved.recommendations, report.recommendations.recommendations);
  const repeated = await read(`/api/requests/${request.request_id}/workflow`, {method: "POST"});
  assert.equal(repeated.recommendations.cache_hit, true);
  assert.deepEqual(repeated.recommendations.recommendations, saved.recommendations);
  const readback = await read(`/api/workflows/${repeated.workflow_id}`);
  assert.deepEqual(readback, repeated);
  const after = await read("/api/status");
  assert.equal(after.live_attempts_today - before.live_attempts_today, plannedCalls);
  await page.reload();
  await page.getByRole("region", {name: "Customer agent workflow"}).getByRole("status").waitFor();
  await mkdir("test-results", {recursive:true});
  await page.screenshot({path:"test-results/live-agent-workflow.png",fullPage:true});
  console.log(JSON.stringify({request_id:request.request_id,workflow_id:repeated.workflow_id,
    outcome:repeated.outcome,new_live_attempts:plannedCalls,cache_reuse:true,readback:true}));
} finally { await browser.close(); }
