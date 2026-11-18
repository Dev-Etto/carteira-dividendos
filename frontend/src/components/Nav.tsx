"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Início" },
  { href: "/explorar", label: "Explorar" },
  { href: "/carteira", label: "Carteira" },
  { href: "/aporte", label: "Aporte do mês" },
  { href: "/renda-fixa", label: "Renda fixa" },
  { href: "/aprender", label: "Aprender" },
  { href: "/config", label: "Configurações" },
];

/** Marca do app: três barras crescentes, como proventos reinvestidos. */
function Logo() {
  return (
    <svg width="32" height="32" viewBox="0 0 44 44" aria-hidden="true">
      <rect width="44" height="44" rx="12" fill="var(--accent)" />
      <rect x="11" y="24" width="5" height="9" rx="2" fill="#ffffff" />
      <rect x="19.5" y="18" width="5" height="15" rx="2" fill="#ffffff" />
      <rect x="28" y="11" width="5" height="22" rx="2" fill="#9ed3de" />
    </svg>
  );
}

export function Nav() {
  const path = usePathname();
  const active = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex min-h-16 max-w-[1200px] flex-wrap items-center justify-between gap-x-6 gap-y-2 px-8 py-3">
        <Link href="/" className="flex items-center gap-2.5 text-ink">
          <Logo />
          <span className="text-[17px] font-bold tracking-tight">Carteira de Dividendos</span>
        </Link>
        <nav aria-label="Principal" className="flex flex-wrap gap-1">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={active(l.href) ? "page" : undefined}
              className={`flex h-9 items-center whitespace-nowrap rounded-[10px] px-3 text-sm transition ${
                active(l.href)
                  ? "bg-accent-soft font-semibold text-accent"
                  : "font-medium text-muted hover:bg-neutral-soft hover:text-ink"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
