"use client";

import { PaymentMethodsPanel } from "@/components/billing";

export default function PaymentMethodsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold">Payment Methods</h1>
        <p className="text-muted-foreground text-sm">
          Manage your payment methods via the Stripe billing portal.
        </p>
      </div>
      <PaymentMethodsPanel />
    </div>
  );
}
