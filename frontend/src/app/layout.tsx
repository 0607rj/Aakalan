import type { Metadata } from "next";
import {
  Geist_Mono,
  IBM_Plex_Mono,
  IBM_Plex_Sans,
  Inter,
  Instrument_Serif,
} from "next/font/google";

import "./globals.css";

// IBM Plex Sans for everything people read and fill in, Plex Mono for small figures (the
// theme in globals.css points the font tokens at them); the older faces stay loaded for now.
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
const plex = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex",
  display: "swap",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
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
      className={`${body.variable} ${serif.variable} ${mono.variable} ${plex.variable} ${plexMono.variable} h-full antialiased`}
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
