import {
  BellIcon,
  CalendarCheckIcon,
  ChartBarIcon,
  ChatCircleDotsIcon,
  CreditCardIcon,
  DeviceMobileIcon,
  FileTextIcon,
  HardDrivesIcon,
  HeadsetIcon,
  IdentificationCardIcon,
  SignInIcon,
  TicketIcon,
} from "@phosphor-icons/react/dist/ssr";

import { cn } from "@/lib/utils";

import type { IconType } from "./illustrations";

/** Two rows of features the catalog prices, sliding past each other. */
const ROWS: { icon: IconType; name: string }[][] = [
  [
    { icon: SignInIcon, name: "Sign-in" },
    { icon: CalendarCheckIcon, name: "Bookings" },
    { icon: CreditCardIcon, name: "Payments" },
    { icon: ChatCircleDotsIcon, name: "Chatbot" },
    { icon: DeviceMobileIcon, name: "Mobile app" },
    { icon: HardDrivesIcon, name: "Hosting" },
  ],
  [
    { icon: HeadsetIcon, name: "Support" },
    { icon: IdentificationCardIcon, name: "Aadhaar eKYC" },
    { icon: FileTextIcon, name: "DigiLocker" },
    { icon: BellIcon, name: "SMS alerts" },
    { icon: ChartBarIcon, name: "Dashboards" },
    { icon: TicketIcon, name: "Grievance tickets" },
  ],
];

/** The round icon's colours, in turn: orange, ink, green, blue. */
const DOTS = ["bg-tape-bright", "bg-foreground", "bg-ai", "bg-[#1f6feb]"];

/**
 * A product window in the middle with features sliding past behind it in two rows, faded at
 * both ends. The rows are decoration (the window says the same in words), so screen readers
 * skip them; with reduced motion they stand still.
 */
export function FeatureTiles({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative mt-16">
      <div className="relative z-10 mx-auto w-[min(380px,86vw)] sm:absolute sm:top-0 sm:left-1/2 sm:-translate-x-1/2">
        {children}
      </div>
      <div
        aria-hidden="true"
        className="tile-rows -mt-10 flex flex-col gap-5 overflow-hidden py-16 sm:mt-0 sm:py-[120px]"
      >
        {ROWS.map((row, r) => (
          <div
            key={r}
            className={cn("tile-row flex w-max gap-5", r === 1 && "rev")}
          >
            {/* four copies: the row slides half its width, so it loops without a gap */}
            {[0, 1, 2, 3].map((copy) =>
              row.map((t, i) => (
                <div
                  key={`${copy}-${t.name}`}
                  className="soft-card flex size-40 shrink-0 flex-col items-center justify-center gap-3.5 rounded-[26px] p-3 text-center text-[15px] font-medium"
                >
                  <span
                    className={cn(
                      "flex size-[54px] items-center justify-center rounded-full text-white",
                      DOTS[(i + r * 2) % DOTS.length],
                    )}
                  >
                    <t.icon size={24} />
                  </span>
                  {t.name}
                </div>
              )),
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
