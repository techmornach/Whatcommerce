import Link from "next/link";
import { resolveLandingWhatsAppE164, whatsappChatUrl } from "@/lib/whatsapp";

const plans = [
  {
    name: "Lite",
    price: "₦5,000",
    cadence: "per month",
    products: 50,
    users: 2,
  },
  {
    name: "Standard",
    price: "₦10,000",
    cadence: "per month",
    products: 100,
    users: 3,
    featured: true,
  },
  {
    name: "Premium",
    price: "₦20,000",
    cadence: "per month",
    products: 500,
    users: 5,
  },
];

export default async function Home() {
  const wa = await resolveLandingWhatsAppE164();
  const getStartedHref = wa ? whatsappChatUrl(wa) : null;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <header className="border-b border-zinc-800/80">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
          <span className="text-lg font-semibold tracking-tight">Whatcommerce</span>
          {getStartedHref ? (
            <Link
              href={getStartedHref}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-full bg-emerald-500 px-4 py-2 text-sm font-medium text-emerald-950 transition hover:bg-emerald-400"
            >
              Get started
            </Link>
          ) : (
            <span className="text-xs text-zinc-500">
              Connect the whatcommerce platform worker (QR login); the public link uses that session number only.
            </span>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-16 sm:py-24">
        <p className="text-sm font-medium uppercase tracking-widest text-emerald-400/90">
          WhatsApp-first commerce
        </p>
        <h1 className="mt-4 max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl">
          Run your store from the chat your customers already use.
        </h1>
        <p className="mt-6 max-w-xl text-lg leading-relaxed text-zinc-400">
          Onboard through our bot, pay with Paystack, connect a dedicated store manager on WhatsApp,
          then manage products and orders without leaving the thread.
        </p>

        <div className="mt-12 flex flex-wrap gap-4">
          {getStartedHref ? (
            <Link
              href={getStartedHref}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center rounded-full bg-emerald-500 px-8 py-3 text-base font-semibold text-emerald-950 shadow-lg shadow-emerald-900/30 transition hover:bg-emerald-400"
            >
              Get started on WhatsApp
            </Link>
          ) : (
            <span className="inline-flex cursor-not-allowed items-center justify-center rounded-full bg-zinc-800 px-8 py-3 text-base font-medium text-zinc-500">
              Configure WhatsApp number
            </span>
          )}
        </div>

        <section className="mt-24">
          <h2 className="text-2xl font-semibold tracking-tight">Plans</h2>
          <p className="mt-2 text-zinc-400">No free tier — pick the capacity that fits your shop.</p>
          <div className="mt-10 grid gap-6 sm:grid-cols-3">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`flex flex-col rounded-2xl border p-6 ${
                  plan.featured
                    ? "border-emerald-500/50 bg-emerald-950/20 shadow-lg shadow-emerald-900/10"
                    : "border-zinc-800 bg-zinc-900/40"
                }`}
              >
                <h3 className="text-lg font-semibold">{plan.name}</h3>
                <p className="mt-4 text-3xl font-bold tracking-tight">{plan.price}</p>
                <p className="text-sm text-zinc-500">{plan.cadence}</p>
                <ul className="mt-6 space-y-2 text-sm text-zinc-400">
                  <li>{plan.products} products</li>
                  <li>{plan.users} users</li>
                </ul>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-zinc-800/80 py-10 text-center text-sm text-zinc-600">
        <span>Whatcommerce — MVP scaffold (FastAPI + Postgres + Next.js)</span>
        {" · "}
        <Link href="/admin" className="text-zinc-500 underline-offset-2 hover:text-zinc-400 hover:underline">
          Admin
        </Link>
      </footer>
    </div>
  );
}
