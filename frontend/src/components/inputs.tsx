"use client";

import { type InputHTMLAttributes, type Ref } from "react";

import { inputCls, useFieldErrorId } from "@/components/ui";
import { maskDecimal, maskInteger, maskMoney, maskPercent, maskTicker } from "@/lib/masks";

/**
 * Props comuns dos campos com máscara. O valor é sempre o texto digitado (já mascarado); quem usa
 * converte e valida com as funções de `src/lib/validation.ts`. Dentro de um `Field` com erro à mostra,
 * o campo ganha `aria-invalid`, borda vermelha e `aria-describedby` apontando para a mensagem.
 */
export type TextInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "type"> & {
  value: string;
  onValueChange: (text: string) => void;
  ref?: Ref<HTMLInputElement>;
};

type MaskedProps = TextInputProps & { mask: (raw: string) => string; type?: string };

function identity(raw: string): string {
  return raw;
}

function MaskedInput({ mask, value, onValueChange, className = "", ...props }: MaskedProps) {
  const errorId = useFieldErrorId();
  return (
    <input
      {...props}
      className={`${inputCls} ${className}`}
      aria-invalid={errorId ? true : undefined}
      aria-describedby={errorId}
      value={value}
      onChange={(e) => onValueChange(mask(e.target.value))}
    />
  );
}

/** Valor em reais: só dígitos, pontos de milhar e vírgula com até 2 casas. */
export function MoneyInput(props: TextInputProps) {
  return <MaskedInput inputMode="decimal" placeholder="0,00" {...props} mask={maskMoney} />;
}

/** Percentual digitado como número ("6,5" para 6,5%), com até 4 casas; o "%" é descartado. */
export function PercentInput(props: TextInputProps) {
  return <MaskedInput inputMode="decimal" {...props} mask={maskPercent} />;
}

/** Número com casas decimais sem unidade, como P/VP ou Dívida/EBITDA. */
export function DecimalInput({ decimals = 4, ...props }: TextInputProps & { decimals?: number }) {
  return <MaskedInput inputMode="decimal" {...props} mask={(raw) => maskDecimal(raw, decimals)} />;
}

/** Número inteiro, como quantidade de cotas ou prazo em dias: só dígitos. */
export function IntegerInput(props: TextInputProps) {
  return <MaskedInput inputMode="numeric" {...props} mask={maskInteger} />;
}

/** Código de negociação da B3: maiúsculas, letras e dígitos, até 6 caracteres. */
export function TickerInput(props: TextInputProps) {
  return <MaskedInput autoCapitalize="characters" autoComplete="off" spellCheck={false} {...props} mask={maskTicker} />;
}

/** Data pelo seletor nativo (AAAA-MM-DD); limites com `min`/`max` e validação com `checkDate`. */
export function DateInput(props: TextInputProps) {
  return <MaskedInput {...props} type="date" mask={identity} />;
}
