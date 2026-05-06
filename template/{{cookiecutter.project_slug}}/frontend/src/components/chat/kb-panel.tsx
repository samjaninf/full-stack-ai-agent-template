{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
"use client";
{% raw %}
import { useEffect } from "react";
import { Database, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { useKnowledgeBases, useConversations } from "@/hooks";
import { useConversationStore, useKBPanelStore } from "@/stores";
import type { KnowledgeBase } from "@/types";
import { cn } from "@/lib/utils";

const SCOPE_LABELS: Record<string, string> = {
  personal: "Personal",
  organization: "Organization",
  app: "App-wide",
};

export function KBPanel() {
  const { isOpen, close } = useKBPanelStore();
  const { kbs, isLoading, fetchKBs } = useKnowledgeBases();
  const { currentConversationId, conversations } = useConversationStore();
  const { updateActiveKBs } = useConversations();

  useEffect(() => {
    if (isOpen) fetchKBs();
  }, [isOpen, fetchKBs]);

  const conversation = conversations.find((c) => c.id === currentConversationId);
  const activeIds = new Set<string>(conversation?.active_knowledge_base_ids ?? []);

  const handleToggle = async (kb: KnowledgeBase, checked: boolean) => {
    if (!currentConversationId) return;
    const newIds = checked
      ? [...activeIds, kb.id]
      : [...activeIds].filter((id) => id !== kb.id);
    await updateActiveKBs(currentConversationId, newIds);
  };

  const grouped = kbs.reduce<Record<string, KnowledgeBase[]>>((acc, kb) => {
    if (!acc[kb.scope]) acc[kb.scope] = [];
    acc[kb.scope].push(kb);
    return acc;
  }, {});

  const sections = (["personal", "organization", "app"] as const).filter(
    (s) => (grouped[s]?.length ?? 0) > 0
  );

  if (!isOpen) return null;

  return (
    <div className="flex w-64 shrink-0 flex-col border-l bg-background">
      <div className="flex items-center justify-between border-b px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          <Database className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-semibold">Knowledge Bases</span>
        </div>
        <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={close}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-4 p-3">
          {!currentConversationId && (
            <p className="text-xs text-muted-foreground">
              Start a conversation to select which knowledge bases to use.
            </p>
          )}

          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }, (_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : kbs.length === 0 ? (
            <p className="text-xs text-muted-foreground">No knowledge bases available.</p>
          ) : (
            sections.map((scope) => (
              <div key={scope}>
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {SCOPE_LABELS[scope]}
                </p>
                <div className="space-y-0.5">
                  {grouped[scope].map((kb) => {
                    const isActive = activeIds.has(kb.id);
                    return (
                      <label
                        key={kb.id}
                        className={cn(
                          "flex cursor-pointer items-start gap-2.5 rounded px-2 py-1.5 text-sm transition-colors hover:bg-muted/50",
                          !currentConversationId && "cursor-not-allowed opacity-50"
                        )}
                      >
                        <Checkbox
                          checked={isActive}
                          onCheckedChange={(checked) =>
                            handleToggle(kb, checked as boolean)
                          }
                          disabled={!currentConversationId}
                          className="mt-0.5 shrink-0"
                        />
                        <div className="min-w-0">
                          <p className="truncate text-sm leading-tight">{kb.name}</p>
                          {kb.description && (
                            <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                              {kb.description}
                            </p>
                          )}
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </ScrollArea>

      {activeIds.size > 0 && (
        <div className="border-t px-3 py-2">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">{activeIds.size}</span>{" "}
            KB{activeIds.size !== 1 ? "s" : ""} active
          </p>
        </div>
      )}
    </div>
  );
}
{% endraw %}
{%- endif %}
