import { BookOpenIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/analysis-understanding";
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
import { Badge } from "~/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "~/components/ui/alert";
import { api } from "~/lib/api/client";
import { ApiError } from "~/lib/api/types";

async function getOrNull<T>(request: Promise<T>): Promise<T | null> {
  try {
    return await request;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const [understanding, source] = await Promise.all([
    getOrNull(api.understanding.get(params.projectId)),
    api.source.get(params.projectId),
  ]);
  return { understanding, threshold: source.threshold };
}

export default function AnalysisUnderstanding({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const { understanding, threshold } = loaderData;
  const status = understanding?.state ?? "empty";

  return (
    <section className="space-y-4">
      <div>
        <div className="mb-2 text-sm font-medium text-muted-foreground">
          {t("analysis.stepOf", { current: 1, total: 3 })}
        </div>
        <h2 className="app-heading text-2xl">
          {t("analysis.understanding.title")}
        </h2>
        <p className="mt-2 max-w-3xl text-muted-foreground text-sm">
          {t("analysis.understanding.description")}
        </p>
      </div>

      {!threshold.passed ? (
        <Alert variant="warning">
          <AlertTitle>{t("analysis.understanding.thresholdTitle")}</AlertTitle>
          <AlertDescription>
            {t("analysis.understanding.thresholdDescription", {
              min: threshold.min_chapters,
            })}
          </AlertDescription>
        </Alert>
      ) : null}

      {understanding ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("analysis.understanding.cardTitle")}</CardTitle>
            <CardDescription>
              {t("analysis.understanding.cardDescription")}
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
              <BookOpenIcon aria-hidden className="size-4" />
            </EmptyMedia>
            <EmptyTitle>{t("analysis.understanding.emptyTitle")}</EmptyTitle>
            <EmptyDescription>
              {t("analysis.understanding.emptyDescription")}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}
    </section>
  );
}
