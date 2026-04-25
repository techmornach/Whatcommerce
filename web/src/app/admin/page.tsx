"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getAdminToken } from "@/lib/admin-api";

export default function AdminIndexPage() {
  const router = useRouter();
  useEffect(() => {
    if (getAdminToken()) router.replace("/admin/whatcommerce");
    else router.replace("/admin/login");
  }, [router]);
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-500">
      Redirecting…
    </div>
  );
}
