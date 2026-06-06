import { LayoutGridIcon, PlusIcon } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/app-shell";
import { LanguageSwitcher } from "~/components/language-switcher";
import { ThemeToggle } from "~/components/theme-toggle";
import { api } from "~/lib/api/client";
import { cn } from "~/lib/utils";

const linkBase =
  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors";
const linkActive = "bg-sidebar-accent text-sidebar-foreground";
const linkIdle =
  "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground";

export async function clientLoader() {
  const { items } = await api.projects.list();
  return { projects: items };
}

export default function AppShell({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const { projects } = loaderData;

  return (
    <div className="flex min-h-dvh bg-background text-foreground">
      <aside className="hidden w-64 shrink-0 flex-col gap-2 border-r border-sidebar-border bg-sidebar px-3 py-4 md:flex">
        <div className="px-2 pb-2 text-sm font-semibold text-sidebar-foreground">
          {t("app.name")}
        </div>

        <NavLink
          className={({ isActive }) =>
            cn(linkBase, isActive ? linkActive : linkIdle)
          }
          end
          to="/"
        >
          <LayoutGridIcon aria-hidden className="size-4" />
          {t("nav.allProjects")}
        </NavLink>

        <div className="mt-3 px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {t("nav.projectsHeading")}
        </div>

        <nav aria-label={t("nav.label")} className="flex flex-col gap-1">
          {projects.length === 0 ? (
            <p className="px-3 py-2 text-sm text-muted-foreground">
              {t("nav.noProjects")}
            </p>
          ) : (
            projects.map((project) => (
              <NavLink
                className={({ isActive }) =>
                  cn(linkBase, isActive ? linkActive : linkIdle)
                }
                key={project.id}
                to={`/projects/${project.id}`}
              >
                <span className="truncate">{project.title}</span>
              </NavLink>
            ))
          )}
        </nav>

        <NavLink className={cn(linkBase, "mt-2 text-primary")} end to="/">
          <PlusIcon aria-hidden className="size-4" />
          {t("nav.newProject")}
        </NavLink>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border px-5 py-3 sm:px-8">
          <NavLink
            className="text-sm font-semibold text-foreground md:hidden"
            to="/"
          >
            {t("app.name")}
          </NavLink>
          <div aria-hidden className="hidden md:block" />
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <ThemeToggle />
          </div>
        </header>
        <main className="min-w-0 flex-1 px-5 py-8 sm:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
