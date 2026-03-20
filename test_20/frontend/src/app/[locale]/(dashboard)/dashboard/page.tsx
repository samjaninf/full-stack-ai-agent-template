"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent, Badge, Avatar, AvatarFallback, Skeleton } from "@/components/ui";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/hooks";
import { ROUTES, BACKEND_URL } from "@/lib/constants";
import type { HealthResponse, Conversation, ConversationListResponse } from "@/types";
import {
  CheckCircle, XCircle, Loader2, User, ArrowRight, MessageSquare,
  Database, Activity, ExternalLink, BookOpen, Upload, Zap,
} from "lucide-react";
import { listCollections, getCollectionInfo, type RAGCollectionInfo } from "@/lib/rag-api";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [healthError, setHealthError] = useState(false);
  const [ragStats, setRagStats] = useState<{
    collections: RAGCollectionInfo[];
    totalVectors: number;
  } | null>(null);
  const [recentConversations, setRecentConversations] = useState<Conversation[]>([]);
  const [conversationsLoading, setConversationsLoading] = useState(true);

  useEffect(() => {
    apiClient.get<HealthResponse>("/health")
      .then(data => { setHealth(data); setHealthError(false); })
      .catch(() => setHealthError(true))
      .finally(() => setHealthLoading(false));

    listCollections().then(async data => {
      const infos: RAGCollectionInfo[] = [];
      let totalVectors = 0;
      for (const name of data.items) {
        try { const info = await getCollectionInfo(name); infos.push(info); totalVectors += info.total_vectors; } catch {}
      }
      setRagStats({ collections: infos, totalVectors });
    }).catch(() => setRagStats({ collections: [], totalVectors: 0 }));

    apiClient.get<ConversationListResponse>("/conversations?limit=5")
      .then(data => setRecentConversations(data.items || []))
      .catch(() => {})
      .finally(() => setConversationsLoading(false));
  }, []);

  const displayName = user?.name || user?.email?.split("@")[0] || "";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">
          {getGreeting()}{displayName ? `, ${displayName}` : ""}
        </h1>
        <p className="text-muted-foreground text-sm">
          Here&apos;s an overview of your project.
        </p>
      </div>

      {/* Stats row */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* API Status */}
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground text-xs font-medium">API</span>
            {healthLoading ? <Loader2 className="text-muted-foreground h-3.5 w-3.5 animate-spin" />
              : healthError ? <XCircle className="text-destructive h-3.5 w-3.5" />
              : <CheckCircle className="h-3.5 w-3.5 text-green-500" />}
          </div>
          <p className="mt-1 text-xl font-bold">
            {healthLoading ? "..." : healthError ? "Offline" : "Online"}
          </p>
          {health?.version && <p className="text-muted-foreground text-[10px]">v{health.version}</p>}
        </Card>

        {/* Conversations */}
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground text-xs font-medium">Conversations</span>
            <MessageSquare className="text-muted-foreground h-3.5 w-3.5" />
          </div>
          <p className="mt-1 text-xl font-bold">
            {conversationsLoading ? "..." : recentConversations.length}
          </p>
          <p className="text-muted-foreground text-[10px]">recent chats</p>
        </Card>

        {/* Knowledge Base */}
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground text-xs font-medium">Knowledge Base</span>
            <Database className="text-muted-foreground h-3.5 w-3.5" />
          </div>
          <p className="mt-1 text-xl font-bold">
            {ragStats?.totalVectors?.toLocaleString() ?? "..."}
          </p>
          <p className="text-muted-foreground text-[10px]">
            vectors in {ragStats?.collections?.length ?? 0} collection{ragStats && ragStats.collections.length !== 1 ? "s" : ""}
          </p>
        </Card>

        {/* AI Agent */}
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground text-xs font-medium">AI Agent</span>
            <Activity className="text-muted-foreground h-3.5 w-3.5" />
          </div>
          <p className="mt-1 text-xl font-bold">pydantic_ai</p>
          <p className="text-muted-foreground text-[10px]">openrouter</p>
        </Card>
      </div>

      {/* Main grid */}
      <div className="grid gap-6 lg:grid-cols-5">
        {/* Left — 3/5 */}
        <div className="space-y-6 lg:col-span-3">
          {/* Recent Conversations */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-sm font-semibold">Recent Conversations</CardTitle>
              <Link href={ROUTES.CHAT} className="text-brand hover:text-brand-hover text-xs font-medium">
                View all
              </Link>
            </CardHeader>
            <CardContent>
              {conversationsLoading ? (
                <div className="space-y-2 py-2">
                  {[1,2,3].map(i => <Skeleton key={i} className="h-9 w-full rounded-md" />)}
                </div>
              ) : recentConversations.length === 0 ? (
                <div className="py-6 text-center">
                  <MessageSquare className="text-muted-foreground mx-auto mb-2 h-6 w-6" />
                  <p className="text-muted-foreground text-sm">No conversations yet</p>
                  <Link href={ROUTES.CHAT} className="text-brand hover:text-brand-hover mt-1 inline-flex items-center gap-1 text-xs font-medium">
                    Start chatting <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              ) : (
                <div className="space-y-0.5">
                  {recentConversations.map(conv => (
                    <Link key={conv.id} href={ROUTES.CHAT}
                      className="hover:bg-muted/50 flex items-center justify-between rounded-md px-3 py-2 transition-colors">
                      <div className="flex items-center gap-2.5 overflow-hidden">
                        <MessageSquare className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
                        <span className="truncate text-sm">{conv.title || "New conversation"}</span>
                      </div>
                      <span className="text-muted-foreground shrink-0 text-[10px]">
                        {timeAgo(conv.updated_at || conv.created_at)}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Collections */}
          {ragStats && ragStats.collections.length > 0 && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="text-sm font-semibold">Collections</CardTitle>
                <Link href={ROUTES.RAG} className="text-brand hover:text-brand-hover text-xs font-medium">
                  Manage
                </Link>
              </CardHeader>
              <CardContent>
                <div className="space-y-1.5">
                  {ragStats.collections.map(col => (
                    <Link key={col.name} href={ROUTES.RAG}
                      className="hover:bg-muted/50 flex items-center justify-between rounded-md border px-3 py-2.5 transition-colors">
                      <div className="flex items-center gap-2.5">
                        <Database className="text-muted-foreground h-3.5 w-3.5" />
                        <div>
                          <p className="text-sm font-medium">{col.name}</p>
                          <p className="text-muted-foreground text-[10px]">{col.total_vectors.toLocaleString()} vectors</p>
                        </div>
                      </div>
                      <Badge variant="secondary" className="text-[10px]">{col.indexing_status}</Badge>
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right — 2/5 */}
        <div className="space-y-6 lg:col-span-2">
          {/* Quick Actions */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-2">
              <Link href={ROUTES.CHAT}
                className="hover:bg-muted/50 flex flex-col items-center gap-2 rounded-lg border p-4 text-center transition-colors">
                <MessageSquare className="text-brand h-5 w-5" />
                <span className="text-xs font-medium">New Chat</span>
              </Link>
              <Link href={ROUTES.RAG}
                className="hover:bg-muted/50 flex flex-col items-center gap-2 rounded-lg border p-4 text-center transition-colors">
                <Upload className="text-brand h-5 w-5" />
                <span className="text-xs font-medium">Upload Docs</span>
              </Link>
              <a href={`${BACKEND_URL}/docs`} target="_blank" rel="noopener noreferrer"
                className="hover:bg-muted/50 flex flex-col items-center gap-2 rounded-lg border p-4 text-center transition-colors">
                <BookOpen className="text-brand h-5 w-5" />
                <span className="text-xs font-medium">API Docs</span>
              </a>
              <Link href={ROUTES.PROFILE}
                className="hover:bg-muted/50 flex flex-col items-center gap-2 rounded-lg border p-4 text-center transition-colors">
                <User className="text-brand h-5 w-5" />
                <span className="text-xs font-medium">Profile</span>
              </Link>
            </CardContent>
          </Card>

          {/* Environment */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Environment</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-xs">Status</span>
                  {healthLoading ? <span className="text-xs">...</span>
                    : healthError ? <span className="text-destructive text-xs font-medium">Offline</span>
                    : <span className="text-xs font-medium text-green-500">Online</span>}
                </div>
                {health?.version && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground text-xs">Version</span>
                    <span className="font-mono text-[10px]">{health.version}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-xs">Framework</span>
                  <span className="text-xs font-medium">PydanticAI</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-xs">LLM</span>
                  <span className="text-xs font-medium">OpenRouter</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-xs">Vector Store</span>
                  <span className="text-xs font-medium">Milvus</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-xs">Account</span>
                  <span className="truncate text-xs font-medium ml-4">{user?.email}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Account */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Account</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <Avatar className="h-10 w-10">
                  <AvatarFallback className="bg-brand/10 text-brand text-sm font-semibold">
                    {user?.email?.substring(0, 2).toUpperCase() || "U"}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{user?.email}</p>
                  <p className="text-muted-foreground text-[10px]">
                    {user?.is_superuser ? "Admin" : "User"}
                    {user?.created_at && ` · Since ${new Date(user.created_at).toLocaleDateString()}`}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
