import { MenuIcon, PanelLeftCloseIcon } from "lucide-react";
import { Outlet, useLocation } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/app-shell";
import { AppSidebar } from "~/components/app-sidebar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "~/components/ui/breadcrumb";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
  useSidebar,
} from "~/components/ui/sidebar";
import { api } from "~/lib/api/client";
import type { ProjectSummary } from "~/lib/api/types";

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
        <AppTopbar projects={projects} />
        <main className="min-h-0 min-w-0 flex-1 overflow-y-auto px-5 py-8 sm:px-8">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}

function AppTopbar({
  projects,
}: {
  projects: ProjectSummary[];
}): React.ReactElement {
  const { t } = useTranslation();
  const { open } = useSidebar();
  const { pathname } = useLocation();
  const SidebarToggleIcon = open ? PanelLeftCloseIcon : MenuIcon;
  const routeContext = getProjectRouteContext(pathname, projects);
  const stageTitle = routeContext?.stageKey
    ? t(routeContext.stageKey)
    : t(getTopbarTitleKey(pathname));

  return (
    <header className="flex min-h-14 shrink-0 items-center justify-between gap-3 border-b border-border p-3">
      <div className="flex min-w-0 items-center gap-3">
        <SidebarTrigger
          aria-label={open ? t("nav.collapseSidebar") : t("nav.expandSidebar")}
          className="size-8 shrink-0"
        >
          <SidebarToggleIcon aria-hidden="true" className="size-4" />
        </SidebarTrigger>
        <Breadcrumb className="pointer-events-none min-w-0 select-none">
          <BreadcrumbList className="flex-nowrap gap-1.5 sm:gap-2">
            {routeContext ? (
              <>
                <BreadcrumbItem className="min-w-0">
                  <span className="truncate text-muted-foreground">
                    {routeContext.projectTitle}
                  </span>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="shrink-0" />
              </>
            ) : null}
            <BreadcrumbItem className="min-w-0">
              <BreadcrumbPage className="app-heading truncate text-md">
                {stageTitle}
              </BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>
    </header>
  );
}

function getProjectRouteContext(
  pathname: string,
  projects: ProjectSummary[],
): { projectTitle: string; stageKey: string } | null {
  const match = pathname.match(/^\/projects\/([^/]+)(?:\/([^/]+))?/);
  if (!match) return null;

  const [, projectId, projectStage = "import"] = match;
  if (!isProjectStage(projectStage)) return null;

  const project = projects.find((item) => item.id === projectId);
  return {
    projectTitle: project?.title ?? projectId,
    stageKey: `pages.${projectStage}.title`,
  };
}

function getTopbarTitleKey(pathname: string): string {
  if (pathname === "/") return "overview.title";

  const projectStage = pathname.match(/^\/projects\/[^/]+\/([^/]+)/)?.[1];
  if (!projectStage || !isProjectStage(projectStage)) {
    return "app.name";
  }

  return `pages.${projectStage}.title`;
}

function isProjectStage(stage: string): boolean {
  return [
    "import",
    "analysis",
    "outline",
    "script",
    "editor",
    "report",
    "settings",
  ].includes(stage);
}
