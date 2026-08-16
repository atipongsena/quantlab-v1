import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "QuantLab - Quantitative Research & Execution Platform",
  description: "Point-in-time cross-sectional alpha research, walk-forward ML, and paper trading operations.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-slate-950 text-slate-100">
        {children}
      </body>
    </html>
  );
}
