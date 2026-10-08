import { describe, expect, test } from "bun:test";
import { resolveApiBase, resolvePublicUrl, validateProductionApiBase } from "../src/api/urlConfig";

describe("API and public photo URLs", () => {
  test("development keeps the same-origin Vite proxies", () => {
    expect(resolveApiBase(undefined, false)).toBe("/api/v1");
    expect(resolvePublicUrl("/uploads/photo.jpg", "/api/v1")).toBe("/uploads/photo.jpg");
  });

  test("production normalizes one explicit base for requests and uploads", () => {
    expect(resolveApiBase("https://api.example.test/api/v1/", true)).toBe("https://api.example.test/api/v1");
  });

  test("production rejects missing, relative or unsafe configuration", () => {
    for (const value of [undefined, "", "/api/v1", "http://api.example.test/api/v1",
      "https://api.example.test", "https://user:pass@api.example.test/api/v1",
      "https://api.example.test/api/v1?x=1", "https://api.example.test/api/v1#x",
      " https://api.example.test/api/v1"]) {
      expect(() => validateProductionApiBase(value)).toThrow();
    }
  });

  test("original and thumbnail paths use the API origin without its prefix", () => {
    for (const path of ["/uploads/photos/original.jpg", "/uploads/photos/thumb.jpg"]) {
      expect(resolvePublicUrl(path, "https://api.example.test:8443/api/v1"))
        .toBe(`https://api.example.test:8443${path}`);
    }
  });

  test("photo references cannot redirect to another origin or leave uploads", () => {
    for (const path of ["https://other.test/photo", "//other.test/photo", "/api/v1/photo",
      "/uploads/../photo", "/uploads/\\other.test/photo", "/uploads/%2e%2e/photo",
      "/uploads/%2f../photo", "/uploads/photo.jpg?redirect=other"]) {
      expect(() => resolvePublicUrl(path, "https://api.example.test/api/v1")).toThrow();
    }
  });
});
