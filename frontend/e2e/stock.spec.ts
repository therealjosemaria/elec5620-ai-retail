import { test, expect } from "@playwright/test";

test("Operator stock lookup denies invalid access and returns exact stock evidence", async ({page}) => {
  await page.goto("/#inventory");
  await page.getByLabel(/Shiraz 750ml/).check();
  await page.getByLabel("Operator token").fill("wrong");
  await page.getByRole("button", {name: "Check selected stock"}).click();
  await expect(page.getByRole("alert")).toContainText("Operator access denied");
  await page.getByLabel("Operator token").fill("fixture-test-operator");
  await page.getByLabel(/Pale Ale 6-pack/).check();
  await page.getByLabel(/Premium Vodka 700ml/).check();
  await page.getByRole("button", {name: "Check selected stock"}).click();
  await expect(page.getByRole("heading", {name: "Stock lookup results"})).toBeVisible();
  const rows = page.locator("#inventory-panel tbody tr");
  await expect(rows).toHaveCount(3);
  await expect(rows.nth(0)).toContainText("24");
  await expect(rows.nth(0)).toContainText("found");
  await expect(rows.nth(1)).toContainText("stale");
  await expect(rows.nth(2)).toContainText("not_found");
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path: "test-results/stock-mobile.png", fullPage: true});
  await page.reload();
  await expect(page.getByLabel("Operator token")).toHaveValue("");
  await expect(page.getByRole("heading", {name: "Stock lookup results"})).toHaveCount(0);
});
