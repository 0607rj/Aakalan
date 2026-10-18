import type { Metadata } from "next";
import { Archivo, Public_Sans } from "next/font/google";

import "./globals.css";

// Heavy Archivo for headlines (the "label on a measuring tape" voice); Public Sans for
// everything people read and fill in.
const display = Archivo({
  subsets: ["latin"],
  variable: "--font-archivo",
  display: "swap",
});
const body = Public_Sans({
  subsets: ["latin"],
  variable: "--font-public-sans",
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
      className={`${display.variable} ${body.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
