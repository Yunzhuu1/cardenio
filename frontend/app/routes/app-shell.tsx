import {
  CheckIcon,
  MenuIcon,
  PanelLeftCloseIcon,
  SettingsIcon,
} from "lucide-react";
import { Link, NavLink, Outlet, useLocation, useMatches } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/app-shell";
import { AppSidebar } from "~/components/app-sidebar";
import { Button } from "~/components/ui/button";
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
import { Tooltip, TooltipPopup, TooltipTrigger } from "~/components/ui/tooltip";
import { api } from "~/lib/api/client";
import type { ProjectSummary, Source } from "~/lib/api/types";
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
        <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
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
    <header className="flex min-h-14 shrink-0 items-center justify-between gap-3 p-3">
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
  const matches = useMatches();
  const routeContext = getProjectRouteContext(pathname, projects);
  if (!routeContext) return null;

  const projectState = routeContext.project?.state ?? "empty";
  const importSource = getImportSourceFromMatches(matches);
  const analysisComplete =
    getAnalysisCompleteFromMatches(matches) ??
    isStageDone("analysis", projectState);
  const outlineConfirmed =
    getOutlineConfirmedFromMatches(matches) ??
    isStageDone("outline", projectState);
  const showImportNextAction =
    routeContext.stageSegment === "import" && importSource !== null;
  const showAnalysisNextAction = routeContext.stageSegment === "analysis";
  const showOutlineNextAction = routeContext.stageSegment === "outline";

  return (
    <footer className="shrink-0 px-5 py-3 sm:px-8">
      <div className="mx-auto flex w-full max-w-6xl items-center gap-4">
        <nav
          aria-label={t("nav.stages")}
          className="min-w-0 flex-1 overflow-x-auto"
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
                        ? "bg-accent text-foreground"
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
        {showImportNextAction ? (
          <ImportFooterNextAction
            projectId={routeContext.projectId}
            source={importSource}
          />
        ) : null}
        {showAnalysisNextAction ? (
          <AnalysisFooterNextAction
            complete={analysisComplete}
            projectId={routeContext.projectId}
          />
        ) : null}
        {showOutlineNextAction ? (
          <OutlineFooterNextAction
            confirmed={outlineConfirmed}
            projectId={routeContext.projectId}
          />
        ) : null}
      </div>
    </footer>
  );
}

function ImportFooterNextAction({
  projectId,
  source,
}: {
  projectId: string;
  source: Source;
}): React.ReactElement {
  const { t } = useTranslation();

  if (source.threshold.passed) {
    return (
      <Button
        className="shrink-0"
        render={<Link to={stagePath(projectId, "analysis")} />}
      >
        {t("import.nextStep")}
      </Button>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            aria-disabled
            className="shrink-0 cursor-not-allowed opacity-64 hover:bg-primary"
            onClick={(event) => event.preventDefault()}
            type="button"
          />
        }
      >
        {t("import.nextStep")}
      </TooltipTrigger>
      <TooltipPopup align="end">
        {t("import.nextStepDisabledTooltip", {
          min: source.threshold.min_chapters,
        })}
      </TooltipPopup>
    </Tooltip>
  );
}

function AnalysisFooterNextAction({
  complete,
  projectId,
}: {
  complete: boolean;
  projectId: string;
}): React.ReactElement {
  const { t } = useTranslation();

  if (complete) {
    return (
      <Button
        className="shrink-0"
        render={<Link to={stagePath(projectId, "outline")} />}
      >
        {t("analysis.intent.outlineCta")}
      </Button>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            aria-disabled
            className="shrink-0 cursor-not-allowed opacity-64 hover:bg-primary"
            onClick={(event) => event.preventDefault()}
            type="button"
          />
        }
      >
        {t("analysis.intent.outlineCta")}
      </TooltipTrigger>
      <TooltipPopup align="end">
        {t("analysis.nextStepDisabledTooltip")}
      </TooltipPopup>
    </Tooltip>
  );
}

function OutlineFooterNextAction({
  confirmed,
  projectId,
}: {
  confirmed: boolean;
  projectId: string;
}): React.ReactElement {
  const { t } = useTranslation();

  if (confirmed) {
    return (
      <Button
        className="shrink-0"
        render={<Link to={stagePath(projectId, "script")} />}
      >
        {t("outline.scriptCta")}
      </Button>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Button
            aria-disabled
            className="shrink-0 cursor-not-allowed opacity-64 hover:bg-primary"
            onClick={(event) => event.preventDefault()}
            type="button"
          />
        }
      >
        {t("outline.scriptCta")}
      </TooltipTrigger>
      <TooltipPopup align="end">
        {t("outline.nextStepDisabledTooltip")}
      </TooltipPopup>
    </Tooltip>
  );
}

function getProjectRouteContext(
  pathname: string,
  projects: ProjectSummary[],
): {
  project: ProjectSummary | undefined;
  projectId: string;
  projectTitle: string;
  stageSegment: string;
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
    stageSegment: projectStage,
    stageKey: `pages.${projectStage}.title`,
  };
}

function getImportSourceFromMatches(
  matches: ReturnType<typeof useMatches>,
): Source | null {
  for (const match of matches) {
    const data = match.data;
    if (
      typeof data === "object" &&
      data !== null &&
      "source" in data &&
      isSource((data as { source: unknown }).source)
    ) {
      return (data as { source: Source }).source;
    }
  }

  return null;
}

function getAnalysisCompleteFromMatches(
  matches: ReturnType<typeof useMatches>,
): boolean | null {
  for (const match of matches) {
    const data = match.data;
    if (
      typeof data === "object" &&
      data !== null &&
      "understanding" in data &&
      "characters" in data &&
      "intent" in data
    ) {
      const analysisData = data as {
        characters: unknown;
        intent: unknown;
        understanding: unknown;
      };
      return (
        isConfirmedArtifact(analysisData.understanding) &&
        isConfirmedArtifact(analysisData.characters) &&
        analysisData.intent !== null
      );
    }
  }

  return null;
}

function getOutlineConfirmedFromMatches(
  matches: ReturnType<typeof useMatches>,
): boolean | null {
  for (const match of matches) {
    const data = match.data;
    if (typeof data === "object" && data !== null && "outline" in data) {
      return isConfirmedArtifact((data as { outline: unknown }).outline);
    }
  }

  return null;
}

function isConfirmedArtifact(value: unknown): boolean {
  return (
    typeof value === "object" &&
    value !== null &&
    "state" in value &&
    (value as { state: unknown }).state === "confirmed"
  );
}

function isSource(value: unknown): value is Source {
  return (
    typeof value === "object" &&
    value !== null &&
    "threshold" in value &&
    typeof (value as Source).threshold === "object" &&
    (value as Source).threshold !== null &&
    "stats" in value
  );
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
