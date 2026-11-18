/** Botão "mostrar mais N" no fim de uma lista cortada; some quando não há nada escondido. */
export function ShowMoreButton({ hidden, onClick }: { hidden: number; onClick: () => void }) {
  if (hidden <= 0) return null;
  return (
    <button type="button" onClick={onClick} className="mt-3 text-sm font-semibold text-accent hover:text-accent-strong">
      Mostrar mais {hidden}
    </button>
  );
}
