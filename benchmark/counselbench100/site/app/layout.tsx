import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(
    "https://counselbench-100.samuelchien821.chatgpt.site",
  ),
  title: {
    default: "CounselBench-100",
    template: "%s · CounselBench-100",
  },
  description:
    "An open long-horizon benchmark for legal agents: 100 matters, 9,600 documents, 109 verified MCP calls per task.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
  openGraph: {
    title: "CounselBench-100",
    description:
      "Long-horizon legal work, measured end to end across 100 realistic matters.",
    type: "website",
    images: [{ url: "/og.png", width: 1200, height: 630 }],
  },
  twitter: {
    card: "summary_large_image",
    title: "CounselBench-100",
    description: "100 matters · 9,600 documents · 109 verified MCP calls",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
