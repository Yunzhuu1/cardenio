import { Link } from "react-router";
import { SlidersHorizontalIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/analysis-intent";
import {
  Alert,
  AlertAction,
  AlertDescription,
  AlertTitle,
} from "~/components/ui/alert";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardPanel,
  CardTitle,
} from "~/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { api } from "~/lib/api/client";
import { ApiError } from "~/lib/api/types";
import { analysisStepPath } from "~/lib/stages";

async function getOrNull<T>(request: Promise<T>): Promise<T | null> {
  try {
    return await request;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const [intent, characters, project] = await Promise.all([
    getOrNull(api.intent.get(params.projectId)),
    getOrNull(api.characters.get(params.projectId)),
    api.projects.get(params.projectId),
  ]);
  return { intent, characters, project };
}

export default function AnalysisIntent({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const { intent, characters, project } = loaderData;
  const locked = characters?.state !== "confirmed";
  const status = intent ? "confirmed" : "empty";

  return (
    <section className="space-y-4">
      <div>
        <div className="mb-2 text-sm font-medium text-muted-foreground">
          {t("analysis.stepOf", { current: 3, total: 3 })}
        </div>
        <h2 className="app-heading text-2xl">{t("analysis.intent.title")}</h2>
        <p className="mt-2 max-w-3xl text-muted-foreground text-sm">
          {t("analysis.intent.description")}
        </p>
      </div>

      {locked ? (
        <Alert variant="warning">
          <AlertTitle>{t("analysis.intent.lockedTitle")}</AlertTitle>
          <AlertDescription>
            {t("analysis.intent.lockedDescription")}
          </AlertDescription>
          <AlertAction>
            <Button
              render={<Link to={analysisStepPath(project.id, "characters")} />}
              size="sm"
              variant="outline"
            >
              {t("analysis.backToCharacters")}
            </Button>
          </AlertAction>
        </Alert>
      ) : intent ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("analysis.intent.cardTitle")}</CardTitle>
            <CardDescription>
              {t("analysis.intent.cardDescription")}
            </CardDescription>
          </CardHeader>
          <CardPanel className="flex items-center justify-between gap-4">
            <span className="text-muted-foreground text-sm">
              {t("analysis.currentStatus")}
            </span>
            <Badge variant="success">{t(`analysis.status.${status}`)}</Badge>
          </CardPanel>
        </Card>
      ) : (
        <Empty className="rounded-lg border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <SlidersHorizontalIcon aria-hidden className="size-4" />
            </EmptyMedia>
            <EmptyTitle>{t("analysis.intent.emptyTitle")}</EmptyTitle>
            <EmptyDescription>
              {t("analysis.intent.emptyDescription")}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}
    </section>
  );
}
