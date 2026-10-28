import { test, expect } from "@playwright/test";

test("LangGraph customer handoff is visible, persisted and reuses recommendations", async ({page}) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/#assistant");
  await page.getByRole("button", {name: "Use sample"}).click();
  await page.getByRole("button", {name: "Capture and save"}).click();
  const workflow = page.getByRole("region", {name: "Customer agent workflow"});
  await workflow.getByRole("button", {name: "Run agent workflow"}).click();
  await expect(workflow.getByRole("status")).toHaveText("Workflow result: partial");
  await expect(workflow.getByText(/generated and saved/)).toBeVisible();
  await expect(workflow.getByLabel("Agent communication trace")).toContainText("inventory procurement agent");
  await expect(workflow.getByRole("heading", {name: "Shiraz 750ml"})).toBeVisible();
  await expect(workflow.getByText(/Availability: Available/)).toBeVisible();
  await workflow.getByRole("button", {name: "Run agent workflow"}).click();
  await expect(workflow.getByText(/reused from SQLite/)).toBeVisible();
  await page.reload();
  await expect(workflow.getByRole("status")).toHaveText("Workflow result: partial");
  const recommendations = page.getByRole("region", {name: "Drink recommendations"});
  await expect(recommendations.getByText(/Reused from SQLite/)).toBeVisible();
  await page.setViewportSize({width: 390, height: 844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await workflow.screenshot({path: "test-results/agent-workflow-mobile.png"});
  expect(errors).toEqual([]);
});
