import {
  BookOpenIcon,
  CheckCircleIcon,
  ChevronDownIcon,
  RefreshCwIcon,
  SaveIcon,
  SparklesIcon,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/analysis-understanding";
import { StringListEditor } from "~/components/string-list-editor";
import {
  Alert,
  AlertAction,
  AlertDescription,
  AlertTitle,
} from "~/components/ui/alert";
import {
  AlertDialog,
  AlertDialogClose,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogPopup,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "~/components/ui/alert-dialog";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardAction,
  CardDescription,
  CardHeader,
  CardPanel,
  CardTitle,
} from "~/components/ui/card";
import {
  Collapsible,
  CollapsiblePanel,
  CollapsibleTrigger,
} from "~/components/ui/collapsible";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { Field, FieldLabel } from "~/components/ui/field";
import { Input } from "~/components/ui/input";
import { Separator } from "~/components/ui/separator";
import { Textarea } from "~/components/ui/textarea";
import { toastManager } from "~/components/ui/toast";
import { api } from "~/lib/api/client";
import {
  ApiError,
  type ProjectId,
  type SourceRef,
  type UnderstandingData,
} from "~/lib/api/types";
import { analysisStepPath, stagePath } from "~/lib/stages";
import { cn } from "~/lib/utils";

type EditableTextField =
  | "logline"
  | "protagonist_goal"
  | "protagonist_fear"
  | "central_conflict"
  | "mood"
  | "style_fingerprint";

async function getOrNull<T>(request: Promise<T>): Promise<T | null> {
  try {
    return await request;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

function formatSourceRef(sourceRef: SourceRef): string {
  const paragraphs = sourceRef.paragraphs.join(", ");
  return `ch${sourceRef.chapter}.p${paragraphs}`;
}

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const projectId = params.projectId as ProjectId;
  const [understanding, source] = await Promise.all([
    getOrNull(api.understanding.get(projectId)),
    api.source.get(projectId),
  ]);
  return { understanding, threshold: source.threshold };
}

export default function AnalysisUnderstanding({
  loaderData,
  params,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const revalidator = useRevalidator();
  const projectId = params.projectId as ProjectId;
  const { understanding, threshold } = loaderData;
  const [draft, setDraft] = useState<UnderstandingData | null>(
    understanding?.data ?? null,
  );
  const [working, setWorking] = useState(false);

  const status = understanding?.state ?? "empty";
  const isConfirmed = status === "confirmed";
  const hasUnderstanding = Boolean(understanding && draft);
  const isDirty =
    Boolean(draft) &&
    JSON.stringify(draft) !== JSON.stringify(understanding?.data);
  const hasEditedConfirmedArtifact = isConfirmed
    ? JSON.stringify(draft) !== JSON.stringify(understanding?.data)
    : false;
  const canSave = Boolean(draft && isDirty);

  const editableFields = useMemo<
    Array<{ key: EditableTextField; label: string; placeholder: string }>
  >(
    () => [
      {
        key: "logline",
        label: t("analysis.understanding.fields.logline"),
        placeholder: t("analysis.understanding.placeholders.logline"),
      },
      {
        key: "protagonist_goal",
        label: t("analysis.understanding.fields.protagonist_goal"),
        placeholder: t("analysis.understanding.placeholders.protagonist_goal"),
      },
      {
        key: "protagonist_fear",
        label: t("analysis.understanding.fields.protagonist_fear"),
        placeholder: t("analysis.understanding.placeholders.protagonist_fear"),
      },
      {
        key: "central_conflict",
        label: t("analysis.understanding.fields.central_conflict"),
        placeholder: t("analysis.understanding.placeholders.central_conflict"),
      },
      {
        key: "mood",
        label: t("analysis.understanding.fields.mood"),
        placeholder: t("analysis.understanding.placeholders.mood"),
      },
      {
        key: "style_fingerprint",
        label: t("analysis.understanding.fields.style_fingerprint"),
        placeholder: t("analysis.understanding.placeholders.style_fingerprint"),
      },
    ],
    [t],
  );

  async function refresh(): Promise<void> {
    await revalidator.revalidate();
  }

  async function generateUnderstanding(): Promise<void> {
    try {
      setWorking(true);
      const envelope = await api.understanding.generate(projectId);
      setDraft(envelope.data);
      toastManager.add({
        title: t("analysis.understanding.generateSuccess"),
        type: "success",
      });
      await refresh();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("analysis.understanding.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function saveUnderstanding(): Promise<void> {
    if (!draft) return;

    try {
      setWorking(true);
      const envelope = await api.understanding.update(projectId, {
        ...draft,
        narrative: understanding?.data.narrative ?? draft.narrative,
        non_visualizable:
          understanding?.data.non_visualizable ?? draft.non_visualizable,
      });
      setDraft(envelope.data);
      toastManager.add({
        title: t("analysis.understanding.saveSuccess"),
        type: "success",
      });
      await refresh();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("analysis.understanding.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function confirmUnderstanding(): Promise<void> {
    try {
      setWorking(true);
      await api.understanding.confirm(projectId);
      toastManager.add({
        title: t("analysis.understanding.confirmSuccess"),
        type: "success",
      });
      await refresh();
      await navigate(analysisStepPath(projectId, "characters"));
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("analysis.understanding.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  function updateField(key: EditableTextField, value: string): void {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
  }

  function updateArray(
    key: "themes" | "strengths" | "difficulties",
    values: string[],
  ): void {
    setDraft((current) => (current ? { ...current, [key]: values } : current));
  }

  return (
    <section className="space-y-4">
      {!threshold.passed && hasUnderstanding ? (
        <Alert variant="warning">
          <AlertTitle>{t("analysis.understanding.thresholdTitle")}</AlertTitle>
          <AlertDescription>
            {t("analysis.understanding.thresholdDescription", {
              min: threshold.min_chapters,
            })}
          </AlertDescription>
          <AlertAction>
            <Button
              render={<Link to={stagePath(projectId, "import")} />}
              size="sm"
              variant="outline"
            >
              {t("analysis.understanding.importLink")}
            </Button>
          </AlertAction>
        </Alert>
      ) : null}

      {hasEditedConfirmedArtifact ? (
        <Alert variant="warning">
          <AlertTitle>{t("analysis.understanding.reconfirmTitle")}</AlertTitle>
          <AlertDescription>
            {t("analysis.understanding.reconfirmDescription")}
          </AlertDescription>
        </Alert>
      ) : null}

      {!understanding || !draft ? (
        <section className="flex min-h-[calc(100dvh-11rem)] items-center justify-center overflow-hidden">
          <Empty className="w-full max-w-xl">
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <BookOpenIcon aria-hidden className="size-4" />
              </EmptyMedia>
              <EmptyTitle>{t("analysis.understanding.emptyTitle")}</EmptyTitle>
              <EmptyDescription
                className={cn(!threshold.passed && "text-warning")}
              >
                {threshold.passed
                  ? t("analysis.understanding.emptyDescription")
                  : t("analysis.understanding.thresholdDescription", {
                      min: threshold.min_chapters,
                    })}
              </EmptyDescription>
            </EmptyHeader>
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Button
                disabled={!threshold.passed}
                loading={working}
                onClick={generateUnderstanding}
              >
                <SparklesIcon aria-hidden />
                {t("analysis.understanding.generate")}
              </Button>
              {!threshold.passed ? (
                <Button
                  render={<Link to={stagePath(projectId, "import")} />}
                  variant="outline"
                >
                  {t("analysis.understanding.importLink")}
                </Button>
              ) : null}
            </div>
          </Empty>
        </section>
      ) : (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t("analysis.understanding.cardTitle")}</CardTitle>
              <CardDescription>
                {t("analysis.understanding.cardDescription")}
              </CardDescription>
              <CardAction className="flex flex-wrap justify-end gap-2">
                <AlertDialog>
                  <AlertDialogTrigger render={<Button variant="outline" />}>
                    <RefreshCwIcon aria-hidden />
                    {t("analysis.understanding.regenerate")}
                  </AlertDialogTrigger>
                  <AlertDialogPopup>
                    <AlertDialogHeader>
                      <AlertDialogTitle>
                        {t("analysis.understanding.regenerateTitle")}
                      </AlertDialogTitle>
                      <AlertDialogDescription>
                        {t("analysis.understanding.regenerateDescription")}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogClose
                        render={<Button type="button" variant="ghost" />}
                      >
                        {t("analysis.understanding.cancel")}
                      </AlertDialogClose>
                      <AlertDialogClose
                        render={
                          <Button
                            loading={working}
                            onClick={generateUnderstanding}
                            type="button"
                          />
                        }
                      >
                        {t("analysis.understanding.regenerateConfirm")}
                      </AlertDialogClose>
                    </AlertDialogFooter>
                  </AlertDialogPopup>
                </AlertDialog>
                <Button
                  disabled={!canSave}
                  loading={working}
                  onClick={saveUnderstanding}
                  variant="secondary"
                >
                  <SaveIcon aria-hidden />
                  {t("analysis.understanding.save")}
                </Button>
                <Button
                  disabled={isDirty}
                  loading={working}
                  onClick={confirmUnderstanding}
                  title={
                    isDirty
                      ? t("analysis.understanding.saveBeforeConfirm")
                      : undefined
                  }
                >
                  <CheckCircleIcon aria-hidden />
                  {t("analysis.understanding.confirm")}
                </Button>
              </CardAction>
            </CardHeader>
            <CardPanel className="space-y-5">
              <div className="grid gap-4 lg:grid-cols-2">
                {editableFields.map((field) => (
                  <Field className="w-full" key={field.key}>
                    <FieldLabel>{field.label}</FieldLabel>
                    <Input
                      onChange={(event) =>
                        updateField(field.key, event.target.value)
                      }
                      placeholder={field.placeholder}
                      value={draft[field.key]}
                    />
                  </Field>
                ))}
              </div>

              <Field className="w-full">
                <FieldLabel>
                  {t("analysis.understanding.fields.synopsis")}
                </FieldLabel>
                <Textarea
                  onChange={(event) =>
                    setDraft((current) =>
                      current
                        ? { ...current, synopsis: event.target.value }
                        : current,
                    )
                  }
                  placeholder={t(
                    "analysis.understanding.placeholders.synopsis",
                  )}
                  value={draft.synopsis}
                />
              </Field>

              <div className="grid gap-4 lg:grid-cols-3">
                <StringListEditor
                  label={t("analysis.understanding.fields.themes")}
                  onChange={(values) => updateArray("themes", values)}
                  placeholder={t("analysis.understanding.addPlaceholder")}
                  values={draft.themes}
                />
                <StringListEditor
                  label={t("analysis.understanding.fields.strengths")}
                  onChange={(values) => updateArray("strengths", values)}
                  placeholder={t("analysis.understanding.addPlaceholder")}
                  values={draft.strengths}
                />
                <StringListEditor
                  label={t("analysis.understanding.fields.difficulties")}
                  onChange={(values) => updateArray("difficulties", values)}
                  placeholder={t("analysis.understanding.addPlaceholder")}
                  values={draft.difficulties}
                />
              </div>
            </CardPanel>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("analysis.understanding.trustTitle")}</CardTitle>
              <CardDescription>
                {t("analysis.understanding.trustDescription")}
              </CardDescription>
            </CardHeader>
            <CardPanel className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge variant="info">
                  {t("analysis.understanding.narrative.perspective", {
                    value: draft.narrative.perspective,
                  })}
                </Badge>
                <Badge variant="info">
                  {t("analysis.understanding.narrative.tense", {
                    value: draft.narrative.tense,
                  })}
                </Badge>
                <Badge
                  variant={draft.narrative.unreliable ? "warning" : "secondary"}
                >
                  {draft.narrative.unreliable
                    ? t("analysis.understanding.narrative.unreliable")
                    : t("analysis.understanding.narrative.reliable")}
                </Badge>
              </div>

              <Separator />

              <Collapsible>
                <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left font-medium text-sm hover:bg-accent/50">
                  <span>
                    {t("analysis.understanding.nonVisualizableTitle")}
                  </span>
                  <span className="flex items-center gap-2 text-muted-foreground">
                    {t("analysis.understanding.nonVisualizableCount", {
                      count: draft.non_visualizable.length,
                    })}
                    <ChevronDownIcon aria-hidden className="size-4" />
                  </span>
                </CollapsibleTrigger>
                <CollapsiblePanel>
                  <div className="space-y-2 pt-3">
                    {draft.non_visualizable.length > 0 ? (
                      draft.non_visualizable.map((mark, index) => (
                        <div
                          className="rounded-lg border bg-muted/30 p-3"
                          key={`${mark.note}-${index}`}
                        >
                          <div className="mb-1 text-muted-foreground text-xs">
                            {formatSourceRef(mark.source_ref)}
                          </div>
                          <p className="text-sm">{mark.note}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-muted-foreground text-sm">
                        {t("analysis.understanding.nonVisualizableEmpty")}
                      </p>
                    )}
                  </div>
                </CollapsiblePanel>
              </Collapsible>
            </CardPanel>
          </Card>
        </div>
      )}
    </section>
  );
}
