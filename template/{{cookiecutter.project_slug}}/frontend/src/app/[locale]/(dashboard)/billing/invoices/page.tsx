{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"use client";
{% raw %}
import { InvoicesPanel } from "@/components/billing";

export default function InvoicesPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold">Invoices</h1>
        <p className="text-sm text-muted-foreground">Your billing history and downloadable invoices.</p>
      </div>
      <InvoicesPanel />
    </div>
  );
}
{% endraw %}
{%- else %}
export default function InvoicesPage() {
  return null;
}
{%- endif %}
