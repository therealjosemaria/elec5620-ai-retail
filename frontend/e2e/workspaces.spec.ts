import { test, expect } from "@playwright/test";

test("Discover catalogue filters, searches and opens accessible product detail", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", {name: /Find your spirit/})).toBeVisible();
  await expect(page.getByText("6 catalogue products")).toBeVisible();
  await page.getByRole("button", {name: "Spirits", exact: true}).click();
  await expect(page.locator(".catalogue-card")).toHaveCount(1);
  await page.getByRole("button", {name: "View Premium Vodka 700ml", exact: true}).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog").getByText(/Availability has not been checked/)).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", {name: "All bottles", exact: true}).click();
  await page.getByRole("searchbox", {name: "Search catalogue"}).fill("not-a-product");
  await expect(page.getByText("No products match this search. Try another name or category.")).toBeVisible();
  await page.getByRole("searchbox", {name: "Search catalogue"}).fill("");
  await expect(page.locator(".catalogue-card")).toHaveCount(6);
  await page.screenshot({path: "test-results/discover-desktop.png", fullPage: true});
});

test("All three workspaces expose honest integration states and preserve navigation", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", {name: /02 Inventory & Procurement/}).click();
  await expect(page).toHaveURL(/#inventory$/);
  await expect(page.getByRole("heading", {name: /A clearer view/})).toBeVisible();
  await expect(page.getByRole("group", {name: "Select products"}).getByRole("checkbox")).toHaveCount(6);
  await expect(page.getByLabel("Operator token")).toBeVisible();
  await expect(page.getByRole("heading", {name: "Stock lookup results"})).toHaveCount(0);
  for (const title of ["Low-stock alerts", "Availability", "Reorder suggestions"]) {
    await page.getByRole("tab", {name: new RegExp(title)}).click();
    await expect(page.getByRole("tabpanel")).toContainText("No result has been generated.");
  }
  await page.getByRole("link", {name: "Business insights", exact: true}).click();
  await expect(page.getByRole("button", {name: "Review sample priorities"})).toBeVisible();
  await page.getByRole("tab", {name: /Profit margins/}).click();
  await expect(page.getByText(/The calculation module exists/)).toBeVisible();
  await page.getByRole("tab", {name: /Demand trends/}).click();
  await expect(page.getByText(/No sales trend is inferred/)).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", {name: /Good evidence/})).toBeVisible();
  await page.getByRole("link", {name: "Customer assistant", exact: true}).click();
  await expect(page.getByRole("heading", {name: "Budget filtering", exact: true})).toBeVisible();
  await expect(page.getByRole("heading", {name: "Product availability", exact: true})).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", {name: /Good evidence/})).toBeVisible();
});

test("All workspaces fit a mobile viewport and handle catalogue failure", async ({ page }) => {
  await page.setViewportSize({width: 390, height: 844});
  for (const hash of ["discover", "assistant", "inventory", "insights"]) {
    await page.goto(`/#${hash}`);
    await expect(page.getByRole("navigation").locator("[aria-current=page]")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({path: `test-results/${hash}-mobile.png`, fullPage: true});
  }
  await page.route("**/api/products", route => route.fulfill({status: 503, contentType: "application/json", body: "{}"}));
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("Catalogue unavailable");
  await expect(page.locator(".catalogue-card")).toHaveCount(0);
});
