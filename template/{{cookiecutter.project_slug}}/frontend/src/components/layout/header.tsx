"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks";
import { Button } from "@/components/ui";
import { ThemeToggle } from "@/components/theme";
{%- if cookiecutter.enable_i18n %}
import { LanguageSwitcherCompact } from "@/components/language-switcher";
{%- endif %}
import { APP_NAME, ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { LogOut, Menu, LayoutDashboard{%- if cookiecutter.enable_ai_agent %}, MessageSquare{%- endif %}{%- if cookiecutter.enable_rag %}, Database{%- endif %}{%- if cookiecutter.use_jwt %}, UserCircle{%- endif %} } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui";
import { useSidebarStore } from "@/stores";

const navItems = [
  { name: "Dashboard", href: ROUTES.DASHBOARD, icon: LayoutDashboard },
{%- if cookiecutter.enable_ai_agent %}
  { name: "Chat", href: ROUTES.CHAT, icon: MessageSquare },
{%- endif %}
{%- if cookiecutter.enable_rag %}
  { name: "Knowledge Base", href: ROUTES.RAG, icon: Database },
{%- endif %}
{%- if cookiecutter.use_jwt %}
  { name: "Profile", href: ROUTES.PROFILE, icon: UserCircle },
{%- endif %}
];

export function Header() {
  const { user, isAuthenticated, logout } = useAuth();
  const { toggle } = useSidebarStore();
  const pathname = usePathname();

  return (
    <header className="bg-background/95 supports-[backdrop-filter]:bg-background/60 sticky top-0 z-40 w-full border-b backdrop-blur">
      <div className="flex h-14 items-center justify-between px-3 sm:px-6">
        {/* Left: mobile menu + app name + nav */}
        <div className="flex items-center gap-1 sm:gap-4">
          <Button variant="ghost" size="sm" className="h-10 w-10 p-0 md:hidden" onClick={toggle}>
            <Menu className="h-5 w-5" />
            <span className="sr-only">Toggle menu</span>
          </Button>

          <Link href={ROUTES.DASHBOARD} className="text-sm font-bold tracking-tight sm:text-base">
            {APP_NAME}
          </Link>

          {/* Desktop nav links */}
          <nav className="hidden items-center gap-0.5 md:flex">
            {navItems.map((item) => {
              const isActive = pathname?.includes(item.href);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <item.icon className="h-3.5 w-3.5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right: language, theme, user */}
        <div className="flex items-center gap-2 sm:gap-3">
{%- if cookiecutter.enable_i18n %}
          <LanguageSwitcherCompact />
{%- endif %}
          <ThemeToggle />
          {isAuthenticated ? (
            <>
              <Button variant="ghost" size="sm" asChild className="h-10 px-2 sm:px-3">
                <Link href={ROUTES.PROFILE} className="flex items-center gap-2">
                  <Avatar className="h-6 w-6">
                    <AvatarFallback className="bg-brand/10 text-brand text-[10px]">
                      {user?.email?.substring(0, 2).toUpperCase() || "U"}
                    </AvatarFallback>
                  </Avatar>
                  <span className="hidden max-w-32 truncate sm:inline">{user?.email}</span>
                </Link>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="h-10 w-10 p-0 sm:w-auto sm:px-3"
              >
                <LogOut className="h-4 w-4" />
                <span className="sr-only sm:not-sr-only sm:ml-2">Logout</span>
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" asChild className="h-10">
                <Link href={ROUTES.LOGIN}>Login</Link>
              </Button>
              <Button size="sm" asChild className="h-10">
                <Link href={ROUTES.REGISTER}>Register</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
