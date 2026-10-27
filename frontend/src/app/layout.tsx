import type { Metadata } from "next";

import { Nav } from "@/components/Nav";

import "./globals.css";

export const metadata: Metadata = {
  title: "Carteira de Dividendos",
  description: "Assistente local de investimentos em dividendos pelo método Barsi",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className="h-full antialiased">
      <body className="min-h-full">
        <div className="mx-auto flex min-h-screen max-w-7xl flex-col md:flex-row">
          <aside className="border-b border-line px-4 py-4 md:sticky md:top-0 md:h-screen md:w-56 md:shrink-0 md:border-b-0 md:border-r md:py-6">
            <div className="mb-4 px-3">
              <div className="text-sm font-semibold text-ink">Carteira de Dividendos</div>
              <div className="text-xs text-muted">método Barsi · uso pessoal</div>
            </div>
            <Nav />
            <p className="mt-6 hidden px-3 text-[11px] leading-relaxed text-muted md:block">
              O app aplica regras e explica o resultado. Não é recomendação de investimento; a decisão é sua.
            </p>
          </aside>
          <main className="min-w-0 flex-1 px-4 py-6 md:px-8 md:py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
