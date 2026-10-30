import type { Metadata } from "next";
import {
  Google_Sans_Flex,
  IBM_Plex_Mono,
  Stack_Sans_Headline,
} from "next/font/google";

import { RevealOnScroll } from "@/components/site/reveal";

import "./globals.css";

// Google Sans Flex for everything people read and fill in, Stack Sans Headline for headings,
// IBM Plex Mono for figures (the theme in globals.css points the font tokens at them).
const body = Google_Sans_Flex({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});
const head = Stack_Sans_Headline({
  subsets: ["latin"],
  variable: "--font-headline",
  display: "swap",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
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
      className={`${body.variable} ${head.variable} ${plexMono.variable} h-full antialiased`}
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
      <body className="flex min-h-full flex-col">
        {children}
        {/* every page, so a [data-reveal] part never stays hidden in the app */}
        <RevealOnScroll />
      </body>
    </html>
  );
}
