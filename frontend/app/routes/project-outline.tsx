import {
  CheckCircleIcon,
  ChevronDownIcon,
  ListTreeIcon,
  RefreshCwIcon,
  SparklesIcon,
} from "lucide-react";
import type * as React from "react";
import { useMemo, useState } from "react";
import { Link, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/project-outline";
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
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { Separator } from "~/components/ui/separator";
import { toastManager } from "~/components/ui/toast";
import { api } from "~/lib/api/client";
import {
  ApiError,
  type ArtifactEnvelope,
  type IntExt,
  type OutlineData,
  type OutlineScene,
  type ProjectId,
  type Source,
  type SourceRef,
  type TimeOfDay,
} from "~/lib/api/types";
import { analysisStepPath, stagePath } from "~/lib/stages";

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

function formatParagraphs(paragraphs: number[]): string {
  if (paragraphs.length === 0) return "";
  const sorted = [...paragraphs].sort((a, b) => a - b);
  const ranges: string[] = [];
  let start = sorted[0];
  let previous = sorted[0];

  for (const paragraph of sorted.slice(1)) {
    if (paragraph === previous + 1) {
      previous = paragraph;
      continue;
    }
    ranges.push(start === previous ? String(start) : `${start}-${previous}`);
    start = paragraph;
    previous = paragraph;
  }

  ranges.push(start === previous ? String(start) : `${start}-${previous}`);
  return ranges.join(", ");
}

function formatSourceRef(sourceRef: SourceRef, template: string): string {
  return template
    .replace("{{chapter}}", String(sourceRef.chapter))
    .replace("{{paragraphs}}", formatParagraphs(sourceRef.paragraphs));
}

function sceneTitle(scene: OutlineScene): string {
  const firstSentence =
    scene.synopsis
      .split(/[。！？.!?]/)
      .map((part) => part.trim())
      .find(Boolean) ?? scene.synopsis;
  return `${scene.heading.location} · ${firstSentence}`;
}

function statusVariant(
  state: ArtifactEnvelope<OutlineData>["state"] | "empty",
): "default" | "secondary" | "success" | "warning" {
  if (state === "confirmed") return "success";
  if (state === "draft") return "warning";
  if (state === "needs_recompute") return "warning";
  return "secondary";
}

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const projectId = params.projectId as ProjectId;
  const [outline, characters, source] = await Promise.all([
    getOrNull(api.outline.get(projectId)),
    getOrNull(api.characters.get(projectId)),
    api.source.get(projectId),
  ]);
  return { characters, outline, projectId, source };
}

