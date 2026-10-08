import { expect, test } from "bun:test";

test("public review loading and submission use the configured API origin", async () => {
  const previousBase = process.env.VITE_API_BASE_URL;
  const originalFetch = globalThis.fetch;
  process.env.VITE_API_BASE_URL = "https://api.example.invalid/api/v1";
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify({
      intervention: { title: "Test", completed_at: "2026-10-07T00:00:00" },
      technician: { full_name: null },
      already_reviewed: false,
    }), { status: 200, headers: { "Content-Type": "application/json" } });
  }) as typeof fetch;
  try {
    const { reviewsApi } = await import("../src/api/client");
    await reviewsApi.get("test/token");
    const submission = { share_token: "test/token", rating: 5, comment: null, reviewer_name: null };
    await reviewsApi.submit(submission);
    expect(calls.map(call => call.url)).toEqual([
      "https://api.example.invalid/api/v1/review/test%2Ftoken",
      "https://api.example.invalid/api/v1/reviews",
    ]);
    expect(calls[1].init?.method).toBe("POST");
    expect(JSON.parse(String(calls[1].init?.body))).toEqual(submission);
    for (const call of calls) {
      expect(new Headers(call.init?.headers).has("Authorization")).toBe(false);
    }
  } finally {
    globalThis.fetch = originalFetch;
    if (previousBase === undefined) delete process.env.VITE_API_BASE_URL;
    else process.env.VITE_API_BASE_URL = previousBase;
  }
});
