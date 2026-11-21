/**
 * Starter Playwright E2E gates graduating high-frequency findings from:
 *   checklists/frontend-vibe-coding-review.md (454-bug empirical study)
 *
 * Copy into your Playwright suite and wire BASE_URL, auth helper, and selectors
 * to your real application. Prove each test turns red by planting a violation.
 */

// import { test, expect } from "@playwright/test";

export interface GateTargets {
  disabledFeatureNavTestId: string;
  disabledFeatureRoute: string;
  disabledFeatureApiPath: string;
  listPageRoute: string;
  listApiGlob: string;
  errorBannerTestId: string;
  emptyStateTestId: string;
}

/**
 * Gate 1 — Disabled-Feature 3-Layer Agreement (catches 77% of entry/auth mismatches):
 * When a feature flag is false, verify ALL three layers agree:
 *   1. Navigation trigger is hidden in UI,
 *   2. Direct URL navigation shows blocked/unavailable state (not a broken shell),
 *   3. Direct backend API call rejects with 403 or 404.
 */
export async function assertDisabledFeatureThreeLayers(
  page: any,
  request: any,
  targets: GateTargets,
  expect: any,
): Promise<void> {
  await page.goto("/");
  await expect(page.getByTestId(targets.disabledFeatureNavTestId)).toHaveCount(0);

  await page.goto(targets.disabledFeatureRoute);
  await expect(page.getByRole("alert")).toBeVisible();

  const apiResp = await request.get(targets.disabledFeatureApiPath);
  expect([403, 404]).toContain(apiResp.status());
}

/**
 * Gate 2 — Error vs Empty Separation (catches `?? 0` / `|| []` plausible fake fallbacks):
 * Force the list API to return HTTP 500 and assert the UI displays an explicit
 * error banner instead of rendering "0 items" / the empty-state illustration.
 */
export async function assertErrorDoesNotRenderAsEmpty(
  page: any,
  targets: GateTargets,
  expect: any,
): Promise<void> {
  await page.route(targets.listApiGlob, (route: any) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ error: "simulated_backend_failure" }),
    }),
  );

  await page.goto(targets.listPageRoute);
  await expect(page.getByTestId(targets.errorBannerTestId)).toBeVisible();
  await expect(page.getByTestId(targets.emptyStateTestId)).toHaveCount(0);
}
