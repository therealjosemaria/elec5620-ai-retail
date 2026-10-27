import { test, expect } from "@playwright/test";

test("Member 2 catalogue recommendations preserve over-budget candidates and explain matches", async ({ page }) => {
  await page.goto("/#assistant");
  await page.getByRole("button", {name: "Use sample", exact: true}).click();
  await page.getByRole("button", {name: "Capture and save"}).click();
  await page.getByRole("button", {name: "Recommend drinks"}).click();
  const section = page.getByRole("region", {name: "Drink recommendations"});
  await expect(section.getByRole("status")).toHaveText("Recommendation result: complete");
  await expect(section.getByRole("heading", {name: /Shiraz/})).toBeVisible();
  await expect(section.getByRole("heading", {name: /Pinot Noir/})).toBeVisible();
  await expect(section.getByText(/Budget and current availability have not been checked/)).toBeVisible();
  await expect(section.getByText(/Your stated need/, {exact: false})).toHaveCount(2);
  await section.screenshot({path: "test-results/member2-recommendations.png"});
  await page.reload();
  await page.getByRole("button", {name: "Recommend drinks"}).click();
  await expect(section.getByRole("status")).toContainText("complete");
});

test("Member 2 restocking demo explains tied evidence, handles no priority, and fits mobile", async ({ page }) => {
  await page.setViewportSize({width: 390, height: 844});
  await page.goto("/#insights");
  await page.getByRole("button", {name: "Review sample priorities"}).click();
  const section = page.getByRole("region", {name: "Restocking demonstration"});
  await expect(section.getByRole("status")).toHaveText("Restocking result: presented");
  await expect(section.getByRole("heading", {name: /Priority 1/})).toHaveCount(2);
  await expect(section.getByText(/not current inventory or real operator authentication/)).toBeVisible();
  await section.screenshot({path: "test-results/member2-restocking-mobile.png"});
  await page.getByLabel("Sample category").selectOption("Beer");
  await expect(section.getByRole("heading", {name: /Priority 1/})).toHaveCount(0);
  await page.getByRole("button", {name: "Review sample priorities"}).click();
  await expect(section.getByRole("status")).toHaveText("Restocking result: no priority");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
