import { CheckIcon, SettingsIcon } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/project-layout";
import { api } from "~/lib/api/client";
import { cn } from "~/lib/utils";
import { isStageDone, stagePath, stages } from "~/lib/stages";

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const project = await api.projects.get(params.projectId);
  return { project };
}

export function meta({ data }: Route.MetaArgs) {
  const title = data?.project?.title;
  return [{ title: title ? `${title} · Cardenio 入戏` : "Cardenio 入戏" }];
}

export default function ProjectLayout({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const { project } = loaderData;

  return (
    <div className="mx-auto w-full max-w-6xl">
      <div className="mb-6 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-balance text-foreground">
            {project.title}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t(`state.${project.state}`)}
          </p>
        </div>
        <NavLink
          aria-label={t("nav.projectSettings")}
          className={({ isActive }) =>
            cn(
              "flex size-9 items-center justify-center rounded-md border border-border",
              isActive
                ? "bg-accent text-foreground"
                : "text-muted-foreground hover:bg-accent",
            )
          }
          to={stagePath(project.id, "settings")}
        >
          <SettingsIcon aria-hidden className="size-4" />
        </NavLink>
      </div>

      <nav
        aria-label={t("nav.stages")}
        className="mb-8 flex gap-2 overflow-x-auto border-b border-border pb-3"
      >
        {stages.map((stage, index) => {
          const done = isStageDone(stage.key, project.state);
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
              to={stagePath(project.id, stage.segment)}
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
      </nav>

      <Outlet />
    </div>
  );
}
