import Link from "next/link";
{%- if cookiecutter.enable_i18n %}
import { getTranslations } from "next-intl/server";
{%- endif %}
import { Badge, buttonVariants } from "@/components/ui";
import { LandingNav } from "@/components/layout/landing-nav";
import { APP_NAME, APP_DESCRIPTION, ROUTES, BACKEND_URL } from "@/lib/constants";
import { cn } from "@/lib/utils";
import {
{%- if cookiecutter.enable_ai_agent %}
  Bot,
  Zap,
{%- endif %}
{%- if cookiecutter.enable_rag %}
  Database,
{%- endif %}
{%- if cookiecutter.use_jwt or cookiecutter.use_api_key %}
  Shield,
{%- endif %}
  LayoutDashboard,
  Server,
  ArrowRight,
  ChevronRight,
  ChevronDown,
} from "lucide-react";

export default async function HomePage() {
{%- if cookiecutter.enable_i18n %}
  const t = await getTranslations("landing");
{%- endif %}

  const features = [
{%- if cookiecutter.enable_ai_agent %}
    {
      icon: Bot,
      title: {% if cookiecutter.enable_i18n %}t("featureAiChat"){% else %}"AI-Powered Chat"{% endif %},
      desc: {% if cookiecutter.enable_i18n %}t("featureAiChatDesc"){% else %}"Conversational AI assistant with real-time streaming, conversation history, and tool-calling capabilities."{% endif %},
      href: ROUTES.CHAT,
    },
{%- endif %}
{%- if cookiecutter.enable_rag %}
    {
      icon: Database,
      title: {% if cookiecutter.enable_i18n %}t("featureRag"){% else %}"Knowledge Base"{% endif %},
      desc: {% if cookiecutter.enable_i18n %}t("featureRagDesc"){% else %}"Vector search across your documents with retrieval-augmented generation."{% endif %},
      href: ROUTES.RAG,
    },
{%- endif %}
{%- if cookiecutter.use_jwt or cookiecutter.use_api_key %}
    {
      icon: Shield,
      title: {% if cookiecutter.enable_i18n %}t("featureAuth"){% else %}"Secure Authentication"{% endif %},
      desc: {% if cookiecutter.enable_i18n %}t("featureAuthDesc"){% else %}"JWT-based auth with refresh tokens, OAuth integration, and role-based access control."{% endif %},
    },
{%- endif %}
    {
      icon: LayoutDashboard,
      title: {% if cookiecutter.enable_i18n %}t("featureDashboard"){% else %}"Dashboard"{% endif %},
      desc: {% if cookiecutter.enable_i18n %}t("featureDashboardDesc"){% else %}"System health monitoring, user management, and statistics at a glance."{% endif %},
      href: ROUTES.DASHBOARD,
    },
    {
      icon: Server,
      title: {% if cookiecutter.enable_i18n %}t("featureApi"){% else %}"REST API"{% endif %},
      desc: {% if cookiecutter.enable_i18n %}t("featureApiDesc"){% else %}"Auto-documented FastAPI backend with OpenAPI specs and async database access."{% endif %},
    },
{%- if cookiecutter.enable_ai_agent %}
    {
      icon: Zap,
      title: {% if cookiecutter.enable_i18n %}t("featureRealtime"){% else %}"Real-time"{% endif %},
      desc: {% if cookiecutter.enable_i18n %}t("featureRealtimeDesc"){% else %}"WebSocket-powered streaming for instant AI responses and live updates."{% endif %},
    },
{%- endif %}
  ];

  const techItems = [
    "Next.js 15", "React 19", "TypeScript", "Tailwind CSS", "FastAPI",
{%- if cookiecutter.use_pydantic_ai %} "PydanticAI",{%- endif %}
{%- if cookiecutter.use_langchain %} "LangChain",{%- endif %}
{%- if cookiecutter.use_langgraph %} "LangGraph",{%- endif %}
{%- if cookiecutter.use_crewai %} "CrewAI",{%- endif %}
{%- if cookiecutter.use_sqlmodel %} "SQLModel",{%- elif cookiecutter.use_sqlalchemy %} "SQLAlchemy",{%- endif %}
{%- if cookiecutter.use_postgresql %} "PostgreSQL",{%- elif cookiecutter.use_sqlite %} "SQLite",{%- elif cookiecutter.use_mongodb %} "MongoDB",{%- endif %}
{%- if cookiecutter.enable_redis %} "Redis",{%- endif %}
{%- if cookiecutter.use_celery %} "Celery",{%- elif cookiecutter.use_taskiq %} "Taskiq",{%- endif %}
{%- if cookiecutter.use_milvus %} "Milvus",{%- elif cookiecutter.use_qdrant %} "Qdrant",{%- elif cookiecutter.use_chromadb %} "ChromaDB",{%- endif %}
{%- if cookiecutter.enable_docker %} "Docker",{%- endif %}
{%- if cookiecutter.use_traefik %} "Traefik",{%- endif %}
{%- if cookiecutter.use_jwt %} "JWT Auth",{%- endif %}
{%- if cookiecutter.enable_oauth %} "OAuth2",{%- endif %}
{%- if cookiecutter.enable_ai_agent %} "WebSockets",{%- endif %}
{%- if cookiecutter.enable_logfire %} "Logfire", "OpenTelemetry",{%- endif %}
{%- if cookiecutter.enable_rag %} "PyMuPDF", "BM25",{%- endif %}
{%- if cookiecutter.enable_i18n %} "next-intl",{%- endif %}
    "Pydantic v2", "Alembic", "Zustand", "TanStack Query", "Vitest",
  ];

  return (
    <div className="bg-background min-h-screen">
      <LandingNav
        signInLabel={ {% if cookiecutter.enable_i18n %}t("signIn"){% else %}"Sign In"{% endif %}}
        getStartedLabel={ {% if cookiecutter.enable_i18n %}t("getStarted"){% else %}"Get Started"{% endif %}}
        dashboardLabel={ {% if cookiecutter.enable_i18n %}t("featureDashboard"){% else %}"Dashboard"{% endif %}}
      />

      <main>
        {/* Hero */}
        <section className="relative flex min-h-svh items-center justify-center overflow-hidden px-4 sm:px-6">
          <div className="grid-bg pointer-events-none absolute inset-0" />
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute left-1/2 top-[5%] h-[400px] w-[500px] -translate-x-1/2 rounded-full bg-brand/[0.12] blur-[120px] sm:h-[600px] sm:w-[800px] sm:blur-[200px]" />
            <div className="absolute left-[30%] top-[15%] h-[300px] w-[350px] -translate-x-1/2 rounded-full bg-brand-muted/[0.08] blur-[100px] sm:h-[400px] sm:w-[500px] sm:blur-[160px]" />
          </div>
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-background to-transparent" />

          <div className="relative mx-auto max-w-4xl text-center">
            <div className="mb-8 inline-flex items-center rounded-full border border-brand/20 bg-brand/[0.06] px-4 py-1.5 text-sm text-muted-foreground">
              <span className="mr-2 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-brand" />
              {APP_DESCRIPTION}
            </div>

            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
              { {% if cookiecutter.enable_i18n %}t("heroTitle"){% else %}"Build Intelligent"{% endif %}}{" "}
              <span className="bg-gradient-to-r from-brand to-brand-hover bg-clip-text text-transparent">
                { {% if cookiecutter.enable_i18n %}t("heroHighlight"){% else %}"Applications"{% endif %}}
              </span>
              <br />
              { {% if cookiecutter.enable_i18n %}t("heroTitleEnd"){% else %}"with Confidence"{% endif %}}
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
              { {% if cookiecutter.enable_i18n %}t("heroSubtitle"){% else %}"A production-ready full-stack platform with AI-powered chat, knowledge base retrieval, secure authentication, and a modern dashboard."{% endif %}}
            </p>

            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link
                href={ROUTES.{% if cookiecutter.use_jwt or cookiecutter.use_api_key %}REGISTER{% else %}DASHBOARD{% endif %}}
                className="inline-flex items-center gap-2 rounded-full bg-brand px-8 py-3 text-base font-semibold text-brand-foreground transition-all hover:bg-brand-hover hover:shadow-lg"
              >
                { {% if cookiecutter.enable_i18n %}t("getStarted"){% else %}"Get Started"{% endif %}}
                <ArrowRight className="h-4 w-4" />
              </Link>
{%- if cookiecutter.use_jwt or cookiecutter.use_api_key %}
              <Link
                href={ROUTES.LOGIN}
                className="inline-flex items-center rounded-full border border-border bg-background/50 px-8 py-3 text-base font-semibold backdrop-blur-sm transition-all hover:border-border/80 hover:bg-background/80"
              >
                { {% if cookiecutter.enable_i18n %}t("signIn"){% else %}"Sign In"{% endif %}}
              </Link>
{%- endif %}
            </div>
          </div>

          <a
            href="#features"
            className="scroll-arrow absolute bottom-8 left-1/2 flex h-10 w-10 -translate-x-1/2 items-center justify-center rounded-full border border-border bg-card text-muted-foreground transition-colors hover:border-brand hover:text-brand"
          >
            <ChevronDown className="h-5 w-5" />
          </a>
        </section>

        {/* Features */}
        <section id="features" className="flex min-h-screen items-center px-4 py-20 sm:px-6 sm:py-28">
          <div className="mx-auto w-full max-w-6xl">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((feature) => {
                const Icon = feature.icon;
                return (
                  <div key={feature.title} className="glass-card group rounded-xl p-6">
                    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-brand/10 transition-transform group-hover:scale-110">
                      <Icon className="h-6 w-6 text-brand" />
                    </div>
                    <h3 className="mb-2 text-lg font-semibold">{feature.title}</h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">{feature.desc}</p>
                    {feature.href && (
                      <Link
                        href={feature.href}
                        className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand transition-colors hover:text-brand-hover"
                      >
                        { {% if cookiecutter.enable_i18n %}t("learnMore"){% else %}"Learn More"{% endif %}}
                        <ChevronRight className="h-3 w-3" />
                      </Link>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Tech Stack Marquee */}
        <section className="border-t border-border/50 py-16 overflow-hidden">
          <div className="mx-auto max-w-5xl px-4 text-center sm:px-6">
            <h2 className="mb-10 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              { {% if cookiecutter.enable_i18n %}t("techStackTitle"){% else %}"Built with modern technologies"{% endif %}}
            </h2>
          </div>
          <div className="marquee-container">
            <div className="marquee-track marquee-left">
              {[...techItems, ...techItems].map((tech, i) => (
                <span
                  key={`${tech}-${i}`}
                  className="inline-flex shrink-0 items-center rounded-lg border border-border/60 bg-card px-5 py-2.5 text-sm font-medium text-foreground/80"
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="px-4 py-20 sm:px-6">
          <div className="relative mx-auto max-w-4xl overflow-hidden rounded-2xl border border-border/50 bg-card px-4 py-16 text-center sm:px-6">
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="h-[300px] w-[500px] rounded-full bg-brand/[0.06] blur-[100px]" />
            </div>
            <div className="relative">
              <h2 className="mb-4 text-3xl font-bold tracking-tight">
                { {% if cookiecutter.enable_i18n %}t("ctaTitle"){% else %}"Ready to get started?"{% endif %}}
              </h2>
              <p className="mx-auto mb-8 max-w-lg text-muted-foreground">
                { {% if cookiecutter.enable_i18n %}t("ctaSubtitle"){% else %}"Create your account and start exploring the platform."{% endif %}}
              </p>
              <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
                <Link
                  href={ROUTES.{% if cookiecutter.use_jwt or cookiecutter.use_api_key %}REGISTER{% else %}DASHBOARD{% endif %}}
                  className="inline-flex items-center gap-2 rounded-full bg-brand px-8 py-3 text-base font-semibold text-brand-foreground transition-all hover:bg-brand-hover hover:shadow-lg"
                >
                  { {% if cookiecutter.enable_i18n %}t("createAccount"){% else %}"Get Started"{% endif %}}
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a
                  href={ `${BACKEND_URL}/docs`}
                  className={cn(buttonVariants({ variant: "outline", size: "lg" }), "rounded-full px-8")}
                >
                  { {% if cookiecutter.enable_i18n %}t("exploreApi"){% else %}"Explore API"{% endif %}}
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50">
        <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
          <div className="flex flex-col gap-8 sm:flex-row sm:justify-between">
            <div className="max-w-xs">
              <p className="text-lg font-bold tracking-tight">{APP_NAME}</p>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                { {% if cookiecutter.enable_i18n %}t("footerDesc"){% else %}"Full-stack AI application platform with enterprise-grade features."{% endif %}}
              </p>
            </div>
            <div className="flex gap-16">
              <div>
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  { {% if cookiecutter.enable_i18n %}t("footerProduct"){% else %}"Product"{% endif %}}
                </h4>
                <ul className="space-y-2">
                  <li><Link href={ROUTES.DASHBOARD} className="text-sm text-muted-foreground transition-colors hover:text-foreground">Dashboard</Link></li>
{%- if cookiecutter.enable_ai_agent %}
                  <li><Link href={ROUTES.CHAT} className="text-sm text-muted-foreground transition-colors hover:text-foreground">Chat</Link></li>
{%- endif %}
{%- if cookiecutter.enable_rag %}
                  <li><Link href={ROUTES.RAG} className="text-sm text-muted-foreground transition-colors hover:text-foreground">Knowledge Base</Link></li>
{%- endif %}
                </ul>
              </div>
              <div>
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  { {% if cookiecutter.enable_i18n %}t("footerResources"){% else %}"Resources"{% endif %}}
                </h4>
                <ul className="space-y-2">
                  <li><a href={ `${BACKEND_URL}/docs`} className="text-sm text-muted-foreground transition-colors hover:text-foreground">API Docs</a></li>
{%- if cookiecutter.use_jwt or cookiecutter.use_api_key %}
                  <li><Link href={ROUTES.LOGIN} className="text-sm text-muted-foreground transition-colors hover:text-foreground">Sign In</Link></li>
{%- endif %}
                </ul>
              </div>
            </div>
          </div>
        </div>
        <div className="border-t border-border/50">
          <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
            <p className="text-center text-xs text-muted-foreground">
              &copy; {new Date().getFullYear()} {APP_NAME}. { {% if cookiecutter.enable_i18n %}t("copyright"){% else %}"All rights reserved."{% endif %}}
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
