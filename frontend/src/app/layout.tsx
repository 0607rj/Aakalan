import type { Metadata } from "next";
import { Geist_Mono, Inter, Instrument_Serif } from "next/font/google";

import "./globals.css";

// Inter for everything people read and fill in; Instrument Serif for the few big statements;
// Geist Mono for small labels and figures.
const body = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});
const serif = Instrument_Serif({
  subsets: ["latin"],
  weight: "400",
  style: ["normal", "italic"],
  variable: "--font-instrument-serif",
  display: "swap",
});
const mono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Aakalan · What should this software cost?",
  description:
    "Describe the software or upload its requirement document and get a low, likely and high cost for every feature, priced for how software is built with AI today.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`dark ${body.variable} ${serif.variable} ${mono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        {/* hide [data-reveal] parts before the first paint; only when scripts run */}
        <script
          dangerouslySetInnerHTML={{
            __html: "document.documentElement.classList.add('rv')",
          }}
        />
      </head>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
