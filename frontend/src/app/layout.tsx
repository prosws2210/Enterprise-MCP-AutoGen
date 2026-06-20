import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "AI-POS | Digital Chief of Staff",
  description: "Enterprise-grade Agentic AI platform powered by AutoGen & MCP",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${inter.variable} antialiased h-full`}>
      <body className="min-h-full flex flex-col bg-black text-white selection:bg-cyan-500/30 overflow-x-hidden font-sans">
        {children}
      </body>
    </html>
  );
}
