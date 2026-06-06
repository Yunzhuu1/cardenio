import { MenuIcon, PanelLeftCloseIcon } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router";
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
  const { pathname } = useLocation();
  const SidebarToggleIcon = open ? PanelLeftCloseIcon : MenuIcon;
  const titleKey = getTopbarTitleKey(pathname);

  return (
    <header className="flex min-h-14 items-center justify-between gap-3 border-b border-border p-3">
      <div className="flex min-w-0 items-center gap-3">
        <SidebarTrigger
          aria-label={open ? t("nav.collapseSidebar") : t("nav.expandSidebar")}
          className="size-8 shrink-0"
        >
          <SidebarToggleIcon aria-hidden="true" className="size-4" />
        </SidebarTrigger>
        <NavLink
          className="app-heading truncate text-md text-foreground"
          to="/"
        >
          {titleKey ? t(titleKey) : t("app.name")}
        </NavLink>
      </div>
    </header>
  );
}

function getTopbarTitleKey(pathname: string): string {
  if (pathname === "/") return "overview.title";

  const projectStage = pathname.match(/^\/projects\/[^/]+\/([^/]+)/)?.[1];
  if (
    !projectStage ||
    ![
      "import",
      "analysis",
      "outline",
      "script",
      "editor",
      "report",
      "settings",
    ].includes(projectStage)
  ) {
    return "app.name";
  }

  return `pages.${projectStage}.title`;
}
