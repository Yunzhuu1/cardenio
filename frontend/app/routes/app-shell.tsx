import { MenuIcon, PanelLeftCloseIcon } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/app-shell";
import { AppSidebar } from "~/components/app-sidebar";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "~/components/ui/sidebar";
import { api } from "~/lib/api/client";

export async function clientLoader() {
  const { items } = await api.projects.list();
  return { projects: items };
}

export default function AppShell({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { projects } = loaderData;

  return (
    <SidebarProvider>
      <AppSidebar projects={projects} />

      <SidebarInset>
        <AppTopbar />
        <main className="min-w-0 flex-1 px-5 py-8 sm:px-8">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

function AppTopbar(): React.ReactElement {
  const { t } = useTranslation();
  const { open } = useSidebar();
  const SidebarToggleIcon = open ? PanelLeftCloseIcon : MenuIcon;

  return (
    <header className="flex min-h-14 items-center justify-between gap-3 border-b border-border px-5 py-3 sm:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <SidebarTrigger
          aria-label={open ? t("nav.collapseSidebar") : t("nav.expandSidebar")}
          className="size-9 shrink-0 border border-border"
        >
          <SidebarToggleIcon aria-hidden="true" className="size-4" />
        </SidebarTrigger>
        <NavLink
          className="app-heading truncate text-sm font-semibold text-foreground md:hidden"
          to="/"
        >
          {t("app.name")}
        </NavLink>
      </div>
    </header>
  );
}
