import { describe, expect, it } from "vitest";

import { maskDecimal, maskInteger, maskMoney, maskPercent, maskTicker } from "./masks";

describe("maskMoney", () => {
  it.each([
    ["1500", "1500"],
    ["1.500,50", "1.500,50"],
    ["12,", "12,"],
    ["R$ 1.500,509", "1.500,50"],
    ["1,2,3", "1,23"],
    ["abc", ""],
    ["-30", "30"],
    ["10.5", "10.5"],
    ["", ""],
  ])("%j → %j", (raw, expected) => {
    expect(maskMoney(raw)).toBe(expected);
  });
});

describe("maskPercent", () => {
  it.each([
    ["6,5%", "6,5"],
    ["0,12345", "0,1234"],
    ["110", "110"],
  ])("%j → %j", (raw, expected) => {
    expect(maskPercent(raw)).toBe(expected);
  });
});

describe("maskDecimal", () => {
  it("sem casas decimais descarta a vírgula e o que vem depois", () => {
    expect(maskDecimal("12,5", 0)).toBe("12");
  });
});

describe("maskInteger", () => {
  it.each([
    ["100", "100"],
    ["1.000", "1000"],
    ["12,5", "125"],
    ["x3y", "3"],
  ])("%j → %j", (raw, expected) => {
    expect(maskInteger(raw)).toBe(expected);
  });
});

describe("maskTicker", () => {
  it.each([
    ["petr4", "PETR4"],
    ["taee 11", "TAEE11"],
    ["hglg11-x", "HGLG11"],
    ["B3SA3", "B3SA3"],
    ["ABCDEFGH", "ABCDEF"],
  ])("%j → %j", (raw, expected) => {
    expect(maskTicker(raw)).toBe(expected);
  });
});
