"use client";

import QRCodeSVG from "react-qr-code";

export function WhatsAppQr({ value }: { value: string }) {
  if (!value) return null;
  return (
    <div className="bg-white p-3 rounded-lg inline-block">
      <QRCodeSVG value={value} size={240} level="M" />
    </div>
  );
}
