/** E.164 without leading +, e.g. 2348012345678 */
export function whatsappChatUrl(e164: string): string {
  const digits = e164.replace(/\D/g, "");
  return `https://wa.me/${digits}`;
}

type PublicConfig = {
  whatcommerce_session_phone_e164?: string | null;
};

/**
 * Server component: "Get started" wa.me target — only the number reported by the
 * whatcommerce platform worker after WhatsApp session is ready (no env/admin fallbacks).
 */
export async function resolveLandingWhatsAppE164(): Promise<string | undefined> {
  const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
  if (!base) return undefined;
  try {
    const res = await fetch(`${base}/v1/public/config`, { next: { revalidate: 30 } });
    if (!res.ok) return undefined;
    const data = (await res.json()) as PublicConfig;
    const session = data.whatcommerce_session_phone_e164?.trim();
    if (session && session.length > 0) return session;
    return undefined;
  } catch {
    return undefined;
  }
}
