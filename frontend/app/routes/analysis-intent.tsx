import {
  CheckCircleIcon,
  ClipboardCheckIcon,
  GitPullRequestArrowIcon,
  SlidersHorizontalIcon,
} from "lucide-react";
import type * as React from "react";
import { useState } from "react";
import { Link, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/analysis-intent";
import { StringListEditor } from "~/components/string-list-editor";
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
  CardAction,
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
import { Field, FieldDescription, FieldLabel } from "~/components/ui/field";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Radio, RadioGroup } from "~/components/ui/radio-group";
import { Separator } from "~/components/ui/separator";
import { Switch } from "~/components/ui/switch";
import { toastManager } from "~/components/ui/toast";
import { api } from "~/lib/api/client";
import {
  ApiError,
  type ArtifactEnvelope,
  type IntentConflict,
  type IntentConstraints,
  type MvpDirection,
  type ProjectId,
} from "~/lib/api/types";
import { analysisStepPath, stagePath } from "~/lib/stages";

const mvpDirections: MvpDirection[] = ["faithful", "cinematic", "short_drama"];

type IntentFormState = IntentConstraints;

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

function isMvpDirection(value: unknown): value is MvpDirection {
  return mvpDirections.includes(value as MvpDirection);
}

function emptyIntentForm(direction: MvpDirection | null): IntentFormState {
  return {
    allow_new_ending: false,
    allow_new_plot: false,
    allow_reorder: false,
    keep: [],
    mood_floor: null,
    must_keep_lines: [],
    no_delete: [],
    no_merge: [],
    target_type: direction,
  };
}

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const projectId = params.projectId as ProjectId;
  const [intent, characters, project] = await Promise.all([
    getOrNull(api.intent.get(projectId)),
    getOrNull(api.characters.get(projectId)),
    api.projects.get(projectId),
  ]);
  return { characters, intent, project, projectId };
}

