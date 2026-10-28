import { test, expect } from "@playwright/test";

test("React → FastAPI → LangGraph fixture → SQLite → React, including reload", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/#assistant");
  await expect(page.getByText("Fixture mode · no AI calls")).toBeVisible();
  await page.getByRole("button", { name: "Use sample" }).click();
  await page.getByRole("button", { name: "Capture and save" }).click();
  await expect(page.getByRole("heading", { name: "Saved in SQLite" })).toBeVisible();
  await expect(page.getByText("30", { exact: true })).toBeVisible();
  await expect(page.getByText("RequestConfirmed", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Saved in SQLite" })).toBeVisible();
  await expect(page.getByText("0 / 5 university attempts recorded today (UTC). Provider quota is separate.")).toBeVisible();
  await page.screenshot({ path: "test-results/capture-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("heading", { name: "Saved in SQLite" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/capture-mobile.png", fullPage: true });
  expect(errors).toEqual([]);
});

test("fixture errors are visible and do not create a record", async ({ page }) => {
  await page.goto("/#assistant");
  await page.getByLabel("What are you looking for?").fill("Not the fixture");
  await page.getByRole("button", { name: "Capture and save" }).click();
  await expect(page.getByRole("alert")).toContainText("Fixture mode accepts only");
  await expect(page.getByRole("heading", { name: "Saved in SQLite" })).toHaveCount(0);
  await page.getByRole("button", {name: "Start a new request"}).click();
  await expect(page.getByLabel("What are you looking for?")).toHaveValue("");
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.getByRole("button", {name: "Use sample"}).click();
  await page.getByRole("button", {name: "Capture and save"}).click();
  await expect(page.getByRole("heading", {name: "Saved in SQLite"})).toBeVisible();
});
