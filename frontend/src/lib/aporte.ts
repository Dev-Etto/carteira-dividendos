/**
 * Quanto do caixa a investir o registro consome. O plano conta com todo o caixa guardado, mas se o usuário
 * deixar de executar alguma linha, aquele dinheiro continua guardado: as linhas desmarcadas saem primeiro do caixa.
 */
export function effectiveCashUsed(cashUsed: number, lines: { amount: number }[], selected: boolean[]): number {
  const skipped = lines.reduce((sum, line, i) => sum + (selected[i] ? 0 : line.amount), 0);
  return Math.max(0, Math.round((cashUsed - skipped) * 100) / 100);
}
