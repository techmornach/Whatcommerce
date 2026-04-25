"use client";

type Props = {
  open: boolean;
  title: string;
  description: React.ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** danger = red-styled primary action */
  tone?: "danger" | "neutral";
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
};

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "neutral",
  busy = false,
  onConfirm,
  onClose,
}: Props) {
  if (!open) return null;

  const confirmClass =
    tone === "danger"
      ? "rounded-md bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-500 disabled:opacity-50"
      : "rounded-md bg-zinc-100 px-3 py-2 text-sm font-medium text-zinc-950 hover:bg-white disabled:opacity-50";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <button
        type="button"
        className="absolute inset-0 bg-black/70"
        aria-label="Close dialog"
        onClick={() => {
          if (!busy) onClose();
        }}
      />
      <div className="relative z-10 w-full max-w-md rounded-lg border border-zinc-800 bg-zinc-950 p-5 shadow-xl">
        <h2 className="text-lg font-semibold text-zinc-100">{title}</h2>
        <div className="mt-3 text-sm leading-relaxed text-zinc-400">{description}</div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            className="rounded-md border border-zinc-700 px-3 py-2 text-sm text-zinc-300 hover:bg-zinc-900 disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button type="button" disabled={busy} onClick={onConfirm} className={confirmClass}>
            {busy ? "Please wait…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
