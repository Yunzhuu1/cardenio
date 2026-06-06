import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/app-shell";
import { AppSidebar } from "~/components/app-sidebar";
import { LanguageSwitcher } from "~/components/language-switcher";
import { ThemeToggle } from "~/components/theme-toggle";
import { SidebarInset, SidebarProvider } from "~/components/ui/sidebar";
import { api } from "~/lib/api/client";

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
    <SidebarProvider>
      <AppSidebar projects={projects} />

      <SidebarInset>
        <header className="flex items-center justify-between gap-3 border-b border-border px-5 py-3 sm:px-8">
          <NavLink
            className="app-heading text-sm font-semibold text-foreground md:hidden"
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
      </SidebarInset>
    </SidebarProvider>
  );
}
