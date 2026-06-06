import { Link } from "react-router";
import { UsersIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/analysis-characters";
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
  const [characters, understanding] = await Promise.all([
    getOrNull(api.characters.get(params.projectId)),
    getOrNull(api.understanding.get(params.projectId)),
  ]);
  return { characters, understanding, projectId: params.projectId };
}

export default function AnalysisCharacters({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const { characters, understanding, projectId } = loaderData;
  const locked = understanding?.state !== "confirmed";
  const status = characters?.state ?? "empty";

  return (
    <section className="space-y-4">
      <div>
        <div className="mb-2 text-sm font-medium text-muted-foreground">
          {t("analysis.stepOf", { current: 2, total: 3 })}
        </div>
        <h2 className="app-heading text-2xl">
          {t("analysis.characters.title")}
        </h2>
        <p className="mt-2 max-w-3xl text-muted-foreground text-sm">
          {t("analysis.characters.description")}
        </p>
      </div>

      {locked ? (
        <Alert variant="warning">
          <AlertTitle>{t("analysis.characters.lockedTitle")}</AlertTitle>
          <AlertDescription>
            {t("analysis.characters.lockedDescription")}
          </AlertDescription>
          <AlertAction>
            <Button
              render={
                <Link to={analysisStepPath(projectId, "understanding")} />
              }
              size="sm"
              variant="outline"
            >
              {t("analysis.backToUnderstanding")}
            </Button>
          </AlertAction>
        </Alert>
      ) : characters ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("analysis.characters.cardTitle")}</CardTitle>
            <CardDescription>
              {t("analysis.characters.cardDescription")}
            </CardDescription>
          </CardHeader>
          <CardPanel className="flex items-center justify-between gap-4">
            <span className="text-muted-foreground text-sm">
              {t("analysis.currentStatus")}
            </span>
            <Badge variant={status === "confirmed" ? "success" : "secondary"}>
              {t(`analysis.status.${status}`)}
            </Badge>
          </CardPanel>
        </Card>
      ) : (
        <Empty className="rounded-lg border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <UsersIcon aria-hidden className="size-4" />
            </EmptyMedia>
            <EmptyTitle>{t("analysis.characters.emptyTitle")}</EmptyTitle>
            <EmptyDescription>
              {t("analysis.characters.emptyDescription")}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}
    </section>
  );
}