export default function ProjectOutline({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const revalidator = useRevalidator();
  const { characters, outline, projectId, source } = loaderData;
  const [working, setWorking] = useState(false);
  const characterNameById = useMemo(() => {
    const entries =
      characters?.data.characters.map(
        (character) => [character.id, character.name] as const,
      ) ?? [];
    return new Map(entries);
  }, [characters]);
  const characterConfirmed = characters?.state === "confirmed";
  const status = outline?.state ?? "empty";
  const scenes = outline?.data.scenes ?? [];

  async function refresh(): Promise<void> {
    await revalidator.revalidate();
  }

  async function generateOutline(): Promise<void> {
    try {
      setWorking(true);
      await api.outline.generate(projectId);
      toastManager.add({
        title: t("outline.generateSuccess"),
        type: "success",
      });
      await refresh();
    } catch (error) {
      toastManager.add({
        description:
          error instanceof ApiError && error.code === "state_gate_blocked"
            ? t("outline.gateBlocked")
            : getErrorMessage(error),
        title: t("outline.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function confirmOutline(): Promise<void> {
    try {
      setWorking(true);
      await api.outline.confirm(projectId);
      toastManager.add({
        title: t("outline.confirmSuccess"),
        type: "success",
      });
      await refresh();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("outline.actionError"),
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
            {t("pages.outline.milestone")}
          </div>
          <h2 className="app-heading text-2xl">{t("pages.outline.title")}</h2>
          <p className="mt-2 max-w-3xl text-muted-foreground text-sm">
            {t("pages.outline.description")}
          </p>
        </div>
        <Badge variant={statusVariant(status)}>
          {t(`outline.status.${status}`)}
        </Badge>
      </div>

      {!characterConfirmed ? (
        <Alert variant="warning">
          <AlertTitle>{t("outline.lockedTitle")}</AlertTitle>
          <AlertDescription>{t("outline.lockedDescription")}</AlertDescription>
          <AlertAction>
            <Button
              render={<Link to={analysisStepPath(projectId, "characters")} />}
              size="sm"
              variant="outline"
            >
              {t("outline.charactersCta")}
            </Button>
          </AlertAction>
        </Alert>
      ) : null}

      {characterConfirmed && !outline ? (
        <Empty className="rounded-xl border bg-card">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <ListTreeIcon />
            </EmptyMedia>
            <EmptyTitle>{t("outline.emptyTitle")}</EmptyTitle>
            <EmptyDescription>{t("outline.emptyDescription")}</EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button loading={working} onClick={generateOutline}>
              <SparklesIcon />
              {t("outline.generate")}
            </Button>
          </EmptyContent>
        </Empty>
      ) : null}

      {outline ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>{t("outline.cardTitle")}</CardTitle>
              <CardDescription>
                {t("outline.cardDescription", { count: scenes.length })}
              </CardDescription>
              <CardAction className="flex flex-wrap gap-2">
                <AlertDialog>
                  <AlertDialogTrigger
                    render={
                      <Button disabled={working} size="sm" variant="outline" />
                    }
                  >
                    <RefreshCwIcon />
                    {t("outline.regenerate")}
                  </AlertDialogTrigger>
                  <AlertDialogPopup>
                    <AlertDialogHeader>
                      <AlertDialogTitle>
                        {t("outline.regenerateTitle")}
                      </AlertDialogTitle>
                      <AlertDialogDescription>
                        {t("outline.regenerateDescription")}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogClose render={<Button variant="ghost" />}>
                        {t("outline.cancel")}
                      </AlertDialogClose>
                      <AlertDialogClose
                        render={
                          <Button
                            loading={working}
                            onClick={generateOutline}
                            variant="destructive"
                          />
                        }
                      >
                        {t("outline.regenerateConfirm")}
                      </AlertDialogClose>
                    </AlertDialogFooter>
                  </AlertDialogPopup>
                </AlertDialog>
                {outline.state === "draft" ? (
                  <Button loading={working} onClick={confirmOutline} size="sm">
                    <CheckCircleIcon />
                    {t("outline.confirm")}
                  </Button>
                ) : (
                  <Button
                    render={<Link to={stagePath(projectId, "script")} />}
                    size="sm"
                  >
                    {t("outline.scriptCta")}
                  </Button>
                )}
              </CardAction>
            </CardHeader>
            <CardPanel>
              {outline.state === "draft" ? (
                <Alert className="mb-4" variant="info">
                  <AlertTitle>{t("outline.needsConfirmTitle")}</AlertTitle>
                  <AlertDescription>
                    {t("outline.needsConfirmDescription")}
                  </AlertDescription>
                </Alert>
              ) : null}
              <div className="grid gap-4">
                {scenes.map((scene, index) => (
                  <OutlineSceneCard
                    characterNameById={characterNameById}
                    index={index}
                    key={scene.id}
                    scene={scene}
                    source={source}
                  />
                ))}
              </div>
            </CardPanel>
          </Card>

          {outline.state === "confirmed" ? (
            <Alert variant="success">
              <AlertTitle>{t("outline.confirmedTitle")}</AlertTitle>
              <AlertDescription>
                {t("outline.confirmedDescription")}
              </AlertDescription>
              <AlertAction>
                <Button
                  render={<Link to={stagePath(projectId, "script")} />}
                  size="sm"
                >
                  {t("outline.scriptCta")}
                </Button>
              </AlertAction>
            </Alert>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function OutlineSceneCard({
  characterNameById,
  index,
  scene,
  source,
}: {
  characterNameById: Map<string, string>;
  index: number;
  scene: OutlineScene;
  source: Source;
}): React.ReactElement {
  const { t } = useTranslation();
  const chapter = source.chapters.find(
    (item) => item.order === scene.source_ref.chapter,
  );
  const sourceLabel = formatSourceRef(scene.source_ref, t("outline.sourceRef"));
  const detailRows = [
    ["synopsis", scene.synopsis],
    ["goal", scene.goal],
    ["conflict", scene.conflict],
    ["mood", scene.mood],
    ["ending_state", scene.ending_state],
  ].filter(([, value]) => value);

  return (
    <Card className="rounded-lg shadow-none">
      <CardHeader className="gap-3">
        <CardTitle className="text-base">
          {t("outline.sceneNumber", { number: index + 1 })} ·{" "}
          {sceneTitle(scene)}
        </CardTitle>
        <CardDescription>
          {chapter
            ? t("outline.chapterHint", {
                paragraphs: chapter.paragraphs.length,
                title: chapter.title,
              })
            : t("outline.chapterMissing")}
        </CardDescription>
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">
            {t(`outline.int_ext.${scene.heading.int_ext as IntExt}`)}
          </Badge>
          <Badge variant="outline">
            {t(`outline.time.${scene.heading.time as TimeOfDay}`)}
          </Badge>
          <Badge variant="info">{sourceLabel}</Badge>
        </div>
      </CardHeader>
      <CardPanel className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          {detailRows.map(([key, value]) => (
            <div className="rounded-lg border bg-muted/32 p-3" key={key}>
              <div className="text-muted-foreground text-xs">
                {t(`outline.fields.${key}`)}
              </div>
              <div className="mt-1 text-sm">{value}</div>
            </div>
          ))}
        </div>

        <Separator />

        <div className="grid gap-4 md:grid-cols-2">
          <TokenGroup
            empty={t("outline.emptyField")}
            label={t("outline.fields.characters")}
            values={scene.characters.map(
              (id) => characterNameById.get(id) ?? id,
            )}
          />
          <TokenGroup
            empty={t("outline.emptyField")}
            label={t("outline.fields.foreshadowing")}
            values={scene.foreshadowing}
          />
        </div>

        <Collapsible>
          <CollapsibleTrigger
            className="inline-flex items-center gap-1 text-muted-foreground text-sm hover:text-foreground"
            type="button"
          >
            <ChevronDownIcon className="size-4" />
            {t("outline.relationChangesToggle", {
              count: scene.relation_changes.length,
            })}
          </CollapsibleTrigger>
          <CollapsiblePanel>
            <div className="space-y-2 pt-3">
              {scene.relation_changes.length > 0 ? (
                scene.relation_changes.map((change, changeIndex) => (
                  <div
                    className="rounded-lg border bg-muted/32 p-3 text-sm"
                    key={`${scene.id}-relation-${changeIndex}`}
                  >
                    <span className="font-medium">
                      {change.characters
                        .map((id) => characterNameById.get(id) ?? id)
                        .join(t("outline.characterSeparator"))}
                    </span>
                    {t("outline.relationChangeSeparator")}
                    {change.change}
                  </div>
                ))
              ) : (
                <div className="text-muted-foreground text-sm">
                  {t("outline.noRelationChanges")}
                </div>
              )}
            </div>
          </CollapsiblePanel>
        </Collapsible>
      </CardPanel>
    </Card>
  );
}

function TokenGroup({
  empty,
  label,
  values,
}: {
  empty: string;
  label: string;
  values: string[];
}): React.ReactElement {
  return (
    <div>
      <div className="mb-2 text-muted-foreground text-xs">{label}</div>
      <div className="flex flex-wrap gap-2">
        {values.length > 0 ? (
          values.map((value) => (
            <Badge key={value} variant="secondary">
              {value}
            </Badge>
          ))
        ) : (
          <span className="text-muted-foreground text-sm">{empty}</span>
        )}
      </div>
    </div>
  );
}
