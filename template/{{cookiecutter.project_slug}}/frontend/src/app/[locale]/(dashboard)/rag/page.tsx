{%- if cookiecutter.enable_rag and cookiecutter.use_frontend %}
"use client";

import { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import { Button, Card, Input, Badge, Skeleton,
  AlertDialog, AlertDialogTrigger, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogAction, AlertDialogCancel,
} from "@/components/ui";
import {
  Database, Search, Trash2, FileText, Plus, Upload, Loader2, FolderOpen,
  CheckCircle, XCircle, ChevronLeft, Download, Eye,
} from "lucide-react";
import {
  listCollections, getCollectionInfo, createCollection, deleteCollection,
  listTrackedDocuments, deleteTrackedDocument, ingestFile, searchDocuments,
  getDocumentDownloadUrl,
  type RAGCollectionInfo, type RAGTrackedDocument, type RAGSearchResult,
} from "@/lib/rag-api";

interface CollectionWithInfo {
  name: string;
  info: RAGCollectionInfo | null;
}

function StatusIcon({ status }: { status: string }) {
  if (status === "done") return <CheckCircle className="h-4 w-4 text-green-500" />;
  if (status === "error") return <XCircle className="h-4 w-4 text-red-500" />;
  return <Loader2 className="h-4 w-4 animate-spin text-brand" />;
}

export default function RAGPage() {
  const [collections, setCollections] = useState<CollectionWithInfo[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [docs, setDocs] = useState<RAGTrackedDocument[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<RAGSearchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [docsLoading, setDocsLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [tab, setTab] = useState<"documents" | "search">("documents");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchCollections = async () => {
    setLoading(true);
    try {
      const data = await listCollections();
      const items: CollectionWithInfo[] = [];
      for (const name of data.items) {
        try { items.push({ name, info: await getCollectionInfo(name) }); }
        catch { items.push({ name, info: null }); }
      }
      setCollections(items);
      if (items.length > 0 && !selected) setSelected(items[0].name);
    } catch { toast.error("Failed to load collections"); }
    finally { setLoading(false); }
  };

  const fetchDocs = async (col: string) => {
    if (!col) { setDocs([]); return; }
    setDocsLoading(true);
    try {
      const data = await listTrackedDocuments(col);
      setDocs(data.items || []);
    } catch { setDocs([]); }
    finally { setDocsLoading(false); }
  };

  useEffect(() => { fetchCollections(); }, []);
  useEffect(() => { if (selected) fetchDocs(selected); }, [selected]);

  const handleCreate = async () => {
    const name = newName.trim().toLowerCase().replace(/\s+/g, "_");
    if (!name) return;
    try {
      await createCollection(name);
      toast.success(`"${name}" created`);
      setNewName(""); setShowCreate(false);
      await fetchCollections();
      setSelected(name);
    } catch { toast.error("Failed to create collection"); }
  };

  const handleDelete = async (name: string) => {
    try {
      await deleteCollection(name);
      toast.success(`"${name}" deleted`);
      setCollections(prev => prev.filter(c => c.name !== name));
      if (selected === name) { setSelected(""); setDocs([]); setSearchResults([]); }
    } catch { toast.error("Failed to delete"); }
  };

  const handleDeleteDoc = async (docId: string) => {
    try {
      await deleteTrackedDocument(docId);
      toast.success("Document deleted");
      setDocs(prev => prev.filter(d => d.id !== docId));
      fetchCollections();
    } catch { toast.error("Failed to delete"); }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || !selected) return;
    e.target.value = "";

    for (const file of Array.from(files)) {
      setUploading(true);
      try {
        const result = await ingestFile(selected, file);
        toast.success(`${file.name}: Ingested`);
      } catch (err) {
        toast.error(`${file.name}: ${err instanceof Error ? err.message : "Failed"}`);
      } finally { setUploading(false); }
    }
    await fetchDocs(selected);
    await fetchCollections();
  };

  const handleSearch = async () => {
    if (!searchQuery.trim() || !selected) return;
    setSearching(true);
    try {
      const data = await searchDocuments({ query: searchQuery, collection_name: selected, limit: 10 });
      setSearchResults(data.results);
      if (data.results.length === 0) toast.info("No results");
    } catch { toast.error("Search failed"); }
    finally { setSearching(false); }
  };

  const info = collections.find(c => c.name === selected)?.info;

  return (
    <div className="-m-3 flex h-full sm:-m-6">
      {/* Sidebar — collections */}
      {sidebarOpen && (
        <div className="flex w-64 shrink-0 flex-col border-r">
          <div className="flex h-12 items-center justify-between border-b px-3">
            <h2 className="text-sm font-semibold">Collections</h2>
            <div className="flex gap-1">
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setShowCreate(!showCreate)}>
                <Plus className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSidebarOpen(false)}>
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {showCreate && (
            <div className="border-b p-3">
              <div className="flex gap-1.5">
                <Input placeholder="name" value={newName} onChange={e => setNewName(e.target.value)} onKeyDown={e => e.key === "Enter" && handleCreate()} className="h-7 text-xs" />
                <Button size="sm" onClick={handleCreate} className="h-7 px-2 text-xs">OK</Button>
              </div>
            </div>
          )}

          <div className="scrollbar-thin flex-1 overflow-y-auto p-2">
            {loading ? (
              <div className="space-y-2 p-2">{[1,2,3].map(i => <Skeleton key={i} className="h-10 w-full rounded-md" />)}</div>
            ) : collections.length === 0 ? (
              <div className="py-8 text-center">
                <Database className="text-muted-foreground mx-auto mb-2 h-6 w-6" />
                <p className="text-muted-foreground text-xs">No collections</p>
                <Button variant="link" size="sm" className="mt-1 text-xs" onClick={() => setShowCreate(true)}>Create one</Button>
              </div>
            ) : (
              <div className="space-y-1">
                {collections.map(col => (
                  <button
                    key={col.name}
                    onClick={() => { setSelected(col.name); setSearchResults([]); setTab("documents"); }}
                    className={`group flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left text-sm transition-colors ${selected === col.name ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-muted/50"}`}
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{col.name}</p>
                      <p className="text-[10px] opacity-60">
                        {col.info ? `${col.info.total_vectors} vectors` : ""}
                      </p>
                    </div>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <button
                          className="text-destructive shrink-0 rounded p-0.5 opacity-0 group-hover:opacity-100"
                          onClick={e => e.stopPropagation()}
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete collection &ldquo;{col.name}&rdquo;?</AlertDialogTitle>
                          <AlertDialogDescription>All documents and vectors will be permanently removed.</AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => handleDelete(col.name)}>Delete</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex min-w-0 flex-1 flex-col">
        {!selected ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3">
            {!sidebarOpen && (
              <Button variant="ghost" size="sm" onClick={() => setSidebarOpen(true)} className="mb-4">
                <Database className="mr-2 h-4 w-4" /> Show Collections
              </Button>
            )}
            <FolderOpen className="text-muted-foreground h-10 w-10" />
            <p className="text-muted-foreground text-sm">Select or create a collection</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex items-center justify-between border-b px-4 py-3">
              <div className="flex items-center gap-3">
                {!sidebarOpen && (
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSidebarOpen(true)}>
                    <Database className="h-4 w-4" />
                  </Button>
                )}
                <div>
                  <h2 className="font-semibold">{selected}</h2>
                  <p className="text-muted-foreground text-xs">
                    {info ? `${info.total_vectors.toLocaleString()} vectors · ${info.dim}d` : ""}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} disabled={uploading}>
                  {uploading ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <Upload className="mr-2 h-3.5 w-3.5" />}
                  Upload
                </Button>
                <input ref={fileRef} type="file" onChange={handleUpload} accept=".pdf,.docx,.txt,.md" multiple className="hidden" />
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b px-4">
              <button className={`px-3 py-2 text-sm font-medium ${tab === "documents" ? "border-b-2 border-brand text-foreground" : "text-muted-foreground"}`} onClick={() => setTab("documents")}>
                Documents {docs.length > 0 && `(${docs.length})`}
              </button>
              <button className={`px-3 py-2 text-sm font-medium ${tab === "search" ? "border-b-2 border-brand text-foreground" : "text-muted-foreground"}`} onClick={() => setTab("search")}>
                Search
              </button>
            </div>

            {/* Content */}
            <div className="scrollbar-thin flex-1 overflow-y-auto p-4">
              {tab === "documents" && (
                docsLoading ? (
                  <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-14 w-full rounded-lg" />)}</div>
                ) : docs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-16">
                    <FileText className="text-muted-foreground mb-3 h-8 w-8" />
                    <p className="text-muted-foreground text-sm">No documents</p>
                    <p className="text-muted-foreground mt-1 text-xs">Upload PDF, DOCX, TXT, or MD</p>
                    <Button variant="outline" size="sm" className="mt-4" onClick={() => fileRef.current?.click()}>
                      <Upload className="mr-2 h-4 w-4" /> Upload Files
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {docs.map(doc => (
                      <div key={doc.id} className="flex items-center justify-between rounded-lg border p-3">
                        <div className="flex items-center gap-3 overflow-hidden">
                          <StatusIcon status={doc.status} />
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium">{doc.filename}</p>
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-[10px]">{doc.filetype.toUpperCase()}</Badge>
                              {doc.status === "done" && (
                                <span className="text-muted-foreground text-xs">
                                  {(doc.filesize / 1024).toFixed(0)} KB
                                </span>
                              )}
                              {doc.status === "processing" && <span className="text-brand text-xs">Processing...</span>}
                              {doc.status === "error" && (
                                <span className="text-xs text-red-500 truncate max-w-[200px]">{doc.error_message}</span>
                              )}
                              {doc.created_at && (
                                <span className="text-muted-foreground text-[10px]">
                                  {new Date(doc.created_at).toLocaleDateString()}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-0.5">
                          {doc.has_file && (
                            <a
                              href={getDocumentDownloadUrl(doc.id)}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-muted-foreground hover:text-foreground rounded p-1.5 transition-colors"
                              title="View original"
                            >
                              <Eye className="h-3.5 w-3.5" />
                            </a>
                          )}
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <button className="text-destructive hover:text-destructive rounded p-1.5 transition-colors">
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Delete &ldquo;{doc.filename}&rdquo;?</AlertDialogTitle>
                                <AlertDialogDescription>This will remove the document from vector store and storage.</AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => handleDeleteDoc(doc.id)}>Delete</AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              )}

              {tab === "search" && (
                <div className="space-y-4">
                  <div className="flex gap-2">
                    <Input
                      placeholder={`Search in "${selected}"...`}
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && handleSearch()}
                    />
                    <Button onClick={handleSearch} disabled={searching || !searchQuery.trim()}>
                      <Search className="mr-2 h-4 w-4" />
                      {searching ? "..." : "Search"}
                    </Button>
                  </div>

                  {searchResults.length > 0 && (
                    <div className="space-y-2">
                      {searchResults.map((r, i) => {
                        // Try to find the source document for "View original" link
                        const sourceDoc = docs.find(d => d.filename === r.metadata?.filename && d.has_file);
                        return (
                          <Card key={i} className="p-3">
                            <div className="mb-1.5 flex flex-wrap items-center gap-2">
                              <FileText className="text-muted-foreground h-3.5 w-3.5" />
                              <span className="text-xs font-medium">{r.metadata?.filename || "?"}</span>
                              {r.metadata?.page_num && <Badge variant="outline" className="text-[10px]">p.{r.metadata.page_num}</Badge>}
                              <Badge variant="secondary" className="ml-auto text-[10px]">{r.score.toFixed(3)}</Badge>
                              {sourceDoc && (
                                <a
                                  href={getDocumentDownloadUrl(sourceDoc.id)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-brand hover:text-brand-hover inline-flex items-center gap-1 text-[10px] font-medium"
                                >
                                  <Eye className="h-3 w-3" /> View source
                                </a>
                              )}
                            </div>
                            <p className="text-muted-foreground text-sm leading-relaxed">{r.content}</p>
                          </Card>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

{%- else %}
export default function RAGPage() { return null; }
{%- endif %}
