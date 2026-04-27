"use client";

import { fetchPublicConfig } from "@/lib/api";
import type { PublicConfig } from "@/lib/api";
import { useEffect, useState } from "react";

const FALLBACK: PublicConfig = {
  whatsapp_e164: "",
  whatsapp_href: "",
  message_prefill: "Hi! I'd like to get started with Whatcommerce.",
  bot_connected: false,
  link_state: "unlinked",
};

export default function Home() {
  const [config, setConfig] = useState<PublicConfig>(FALLBACK);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      const next = await fetchPublicConfig();
      if (cancelled) return;
      if (next) setConfig(next);
      setLoaded(true);
    };

    void load();
    const t = window.setInterval(() => {
      void load();
    }, 30_000);

    return () => {
      cancelled = true;
      window.clearInterval(t);
    };
  }, []);

  const ready = config.bot_connected && (config.whatsapp_href || "").length > 0;

  return (
    <div className="min-h-screen bg-[#f4f7fb] text-slate-900">
      <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex items-center justify-between rounded-2xl border border-slate-200/70 bg-white px-5 py-3 shadow-sm">
          <div className="text-2xl font-semibold tracking-tight text-[#0f4b45]">
            WhatCommerce
          </div>
          <nav className="hidden items-center gap-8 text-sm text-slate-600 md:flex">
            <a href="#features" className="hover:text-slate-900">
              Features
            </a>
            <a href="#pricing" className="hover:text-slate-900">
              Pricing
            </a>
          </nav>
        </header>

        <main className="mt-4 overflow-hidden rounded-3xl border border-slate-200/70 bg-gradient-to-b from-[#f8fbff] to-[#eef2f8] px-6 pb-10 pt-8 shadow-sm sm:px-10 md:pt-12 lg:px-14">
          <section className="grid items-center gap-10 lg:grid-cols-2">
            <div>
              <p className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                NEW: Conversational ERP v2.0
              </p>
              <h1 className="mt-4 text-4xl font-semibold leading-tight text-[#0f4b45] md:text-6xl">
                Manage Your Entire Store from WhatsApp
              </h1>
              <p className="mt-5 max-w-xl text-lg leading-relaxed text-slate-600">
                The first ERP built for the chat era. Sync inventory, process orders, and
                manage customers without ever leaving the WhatsApp interface.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                {ready ? (
                  <a
                    href={config.whatsapp_href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center rounded-xl bg-[#0f4b45] px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#0b3f3b]"
                  >
                    Get Started
                  </a>
                ) : (
                  <span className="inline-flex items-center rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm text-slate-500">
                    {loaded ? "WhatsApp link unavailable" : "Checking WhatsApp link..."}
                  </span>
                )}
              </div>
            </div>

            <div className="mx-auto w-full max-w-md rounded-[2.6rem] border-[6px] border-[#101533] bg-[#f7f8fb] p-3 shadow-2xl shadow-slate-300/60">
              <div className="overflow-hidden rounded-[2.1rem] border border-slate-300 bg-[#d7d2cb]">
                <div className="flex items-center justify-between bg-[#0f7867] px-4 py-3 text-white">
                  <div className="text-sm font-semibold">Store Manager</div>
                  <div className="text-xs">Online</div>
                </div>
                <div className="space-y-3 p-4">
                  <div className="max-w-[85%] rounded-xl bg-white px-3 py-2 text-sm text-slate-700">
                    Hello! How can I help with your store today?
                  </div>
                  <div className="ml-auto max-w-[75%] rounded-xl bg-[#d4f9c9] px-3 py-2 text-sm text-slate-700">
                    inventory check product-id-402
                  </div>
                  <div className="max-w-[88%] rounded-xl border-l-4 border-[#0f7867] bg-white px-3 py-2 text-sm text-slate-700">
                    <p className="font-semibold">Inventory Alert</p>
                    <p>Wireless Earbuds Pro*</p>
                    <p>Current Stock: 12 units</p>
                    <p>Status: Low Stock</p>
                  </div>
                </div>
                <div className="border-t border-slate-300 bg-[#efefef] px-4 py-2 text-xs text-slate-500">
                  Type /command to manage...
                </div>
              </div>
            </div>
          </section>

          <section id="features" className="mt-10 grid gap-3 md:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Orders</p>
              <p className="mt-1 text-sm text-slate-700">
                Track every order from WhatsApp without spreadsheets.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Inventory</p>
              <p className="mt-1 text-sm text-slate-700">
                Update stock in seconds and receive low-stock alerts.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Customers</p>
              <p className="mt-1 text-sm text-slate-700">
                Keep customer history and responses organized in one thread.
              </p>
            </div>
          </section>

          <section id="pricing" className="mt-8">
            <h2 className="text-2xl font-semibold text-[#0f4b45]">Pricing</h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              Simple subscription pricing. Start from WhatsApp and choose the plan that fits
              your business size.
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-sm font-semibold text-slate-900">Starter</p>
                <p className="mt-2 text-2xl font-semibold text-[#0f4b45]">₦5,000/mo</p>
                <p className="mt-2 text-sm text-slate-600">
                  For new businesses managing early daily orders.
                </p>
              </div>
              <div className="rounded-2xl border border-[#0f4b45]/30 bg-white p-4 shadow-sm">
                <p className="text-sm font-semibold text-slate-900">Growth</p>
                <p className="mt-2 text-2xl font-semibold text-[#0f4b45]">₦10,000/mo</p>
                <p className="mt-2 text-sm text-slate-600">
                  Best for growing teams handling more products and customers.
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-sm font-semibold text-slate-900">Scale</p>
                <p className="mt-2 text-2xl font-semibold text-[#0f4b45]">₦20,000/mo</p>
                <p className="mt-2 text-sm text-slate-600">
                  For larger stores with high-volume operations.
                </p>
              </div>
            </div>
          </section>
        </main>

        <footer className="px-2 pb-3 pt-6 text-center text-xs text-slate-500">
          Powered by Whatcommerce • Billing via Paystack • Built for growing businesses
        </footer>
      </div>
    </div>
  );
}
