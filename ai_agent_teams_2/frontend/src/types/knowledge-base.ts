export type KBScope = "personal" | "organization" | "app";

export interface KnowledgeBase {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  scope: KBScope;
  created_by_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface KnowledgeBaseList {
  items: KnowledgeBase[];
  total: number;
}

export interface CreateKnowledgeBaseInput {
  name: string;
  description?: string;
  scope: KBScope;
}
