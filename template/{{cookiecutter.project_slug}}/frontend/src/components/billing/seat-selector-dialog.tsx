{%- if cookiecutter.enable_billing and cookiecutter.enable_teams %}
"use client";
{% raw %}
import { useState } from "react";
import { Minus, Plus, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useBilling, usePlans } from "@/hooks";

interface SeatSelectorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /**
   * "checkout" (default) — starts a Stripe checkout session.
   * "update" — calls onUpdate(seats) to patch the existing subscription.
   */
  mode?: "checkout" | "update";
  initialSeats?: number;
  onUpdate?: (seats: number) => Promise<void>;
}

export function SeatSelectorDialog({
  open,
  onOpenChange,
  mode = "checkout",
  initialSeats = 5,
  onUpdate,
}: SeatSelectorDialogProps) {
  const { plans, isLoading: plansLoading } = usePlans();
  const { startCheckout, isLoading: checkoutLoading } = useBilling();
  const [seats, setSeats] = useState(initialSeats);
  const [isUpdating, setIsUpdating] = useState(false);

  const change = (delta: number) => setSeats((s) => Math.max(1, s + delta));

  const activePlan = plans.find((p) => p.prices.some((pr) => pr.is_active));
  const price = activePlan?.prices.find((pr) => pr.is_active && pr.interval === "month");
  const perSeat = price ? price.unit_amount / 100 : null;

  const fmt = (amount: number) =>
    amount.toLocaleString("en-US", {
      style: "currency",
      currency: price?.currency.toUpperCase() ?? "USD",
      minimumFractionDigits: 0,
    });

  const handleConfirm = async () => {
    if (mode === "update" && onUpdate) {
      setIsUpdating(true);
      await onUpdate(seats);
      setIsUpdating(false);
      onOpenChange(false);
      return;
    }
    await startCheckout({
      seats,
      price_id: price?.id,
      success_url: `${window.location.origin}/billing?success=1`,
      cancel_url: window.location.href,
    });
  };

  const busy = checkoutLoading || isUpdating;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>
            {mode === "update" ? "Change seat count" : "Choose your seats"}
          </DialogTitle>
          <DialogDescription>
            {mode === "update"
              ? "Adjust the number of seats on your current subscription."
              : "Each seat lets one team member access the workspace."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          <div className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-2 text-sm font-medium">
              <Users className="h-4 w-4 text-muted-foreground" />
              Seats
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => change(-1)}
                disabled={seats <= 1}
              >
                <Minus className="h-3.5 w-3.5" />
              </Button>
              <span className="w-8 text-center text-lg font-bold tabular-nums">{seats}</span>
              <Button
                variant="outline"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => change(1)}
              >
                <Plus className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {!plansLoading && perSeat !== null && (
            <div className="rounded-lg bg-muted/50 p-4 text-sm">
              <div className="flex justify-between text-muted-foreground">
                <span>Per seat / month</span>
                <span>{fmt(perSeat)}</span>
              </div>
              <div className="mt-2 flex justify-between border-t pt-2">
                <span className="font-semibold">Total / month</span>
                <span className="text-lg font-bold">{fmt(perSeat * seats)}</span>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={busy}>
            {busy
              ? "Please wait…"
              : mode === "update"
              ? "Save changes"
              : "Continue to checkout"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
{% endraw %}
{%- else %}
export {};
{%- endif %}
