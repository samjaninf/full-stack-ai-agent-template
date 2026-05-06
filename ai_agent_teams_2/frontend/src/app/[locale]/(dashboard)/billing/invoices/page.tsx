"use client";

import { InvoicesPanel } from "@/components/billing";

export default function InvoicesPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold">Invoices</h1>
        <p className="text-muted-foreground text-sm">
          Your billing history and downloadable invoices.
        </p>
      </div>
      <InvoicesPanel />
    </div>
  );
}
