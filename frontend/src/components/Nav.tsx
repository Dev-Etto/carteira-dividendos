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

export function Nav() {
  const path = usePathname();
  const active = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));
  return (
    <nav className="flex gap-1 overflow-x-auto md:flex-col">
      {LINKS.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${
            active(l.href) ? "bg-accent-soft text-accent" : "text-muted hover:bg-neutral-soft hover:text-ink"
          }`}
        >
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
