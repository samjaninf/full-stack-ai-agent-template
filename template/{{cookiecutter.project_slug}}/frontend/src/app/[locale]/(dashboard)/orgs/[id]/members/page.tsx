"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, MailPlus, UserPlus, Users } from "lucide-react";

import { InviteMemberDialog, MembersTable } from "@/components/teams";
import { EmptyState, LoadingState } from "@/components/states";
import { useAuth, useInvitations, useMembers } from "@/hooks";
import { cn } from "@/lib/utils";
import type { OrgRole } from "@/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

const ROLE_TONE: Record<string, string> = {
  owner: "bg-brand/15 text-foreground",
  admin: "border-foreground/15 text-foreground/70 border",
  member: "border-foreground/10 text-foreground/55 border",
  viewer: "border-foreground/10 text-foreground/55 border",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function OrgMembersPage({ params }: PageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { user } = useAuth();
  const { members, total, isLoading, fetchMembers, changeRole, removeMember } = useMembers(id);
  const { invitations, fetchInvitations, revokeInvitation } = useInvitations(id);
  const [inviteOpen, setInviteOpen] = useState(false);

  useEffect(() => {
    fetchMembers();
    fetchInvitations();
  }, [fetchMembers, fetchInvitations]);

  const currentMember = members.find((m) => m.user_id === user?.id);
  const canManage = currentMember?.role === "owner" || currentMember?.role === "admin";
  const pendingInvitations = invitations.filter((i) => i.status === "pending");

  return (
    <div className="mx-auto w-full max-w-5xl space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <button
            type="button"
            onClick={() => router.push("/orgs")}
            className="text-foreground/55 hover:text-foreground inline-flex items-center gap-1.5 text-xs font-medium transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to organizations
          </button>
          <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
            Members
          </p>
          <h1 className="font-display text-foreground text-3xl font-bold tracking-tight sm:text-4xl">
            People in this workspace
          </h1>
          <p className="text-foreground/65 max-w-xl text-sm">
            {total} {total === 1 ? "person has" : "people have"} access. Owners and admins can
            invite teammates and adjust roles.
          </p>
        </div>
        {canManage && (
          <button
            type="button"
            onClick={() => setInviteOpen(true)}
            className="bg-foreground text-background hover:bg-foreground/90 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors"
          >
            <UserPlus className="h-4 w-4" />
            Invite teammate
          </button>
        )}
      </header>

      {isLoading ? (
        <LoadingState variant="skeleton-list" rows={3} />
      ) : members.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No members yet"
          description="Invite teammates by email to give them access to this workspace."
          cta={
            canManage
              ? { label: "Invite teammate", onClick: () => setInviteOpen(true) }
              : undefined
          }
        />
      ) : (
        <div className="border-border bg-card overflow-hidden rounded-2xl border">
          <MembersTable
            members={members}
            currentUserId={user?.id ?? ""}
            canManage={canManage}
            onRoleChange={(userId, role: OrgRole) => changeRole(userId, role)}
            onRemove={removeMember}
          />
        </div>
      )}

      {pendingInvitations.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-end justify-between gap-2">
            <div>
              <p className="text-foreground/55 font-mono text-[11px] tracking-wider uppercase">
                Pending invitations
              </p>
              <h2 className="font-display text-foreground text-xl font-semibold tracking-tight">
                {pendingInvitations.length} waiting on a response
              </h2>
            </div>
          </div>
          <ul className="space-y-2">
            {pendingInvitations.map((inv) => (
              <li
                key={inv.id}
                className="border-border bg-card flex flex-wrap items-center gap-3 rounded-2xl border p-4 sm:p-5"
              >
                <div className="bg-brand/15 text-foreground flex h-10 w-10 shrink-0 items-center justify-center rounded-full">
                  <MailPlus className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-foreground truncate text-sm font-semibold">{inv.email}</p>
                  <p className="text-foreground/55 mt-0.5 text-xs">
                    Invited {formatDate(inv.created_at)}
                    {inv.expires_at && <> · expires {formatDate(inv.expires_at)}</>}
                  </p>
                </div>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase",
                    ROLE_TONE[inv.role] ?? ROLE_TONE.member,
                  )}
                >
                  {inv.role}
                </span>
                {canManage && (
                  <button
                    type="button"
                    onClick={() => revokeInvitation(inv.token)}
                    className="text-foreground/55 hover:text-destructive text-xs font-medium transition-colors"
                  >
                    Revoke
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <InviteMemberDialog open={inviteOpen} onOpenChange={setInviteOpen} orgId={id} />
    </div>
  );
}
