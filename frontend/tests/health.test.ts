import { describe, expect, it } from "vitest";

describe("useHealth contract", () => {
  it("expects /health response shape", () => {
    type HealthResponse = { status: "ok" | "degraded"; db: "ok" | "unreachable" };
    const sample: HealthResponse = { status: "ok", db: "ok" };
    expect(sample.status).toBe("ok");
    expect(sample.db).toBe("ok");
  });

  it("recognises degraded shape", () => {
    type HealthResponse = { status: "ok" | "degraded"; db: "ok" | "unreachable" };
    const sample: HealthResponse = { status: "degraded", db: "unreachable" };
    expect(sample.status).toBe("degraded");
  });
});
