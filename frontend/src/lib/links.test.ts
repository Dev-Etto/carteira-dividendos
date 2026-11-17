import { describe, expect, it } from "vitest";

import { investidor10Url } from "./links";

describe("investidor10Url", () => {
  it.each([
    ["TAEE11", "acao", "https://investidor10.com.br/acoes/taee11/"],
    ["MXRF11", "fii", "https://investidor10.com.br/fiis/mxrf11/"],
    ["BOVA11", "etf", "https://investidor10.com.br/etfs/bova11/"],
    [" itub4 ", "acao", "https://investidor10.com.br/acoes/itub4/"],
    ["XYZW3", "desconhecida", "https://investidor10.com.br/acoes/xyzw3/"],
  ])("%s (%s) → %s", (ticker, assetClass, url) => {
    expect(investidor10Url(ticker, assetClass)).toBe(url);
  });
});
