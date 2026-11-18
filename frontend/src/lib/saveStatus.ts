export type SaveTone = "good" | "warn" | "bad" | "muted";
export type SaveStatus = { tone: SaveTone; text: string };

/**
 * Mensagem da barra de salvar de um formulário de ajustes. Com alterações pendentes, mostra o que impede
 * salvar ou quantas são; sem elas, a confirmação do último salvamento ou que não há nada pendente.
 */
export function saveStatus(saved: string | null, problem: string | null, pending: number): SaveStatus {
  if (pending > 0 && problem) return { tone: "bad", text: problem };
  if (pending === 1) return { tone: "warn", text: "1 alteração não salva" };
  if (pending > 1) return { tone: "warn", text: `${pending} alterações não salvas` };
  if (saved) return { tone: "good", text: saved };
  return { tone: "muted", text: "Nenhuma alteração pendente." };
}
