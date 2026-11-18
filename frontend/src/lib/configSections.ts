/** Seções da tela de Configurações, na ordem do menu. A chave vai na URL (`/config?secao=regras`). */
export const CONFIG_SECTIONS = [
  {
    key: "perfil",
    label: "Perfil e metodologias",
    description: "Seu perfil de risco e como o app escolhe ações e divide a carteira.",
  },
  { key: "divisao", label: "Divisão da carteira", description: "Quanto da carteira vai para cada classe de ativo." },
  { key: "regras", label: "Limites das regras", description: "Os números que decidem comprar, aguardar ou evitar." },
  { key: "dados", label: "Dados e atualização", description: "Quando os dados do mercado foram atualizados e o histórico." },
] as const;

export type ConfigSection = (typeof CONFIG_SECTIONS)[number]["key"];

export const SECTION_PARAM = "secao";
export const GROUP_PARAM = "grupo";

/** Seção pedida na URL; ausente ou desconhecida abre a primeira. */
export function sectionFromParam(param: string | null): ConfigSection {
  return CONFIG_SECTIONS.find((s) => s.key === param)?.key ?? CONFIG_SECTIONS[0].key;
}

/** Endereço da tela de Configurações numa seção (e, nos limites, num grupo). */
export function configHref(section: ConfigSection, group?: string): string {
  const params = new URLSearchParams({ [SECTION_PARAM]: section });
  if (group) params.set(GROUP_PARAM, group);
  return `/config?${params.toString()}`;
}
