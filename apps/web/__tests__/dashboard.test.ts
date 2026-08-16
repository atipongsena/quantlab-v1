import { HealthResponse, ModelComparisonResponse } from "../types/api";

describe("Web Dashboard Contracts & Models", () => {
  it("validates API response interfaces", () => {
    const health: HealthResponse = {
      status: "ok",
      version: "0.1.0",
    };
    expect(health.status).toBe("ok");

    const comparison: ModelComparisonResponse = {
      champion_model: "RIDGE",
      champion_reason: "Higher Rank IC",
      reports: [
        {
          model_name: "composite",
          mean_ic: 0.052,
          ic_ir: 1.85,
          top_bottom_spread: 0.04,
          is_monotonic: true,
        },
      ],
    };
    expect(comparison.champion_model).toBe("RIDGE");
    expect(comparison.reports.length).toBe(1);
  });
});
