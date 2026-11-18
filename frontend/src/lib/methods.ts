import type { Method } from "./api/client";

/** Par de metodologias do perfil: uma para escolher as ações e outra para dividir a carteira. */
export type MethodChoice = { selection_method: string; allocation_method: string };

/** O que o usuário mexeu na tela, ainda sem salvar. Campo ausente segue o salvo. */
export type MethodDraft = Partial<MethodChoice>;

const FOCUS_LABEL: Record<string, string> = {
  renda: "Foco em renda",
  valor: "Foco em valor",
  valorizacao: "Foco em valorização",
  divisao: "Divisão da carteira",
};

/** Rótulo curto do foco da metodologia; foco desconhecido não ganha rótulo. */
export function focusLabel(focus: string): string | null {
  return FOCUS_LABEL[focus] ?? null;
}

/** Escolha efetiva: o rascunho por cima do que está salvo no perfil. */
export function resolveChoice(draft: MethodDraft, saved: MethodChoice): MethodChoice {
  return {
    selection_method: draft.selection_method ?? saved.selection_method,
    allocation_method: draft.allocation_method ?? saved.allocation_method,
  };
}

/** Se a escolha difere da salva e precisa ir para a API. */
export function choiceChanged(choice: MethodChoice, saved: MethodChoice): boolean {
  return choice.selection_method !== saved.selection_method || choice.allocation_method !== saved.allocation_method;
}

/**
 * Se o questionário deve manter a divisão-alvo atual. Só faz sentido para quem já tem perfil e pediu para manter,
 * e nunca quando a metodologia de divisão mudou: a divisão antiga pode nem ter as mesmas classes.
 */
export function shouldKeepAllocation(onboarded: boolean, keep: boolean, choice: MethodChoice, saved: MethodChoice): boolean {
  return onboarded && keep && choice.allocation_method === saved.allocation_method;
}

/** Nome da metodologia para mostrar; sem ela na lista, a própria chave. */
export function methodLabel(methods: Method[], key: string): string {
  return methods.find((m) => m.key === key)?.label ?? key;
}
