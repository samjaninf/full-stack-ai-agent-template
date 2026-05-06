{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"use client";
{% raw %}
import { CreditCard, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useBilling, useSubscription } from "@/hooks";

const CARD_BRAND_LABELS: Record<string, string> = {
  visa: "Visa",
  mastercard: "Mastercard",
  amex: "American Express",
  discover: "Discover",
  jcb: "JCB",
  unionpay: "UnionPay",
  diners: "Diners Club",
};

export function PaymentMethodsPanel() {
  const { subscription, isLoading } = useSubscription();
  const { isLoading: billingLoading, openPortal } = useBilling();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Payment Methods</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CreditCard className="h-5 w-5" />
          Payment Methods
        </CardTitle>
        <CardDescription>
          Payment methods are securely managed through Stripe.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {subscription ? (
          <div className="rounded-lg border bg-muted/30 p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-14 items-center justify-center rounded-md border bg-background text-xs font-bold uppercase text-muted-foreground">
                {subscription.price?.currency?.toUpperCase() ?? "···"}
              </div>
              <div>
                <p className="text-sm font-medium">
                  {subscription.status === "active" || subscription.status === "trialing"
                    ? "Active subscription"
                    : "Subscription on file"}
                </p>
                <p className="text-xs text-muted-foreground">
                  Use the billing portal to update your payment method.
                </p>
              </div>
              <Badge variant="secondary" className="ml-auto shrink-0">
                Managed by Stripe
              </Badge>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
            <Shield className="h-5 w-5 shrink-0" />
            <p>No active subscription. Upgrade to add a payment method.</p>
          </div>
        )}
      </CardContent>
      <CardFooter>
        <Button
          variant="outline"
          onClick={openPortal}
          disabled={billingLoading || !subscription}
        >
          {billingLoading ? "Redirecting…" : "Manage Payment Methods"}
        </Button>
      </CardFooter>
    </Card>
  );
}
{% endraw %}
{%- else %}
export {};
{%- endif %}
