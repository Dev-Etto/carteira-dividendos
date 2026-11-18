import { describe, expect, it } from "vitest";

import { hiddenCount, visibleItems } from "./lists";

describe("listas longas", () => {
  it("mostra os primeiros até expandir", () => {
    expect(visibleItems([1, 2, 3, 4], 2, false)).toEqual([1, 2]);
    expect(visibleItems([1, 2, 3, 4], 2, true)).toEqual([1, 2, 3, 4]);
  });
  it("conta os escondidos", () => {
    expect(hiddenCount(10, 5, false)).toBe(5);
    expect(hiddenCount(3, 5, false)).toBe(0);
    expect(hiddenCount(10, 5, true)).toBe(0);
  });
});
