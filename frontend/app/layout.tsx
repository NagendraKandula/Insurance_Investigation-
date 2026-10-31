import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "Fraud Investigation Portal",
  description: "Review suspicious claimants, providers and payment networks.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100">
        <Suspense fallback={<div className="h-14 border-b border-slate-200 dark:border-slate-800" />}>
          <Nav />
        </Suspense>
        <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6">{children}</main>
      </body>
    </html>
  );
}
