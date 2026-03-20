import { Header, Sidebar } from "@/components/layout";
import { AuthGuard } from "@/components/layout/auth-guard";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex h-screen flex-col">
        <Header />
        <Sidebar />
        <main className="flex-1 overflow-auto p-3 sm:p-6">{children}</main>
      </div>
    </AuthGuard>
  );
}
