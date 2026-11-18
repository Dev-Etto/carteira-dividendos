import type { Metadata } from "next";
import { Figtree } from "next/font/google";

import { Nav } from "@/components/Nav";

import "./globals.css";

const figtree = Figtree({ subsets: ["latin"], weight: ["400", "500", "600", "700", "800"], variable: "--font-figtree" });

export const metadata: Metadata = {
  title: "Carteira de Dividendos",
  description: "Assistente local de investimentos em dividendos pelo método Barsi",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${figtree.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <Nav />
        <main className="mx-auto w-full min-w-0 max-w-[1200px] flex-1 px-8 pb-20 pt-10">{children}</main>
        <footer className="border-t border-line">
          <p className="mx-auto max-w-[1200px] px-8 py-5 text-xs text-subtle">
            O app aplica regras e explica o resultado. Não é recomendação de investimento; a decisão é sua.
          </p>
        </footer>
      </body>
    </html>
  );
}
