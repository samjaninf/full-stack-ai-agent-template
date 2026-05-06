"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { ChatContainer, ConversationSidebar } from "@/components/chat";
import { useConversationStore } from "@/stores";
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
import { KBPanel } from "@/components/chat";
{%- endif %}

export default function ChatPage() {
  const searchParams = useSearchParams();
  const { setCurrentConversationId } = useConversationStore();

  useEffect(() => {
    const conversationId = searchParams.get("id");
    if (conversationId) {
      setCurrentConversationId(conversationId);
    }
  }, [searchParams, setCurrentConversationId]);

  return (
    <div className="flex min-h-0 flex-1 -m-3 sm:-m-6">
      <ConversationSidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <div className="flex min-h-0 flex-1">
          <div className="flex-1 min-w-0">
            <ChatContainer />
          </div>
{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
          <KBPanel />
{%- endif %}
        </div>
      </div>
    </div>
  );
}
