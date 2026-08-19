import { describe, expect, it } from "vitest";

import { formatNumber, formatPercent, formatSigned } from "../lib/api";

describe("formatters", () => {
  it("renders a fraction as a percentage", () => {
    expect(formatPercent(0.2183)).toBe("21.83%");
    expect(formatPercent(-0.3517)).toBe("-35.17%");
  });

  it("keeps the sign explicit so a negative Sharpe cannot read as positive", () => {
    expect(formatSigned(1.04)).toBe("+1.04");
    expect(formatSigned(-0.23)).toBe("-0.23");
  });

  it("renders missing values as an em dash rather than zero", () => {
    // A metric that was never computed must not be displayed as 0.00%, which reads as
    // a real measurement of no effect.
    expect(formatPercent(undefined)).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
    expect(formatSigned(Number.NaN)).toBe("—");
  });
});
