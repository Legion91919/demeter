// Scripted walkthrough for the README demo. Run: node demo/record.mjs .
import { resolve } from "node:path";

const sample = name => resolve(import.meta.dirname, "../samples", name);

async function load(page, name) {
  await page.getByLabel("Borrower rent roll (CSV)").setInputFiles(sample(name));
  await page.locator("#upload-result").evaluate(el => (el.innerHTML = ""));
  await page.getByRole("button", { name: "Load file" }).click();
  await page.locator("#upload-result .note").waitFor();
  await page.getByRole("button", { name: "Load file" }).and(page.locator(":enabled")).waitFor();
}

export default async ({ page, step, shot }) => {
  await step("Demeter starts empty: no rent rolls loaded, nothing to trust yet", async () => {
    await page.locator("#properties").getByText("No rent rolls loaded").waitFor();
  });
  await step("Two borrowers, two different layouts: each file reconciles to its own total", async () => {
    await load(page, "keelridge-estates_2026-10.csv");
    await page.waitForTimeout(700);
    await load(page, "marlowe-bay_2026-10.csv");
  });
  await shot("portfolio");
  await step("Tidewater's rows don't add up to its stated total: quarantined with the exact difference", async () => {
    await load(page, "tidewater-living_2026-10_v1-bad-total.csv");
    await page.waitForTimeout(1200);
  });
  await shot("quarantine");
  await step("Nothing was half-loaded: the job run records why the file was refused", async () => {
    await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" }));
    await page.waitForTimeout(1200);
  });
  await step("The corrected file loads, and Tidewater Mews joins the portfolio", async () => {
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
    await load(page, "tidewater-living_2026-10_v2.csv");
    await page.getByRole("cell", { name: "Tidewater Mews" }).waitFor();
  });
  await step("Every dashboard figure traces back to its source file, line and raw text", async () => {
    await page.getByRole("cell", { name: "Tidewater Mews" }).click();
    await page.locator("#lineage").getByText("equals the dashboard figure").waitFor();
    await page.waitForTimeout(1200);
    await page.evaluate(() => window.scrollBy({ top: 320, behavior: "smooth" }));
    await page.waitForTimeout(1200);
  });
  await shot("lineage");
};

export async function mobile({ page, shot }) {
  await page.getByRole("cell", { name: "Keelridge Quay" }).first().waitFor();
  await shot("mobile");
}
