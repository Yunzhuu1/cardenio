import {
  CheckIcon,
  MenuIcon,
  PanelLeftCloseIcon,
  SettingsIcon,
} from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router";
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
import { isStageDone, stagePath, stages } from "~/lib/stages";
import { cn } from "~/lib/utils";

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
        <main className="min-h-0 min-w-0 flex-1 overflow-hidden px-5 py-8 sm:px-8">
          <Outlet />
        </main>
        <AppStageFooter projects={projects} />
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
      {routeContext ? (
        <NavLink
          aria-label={t("nav.projectSettings")}
          className={({ isActive }) =>
            cn(
              "inline-flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground",
              isActive && "bg-sidebar-accent text-sidebar-foreground",
            )
          }
          to={stagePath(routeContext.projectId, "settings")}
        >
          <SettingsIcon aria-hidden="true" className="size-4" />
        </NavLink>
      ) : null}
    </header>
  );
}

function AppStageFooter({
  projects,
}: {
  projects: ProjectSummary[];
}): React.ReactElement | null {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const routeContext = getProjectRouteContext(pathname, projects);
  if (!routeContext) return null;

  const projectState = routeContext.project?.state ?? "empty";

  return (
    <footer className="shrink-0 border-t border-border px-5 py-3 sm:px-8">
      <nav
        aria-label={t("nav.stages")}
        className="mx-auto w-full max-w-6xl overflow-x-auto"
      >
        <div className="flex gap-2">
          {stages.map((stage, index) => {
            const done = isStageDone(stage.key, projectState);
            return (
              <NavLink
                className={({ isActive }) =>
                  cn(
                    "flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground",
                  )
                }
                key={stage.key}
                to={stagePath(routeContext.projectId, stage.segment)}
              >
                <span
                  className={cn(
                    "flex size-5 items-center justify-center rounded-full border text-xs",
                    done
                      ? "border-success bg-success text-success-foreground"
                      : "border-current",
                  )}
                >
                  {done ? (
                    <CheckIcon aria-hidden className="size-3" />
                  ) : (
                    index + 1
                  )}
                </span>
                {t(`steps.${stage.key}`)}
              </NavLink>
            );
          })}
        </div>
      </nav>
    </footer>
  );
}

function getProjectRouteContext(
  pathname: string,
  projects: ProjectSummary[],
): {
  project: ProjectSummary | undefined;
  projectId: string;
  projectTitle: string;
  stageKey: string;
} | null {
  const match = pathname.match(/^\/projects\/([^/]+)(?:\/([^/]+))?/);
  if (!match) return null;

  const [, projectId, projectStage = "import"] = match;
  if (!isProjectStage(projectStage)) return null;

  const project = projects.find((item) => item.id === projectId);
  return {
    project,
    projectId,
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
