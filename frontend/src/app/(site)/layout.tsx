import { Footer } from "@/components/site/footer";
import { SiteNavBar } from "@/components/site/navbar";

/** Public pages: home, features, how it works, about, contact and sign in. */
export default function SiteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <SiteNavBar />
      <div className="flex flex-1 flex-col leading-[1.55]">{children}</div>
      <Footer />
    </>
  );
}