export default function AnalysisIntent({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const revalidator = useRevalidator();
  const { characters, intent, project, projectId } = loaderData;
  const initialDirection = isMvpDirection(project.meta.adaptation_direction)
    ? project.meta.adaptation_direction
    : null;
  const [direction, setDirection] = useState<MvpDirection | null>(
    initialDirection,
  );
  const [savedIntent, setSavedIntent] =
    useState<ArtifactEnvelope<IntentConstraints> | null>(intent);
  const [form, setForm] = useState<IntentFormState>(
    intent?.data ?? emptyIntentForm(initialDirection),
  );
  const [conflicts, setConflicts] = useState<IntentConflict[] | null>(null);
  const [working, setWorking] = useState(false);
  const locked = characters?.state !== "confirmed";
  const status = savedIntent ? savedIntent.state : "empty";
  const canValidate = Boolean(savedIntent && direction);

  function updateList(
    key: keyof Pick<
      IntentFormState,
      "keep" | "no_delete" | "no_merge" | "must_keep_lines"
    >,
    values: string[],
  ): void {
    setForm((current) => ({ ...current, [key]: values }));
  }

  function updateBoolean(
    key: keyof Pick<
      IntentFormState,
      "allow_new_plot" | "allow_reorder" | "allow_new_ending"
    >,
    value: boolean,
  ): void {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function refresh(): Promise<void> {
    await revalidator.revalidate();
  }

  async function validateConflicts(): Promise<IntentConflict[]> {
    const response = await api.intent.validate(projectId);
    setConflicts(response.conflicts);
    return response.conflicts;
  }

  async function saveIntent(): Promise<void> {
    try {
      setWorking(true);
      const payload: IntentConstraints = {
        ...form,
        mood_floor: form.mood_floor?.trim() || null,
        target_type: direction,
      };
      const envelope = await api.intent.save(projectId, payload);
      setForm(envelope.data);
      setSavedIntent(envelope);
      toastManager.add({
        title: t("analysis.intent.saveSuccess"),
        type: "success",
      });
      if (direction) {
        await validateConflicts();
      } else {
        setConflicts(null);
      }
      await refresh();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("analysis.intent.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function selectDirection(nextDirection: MvpDirection): Promise<void> {
    try {
      setWorking(true);
      const response = await api.intent.setDirection(projectId, nextDirection);
      setDirection(response.direction);
      toastManager.add({
        title: t("analysis.intent.selectDirectionSuccess"),
        type: "success",
      });
      if (savedIntent) {
        await validateConflicts();
      } else {
        setConflicts(null);
      }
      await refresh();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("analysis.intent.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function runValidation(): Promise<void> {
    if (!canValidate) return;

    try {
      setWorking(true);
      await validateConflicts();
      toastManager.add({
        title: t("analysis.intent.validateSuccess"),
        type: "success",
      });
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("analysis.intent.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="mb-2 text-sm font-medium text-muted-foreground">
            {t("analysis.stepOf", { current: 3, total: 3 })}
          </div>
          <h2 className="app-heading text-2xl">{t("analysis.intent.title")}</h2>
          <p className="mt-2 max-w-3xl text-muted-foreground text-sm">
            {t("analysis.intent.description")}
          </p>
        </div>
        <Badge variant={status === "confirmed" ? "success" : "secondary"}>
          {t(`analysis.status.${status}`)}
        </Badge>
      </div>

      {locked ? (
        <Alert variant="warning">
          <AlertTitle>{t("analysis.intent.lockedTitle")}</AlertTitle>
          <AlertDescription>
            {t("analysis.intent.lockedDescription")}
            <span className="mt-1 block">{t("analysis.intent.gateNote")}</span>
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
      ) : (
        <div className="space-y-4">
          {!savedIntent ? (
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
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>{t("analysis.intent.formTitle")}</CardTitle>
              <CardDescription>
                {t("analysis.intent.formDescription")}
              </CardDescription>
              <CardAction>
                <Button loading={working} onClick={saveIntent}>
                  <CheckCircleIcon aria-hidden />
                  {t("analysis.intent.save")}
                </Button>
              </CardAction>
            </CardHeader>
            <CardPanel className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <StringListEditor
                  description={t("analysis.intent.fieldDescriptions.keep")}
                  label={t("analysis.intent.fields.keep")}
                  onChange={(values) => updateList("keep", values)}
                  placeholder={t("analysis.intent.placeholders.keep")}
                  values={form.keep}
                />
                <StringListEditor
                  description={t("analysis.intent.fieldDescriptions.no_delete")}
                  label={t("analysis.intent.fields.no_delete")}
                  onChange={(values) => updateList("no_delete", values)}
                  placeholder={t("analysis.intent.placeholders.no_delete")}
                  values={form.no_delete}
                />
                <StringListEditor
                  description={t("analysis.intent.fieldDescriptions.no_merge")}
                  label={t("analysis.intent.fields.no_merge")}
                  onChange={(values) => updateList("no_merge", values)}
                  placeholder={t("analysis.intent.placeholders.no_merge")}
                  values={form.no_merge}
                />
                <StringListEditor
                  description={t(
                    "analysis.intent.fieldDescriptions.must_keep_lines",
                  )}
                  label={t("analysis.intent.fields.must_keep_lines")}
                  onChange={(values) => updateList("must_keep_lines", values)}
                  placeholder={t(
                    "analysis.intent.placeholders.must_keep_lines",
                  )}
                  values={form.must_keep_lines}
                />
              </div>
              <Field className="w-full">
                <FieldLabel>
                  {t("analysis.intent.fields.mood_floor")}
                </FieldLabel>
                <FieldDescription>
                  {t("analysis.intent.fieldDescriptions.mood_floor")}
                </FieldDescription>
                <Input
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      mood_floor: event.target.value,
                    }))
                  }
                  placeholder={t("analysis.intent.placeholders.mood_floor")}
                  type="text"
                  value={form.mood_floor ?? ""}
                />
              </Field>
              <Separator />
              <div className="grid gap-3 md:grid-cols-3">
                <IntentSwitch
                  checked={form.allow_new_plot}
                  description={t(
                    "analysis.intent.fieldDescriptions.allow_new_plot",
                  )}
                  id="allow-new-plot"
                  label={t("analysis.intent.fields.allow_new_plot")}
                  onCheckedChange={(value) =>
                    updateBoolean("allow_new_plot", value)
                  }
                />
                <IntentSwitch
                  checked={form.allow_reorder}
                  description={t(
                    "analysis.intent.fieldDescriptions.allow_reorder",
                  )}
                  id="allow-reorder"
                  label={t("analysis.intent.fields.allow_reorder")}
                  onCheckedChange={(value) =>
                    updateBoolean("allow_reorder", value)
                  }
                />
                <IntentSwitch
                  checked={form.allow_new_ending}
                  description={t(
                    "analysis.intent.fieldDescriptions.allow_new_ending",
                  )}
                  id="allow-new-ending"
                  label={t("analysis.intent.fields.allow_new_ending")}
                  onCheckedChange={(value) =>
                    updateBoolean("allow_new_ending", value)
                  }
                />
              </div>
            </CardPanel>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("analysis.intent.directionTitle")}</CardTitle>
              <CardDescription>
                {t("analysis.intent.directionDescription")}
              </CardDescription>
            </CardHeader>
            <CardPanel>
              <RadioGroup
                aria-label={t("analysis.intent.directionTitle")}
                onValueChange={(value) => {
                  if (isMvpDirection(value)) void selectDirection(value);
                }}
                value={direction ?? undefined}
              >
                {mvpDirections.map((item) => (
                  <Label
                    className="flex items-start gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/64 has-[[data-checked]]:border-primary has-[[data-checked]]:bg-primary/6"
                    key={item}
                  >
                    <Radio value={item} />
                    <span className="grid gap-1">
                      <span>
                        {t(`analysis.intent.directions.${item}.label`)}
                      </span>
                      <span className="font-normal text-muted-foreground text-sm">
                        {t(`analysis.intent.directions.${item}.description`)}
                      </span>
                    </span>
                  </Label>
                ))}
              </RadioGroup>
            </CardPanel>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("analysis.intent.validationTitle")}</CardTitle>
              <CardDescription>
                {t("analysis.intent.validationDescription")}
              </CardDescription>
              <CardAction>
                <Button
                  disabled={!canValidate}
                  loading={working}
                  onClick={runValidation}
                  variant="outline"
                >
                  <ClipboardCheckIcon aria-hidden />
                  {t("analysis.intent.validate")}
                </Button>
              </CardAction>
            </CardHeader>
            <CardPanel className="space-y-3">
              {!canValidate ? (
                <Alert variant="info">
                  <AlertTitle>{t("analysis.intent.validateFirst")}</AlertTitle>
                  <AlertDescription>
                    {t("analysis.intent.validationDescription")}
                  </AlertDescription>
                </Alert>
              ) : null}
              {conflicts ? (
                conflicts.length === 0 ? (
                  <Alert variant="success">
                    <AlertTitle>
                      {t("analysis.intent.noConflictsTitle")}
                    </AlertTitle>
                    <AlertDescription>
                      {t("analysis.intent.noConflictsDescription")}
                    </AlertDescription>
                  </Alert>
                ) : (
                  <div className="space-y-2">
                    {conflicts.map((conflict) => (
                      <Alert key={conflict.code} variant="warning">
                        <AlertTitle>
                          {t("analysis.intent.conflictTitle")}
                        </AlertTitle>
                        <AlertDescription>
                          <span className="block">
                            {t(`analysis.intent.conflicts.${conflict.code}`, {
                              defaultValue:
                                conflict.message ||
                                t("analysis.intent.conflicts.unknown"),
                            })}
                          </span>
                          <span className="mt-1 block">
                            {t("analysis.intent.conflictDescription")}
                          </span>
                        </AlertDescription>
                      </Alert>
                    ))}
                  </div>
                )
              ) : null}
            </CardPanel>
          </Card>

          {savedIntent ? (
            <Alert variant="success">
              <AlertTitle>{t("analysis.intent.completeTitle")}</AlertTitle>
              <AlertDescription>
                {t("analysis.intent.completeDescription")}
              </AlertDescription>
              <AlertAction>
                <Button
                  render={<Link to={stagePath(projectId, "outline")} />}
                  size="sm"
                  variant="outline"
                >
                  <GitPullRequestArrowIcon aria-hidden />
                  {t("analysis.intent.outlineCta")}
                </Button>
              </AlertAction>
            </Alert>
          ) : null}
        </div>
      )}
    </section>
  );
}

function IntentSwitch({
  checked,
  description,
  id,
  label,
  onCheckedChange,
}: {
  checked: boolean;
  description: string;
  id: string;
  label: string;
  onCheckedChange: (checked: boolean) => void;
}): React.ReactElement {
  return (
    <div className="flex items-start justify-between gap-4 rounded-lg border p-3">
      <div className="grid gap-1">
        <Label htmlFor={id}>{label}</Label>
        <p className="text-muted-foreground text-sm">{description}</p>
      </div>
      <Switch checked={checked} id={id} onCheckedChange={onCheckedChange} />
    </div>
  );
}
