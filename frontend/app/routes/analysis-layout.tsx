import { CheckIcon, LockIcon } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import { useState, type ReactNode } from "react";
import type { Route } from "./+types/analysis-layout";
import { Badge } from "~/components/ui/badge";
import { api } from "~/lib/api/client";
import { ApiError, type ArtifactState } from "~/lib/api/types";
import { analysisStepPath, type AnalysisStep } from "~/lib/stages";
import { cn } from "~/lib/utils";

type NullableArtifact = { state: ArtifactState } | null;
type StepStatus = "empty" | ArtifactState;

export type AnalysisLayoutContext = {
  setActions: (actions: ReactNode) => void;
};

async function getOrNull<T>(request: Promise<T>): Promise<T | null> {
  try {
    return await request;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

function artifactStatus(artifact: NullableArtifact): StepStatus {
  return artifact?.state ?? "empty";
}

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const projectId = params.projectId;
  const [project, source, understanding, characters, intent] =
    await Promise.all([
      api.projects.get(projectId),
      api.source.get(projectId),
      getOrNull(api.understanding.get(projectId)),
      getOrNull(api.characters.get(projectId)),
      getOrNull(api.intent.get(projectId)),
    ]);

  return {
    project,
    threshold: source.threshold,
    understanding,
    characters,
    intent,
  };
}

export default function AnalysisLayout({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const { project, understanding, characters, intent } = loaderData;
  const [actions, setActions] = useState<ReactNode>(null);
  const steps: Array<{
    key: AnalysisStep;
    index: number;
    locked: boolean;
    status: StepStatus;
  }> = [
    {
      key: "understanding",
      index: 1,
      locked: false,
      status: artifactStatus(understanding),
    },
    {
      key: "characters",
      index: 2,
      locked: understanding?.state !== "confirmed",
      status: artifactStatus(characters),
    },
    {
      key: "intent",
      index: 3,
      locked: characters?.state !== "confirmed",
      status: intent ? "confirmed" : "empty",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="sticky top-0 z-10 -mx-5 border-b bg-background/95 px-5 py-3 backdrop-blur sm:-mx-8 sm:px-8">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <nav
            aria-label={t("analysis.navLabel")}
            className="flex gap-2 overflow-x-auto"
          >
            {steps.map((step) => {
              const done = step.status === "confirmed";
              const content = (
                <>
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
                      step.index
                    )}
                  </span>
                  <span>{t(`analysis.steps.${step.key}`)}</span>
                  {step.locked ? (
                    <LockIcon aria-hidden className="size-3.5 opacity-70" />
                  ) : (
                    <Badge size="sm" variant={done ? "success" : "secondary"}>
                      {t(`analysis.status.${step.status}`)}
                    </Badge>
                  )}
                </>
              );

              if (step.locked) {
                return (
                  <span
                    aria-disabled="true"
                    className="flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground opacity-70"
                    key={step.key}
                    title={t("analysis.locked")}
                  >
                    {content}
                  </span>
                );
              }

              return (
                <NavLink
                  className={({ isActive }) =>
                    cn(
                      "flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-accent text-foreground"
                        : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                    )
                  }
                  key={step.key}
                  to={analysisStepPath(project.id, step.key)}
                >
                  {content}
                </NavLink>
              );
            })}
          </nav>
          {actions ? (
            <div className="flex shrink-0 flex-wrap gap-2 lg:justify-end">
              {actions}
            </div>
          ) : null}
        </div>
      </div>

      <Outlet context={{ setActions } satisfies AnalysisLayoutContext} />
    </div>
  );
}
