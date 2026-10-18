import type { Metadata } from "next";

import { SettingsForm } from "./settings-form";

// Auth is client-side (token in localStorage), so there is no server-rendered shell to
// validate for instant navigation.
export const instant = false;

export const metadata: Metadata = {
  title: "Settings · Aakalan",
};

export default function SettingsPage() {
  return <SettingsForm />;
}
