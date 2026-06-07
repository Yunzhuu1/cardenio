import {
  CheckCircleIcon,
  GitMergeIcon,
  ListTreeIcon,
  PlusIcon,
  RefreshCwIcon,
  SparklesIcon,
} from "lucide-react";
import type * as React from "react";
import { useMemo, useState } from "react";
import { Link, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import {
  createBlankScene,
  OutlineSceneCard,
  SceneDialog,
  type SceneFormState,
} from "~/components/outline-scene-editor";
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
import { Dialog, DialogTrigger } from "~/components/ui/dialog";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { toastManager } from "~/components/ui/toast";
import { api } from "~/lib/api/client";
import { api as loaderApi } from "~/lib/api/client";
import {
  ApiError,
  type MergeSuggestion,
  type OutlineScene,
  type ProjectId,
} from "~/lib/api/types";
import { analysisStepPath } from "~/lib/stages";

async function getOrNull<T>(request: Promise<T>): Promise<T | null> {
  try {
    return await request;
  } catch (error) {
    if (
      typeof error === "object" &&
      error !== null &&
      "status" in error &&
      error["status"] === 404
    ) {
      return null;
    }
    throw error;
  }
}

export async function clientLoader(args: Route.ClientLoaderArgs) {
  const projectId = args.params.projectId as ProjectId;
  const [outline, characters, source] = await Promise.all([
    getOrNull(loaderApi.outline.get(projectId)),
    getOrNull(loaderApi.characters.get(projectId)),
    loaderApi.source.get(projectId),
  ]);
  const mergeSuggestions = outline
    ? await getOrNull(loaderApi.outline.getMergeSuggestions(projectId))
    : null;

  return { characters, mergeSuggestions, outline, projectId, source };
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

function nullableText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function isInvalidSourceRefError(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    (error.message.includes("invalid_source_ref") ||
      error.message.includes("missing_paragraphs"))
  );
}

function outlineSceneTitle(scene: OutlineScene): string {
  const firstSentence =
    scene.synopsis
      .split(/[。！？.!?]/)
      .map((part) => part.trim())
      .find(Boolean) ?? scene.synopsis;
  return `${scene.heading.location} · ${firstSentence}`;
}

function mergeStatusVariant(
  status: MergeSuggestion["status"],
): "secondary" | "success" | "warning" {
  if (status === "applied") return "success";
  if (status === "dismissed") return "secondary";
  return "warning";
}

export default function ProjectOutline({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const revalidator = useRevalidator();
  const { characters, mergeSuggestions, outline, projectId, source } =
    loaderData;
  const [working, setWorking] = useState(false);
  const [sceneForm, setSceneForm] = useState<SceneFormState | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<OutlineScene | null>(null);
  const characterNameById = useMemo(() => {
    const entries =
      characters?.data.characters.map(
        (character) => [character.id, character.name] as const,
      ) ?? [];
    return new Map(entries);
  }, [characters]);
  const characterList = characters?.data.characters ?? [];
  const characterConfirmed = characters?.state === "confirmed";
  const scenes = useMemo(() => outline?.data.scenes ?? [], [outline]);
  const suggestions = mergeSuggestions?.suggestions ?? [];
  const sceneById = useMemo(() => {
    return new Map(scenes.map((scene) => [scene.id, scene] as const));
  }, [scenes]);

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

  function openCreateScene(): void {
    setSceneForm({
      mode: "create",
      scene: createBlankScene({
        characters: characterList,
        scenes,
        source,
      }),
    });
  }

  function openEditScene(scene: OutlineScene): void {
    setSceneForm({
      mode: "edit",
      scene: {
        ...scene,
        characters: [...scene.characters],
        foreshadowing: [...scene.foreshadowing],
        relation_changes: scene.relation_changes.map((change) => ({
          characters: [...change.characters],
          change: change.change,
        })),
        source_ref: {
          chapter: scene.source_ref.chapter,
          paragraphs: [...scene.source_ref.paragraphs],
        },
      },
    });
  }

  function sceneWriteErrorDescription(error: unknown): string {
    if (isInvalidSourceRefError(error)) {
      return t("outline.edit.invalidSourceRef");
    }
    if (error instanceof ApiError && error.status === 409) {
      return t("outline.edit.sceneIdConflict");
    }
    return getErrorMessage(error);
  }

  async function saveScene(): Promise<void> {
    if (!sceneForm) return;
    const scene: OutlineScene = {
      ...sceneForm.scene,
      conflict: nullableText(sceneForm.scene.conflict ?? ""),
      ending_state: nullableText(sceneForm.scene.ending_state ?? ""),
      goal: nullableText(sceneForm.scene.goal ?? ""),
      heading: {
        ...sceneForm.scene.heading,
        location: sceneForm.scene.heading.location.trim(),
      },
      mood: nullableText(sceneForm.scene.mood ?? ""),
      relation_changes: sceneForm.scene.relation_changes
        .map((change) => ({
          characters: change.characters,
          change: change.change.trim(),
        }))
        .filter((change) => change.characters.length > 0 && change.change),
      source_ref: {
        chapter: sceneForm.scene.source_ref.chapter,
        paragraphs: [...sceneForm.scene.source_ref.paragraphs].sort(
          (a, b) => a - b,
        ),
      },
      synopsis: sceneForm.scene.synopsis.trim(),
    };

    if (!scene.synopsis || !scene.heading.location) {
      toastManager.add({
        description: t("outline.edit.requiredFields"),
        title: t("outline.actionError"),
        type: "error",
      });
      return;
    }

    if (scene.source_ref.paragraphs.length === 0) {
      toastManager.add({
        description: t("outline.edit.invalidSourceRef"),
        title: t("outline.actionError"),
        type: "error",
      });
      return;
    }

    try {
      setWorking(true);
      if (sceneForm.mode === "create") {
        await api.outline.addScene(projectId, scene);
      } else {
        await api.outline.updateScene(projectId, scene.id, scene);
      }
      toastManager.add({
        description: t("outline.edit.draftNotice"),
        title:
          sceneForm.mode === "create"
            ? t("outline.edit.createSuccess")
            : t("outline.edit.updateSuccess"),
        type: "success",
      });
      setSceneForm(null);
      await refresh();
    } catch (error) {
      toastManager.add({
        description: sceneWriteErrorDescription(error),
        title: t("outline.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function deleteScene(): Promise<void> {
    if (!deleteTarget) return;
    try {
      setWorking(true);
      await api.outline.deleteScene(projectId, deleteTarget.id);
      toastManager.add({
        description: t("outline.edit.draftNotice"),
        title: t("outline.edit.deleteSuccess"),
        type: "success",
      });
      setDeleteTarget(null);
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

  async function moveScene(
    scenePosition: number,
    direction: -1 | 1,
  ): Promise<void> {
    const targetIndex = scenePosition + direction;
    if (targetIndex < 0 || targetIndex >= scenes.length) return;
    const order = scenes.map((scene) => scene.id);
    const currentSceneId = order[scenePosition];
    order[scenePosition] = order[targetIndex];
    order[targetIndex] = currentSceneId;

    try {
      setWorking(true);
      await api.outline.reorder(projectId, order);
      toastManager.add({
        description: t("outline.edit.draftNotice"),
        title: t("outline.edit.reorderSuccess"),
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

  async function resolveMergeSuggestion(
    suggestion: MergeSuggestion,
    status: "applied" | "dismissed",
  ): Promise<void> {
    try {
      setWorking(true);
      if (status === "applied") {
        await api.outline.applyMergeSuggestion(projectId, suggestion.id);
      } else {
        await api.outline.dismissMergeSuggestion(projectId, suggestion.id);
      }
      toastManager.add({
        description: t("outline.merge.statusNotice"),
        title:
          status === "applied"
            ? t("outline.merge.applySuccess")
            : t("outline.merge.dismissSuccess"),
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
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 space-y-1">
              <h1 className="app-heading text-xl">{t("outline.cardTitle")}</h1>
              <p className="text-muted-foreground text-sm">
                {t("outline.cardDescription", { count: scenes.length })}
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <Dialog
                onOpenChange={(open) => {
                  if (!open) setSceneForm(null);
                }}
                open={Boolean(sceneForm)}
              >
                <DialogTrigger
                  render={
                    <Button
                      disabled={working}
                      onClick={openCreateScene}
                      size="sm"
                      variant="outline"
                    />
                  }
                >
                  <PlusIcon aria-hidden />
                  {t("outline.edit.addScene")}
                </DialogTrigger>
                {sceneForm ? (
                  <SceneDialog
                    characters={characterList}
                    form={sceneForm}
                    onFormChange={setSceneForm}
                    onSave={saveScene}
                    source={source}
                    working={working}
                  />
                ) : null}
              </Dialog>
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
              ) : null}
            </div>
          </div>

          <div className="divide-y">
            {scenes.map((scene, scenePosition) => (
              <OutlineSceneCard
                characterNameById={characterNameById}
                canMoveDown={scenePosition < scenes.length - 1}
                canMoveUp={scenePosition > 0}
                index={scenePosition}
                key={scene.id}
                onDelete={setDeleteTarget}
                onEdit={openEditScene}
                onMoveDown={() => moveScene(scenePosition, 1)}
                onMoveUp={() => moveScene(scenePosition, -1)}
                scene={scene}
                source={source}
                working={working}
              />
            ))}
          </div>

          <section className="space-y-4 border-t pt-6">
            <div className="space-y-1">
              <h2 className="flex items-center gap-2 font-medium text-base">
                <GitMergeIcon className="size-5" aria-hidden />
                {t("outline.merge.title")}
              </h2>
              <p className="text-muted-foreground text-sm">
                {t("outline.merge.description")}
              </p>
            </div>

            {suggestions.length > 0 ? (
              <div className="grid gap-3">
                {suggestions.map((suggestion) => (
                  <div
                    className="rounded-lg border bg-muted/24 p-4"
                    key={suggestion.id}
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          {suggestion.scene_ids.map((sceneId) => {
                            const scene = sceneById.get(sceneId);
                            return (
                              <Badge key={sceneId} variant="outline">
                                {scene
                                  ? outlineSceneTitle(scene)
                                  : t("outline.merge.missingScene", {
                                      id: sceneId,
                                    })}
                              </Badge>
                            );
                          })}
                        </div>
                        <p className="text-sm">{suggestion.reason}</p>
                      </div>
                      <Badge variant={mergeStatusVariant(suggestion.status)}>
                        {t(`outline.merge.status.${suggestion.status}`)}
                      </Badge>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        disabled={working || suggestion.status === "applied"}
                        onClick={() =>
                          resolveMergeSuggestion(suggestion, "applied")
                        }
                        size="sm"
                        type="button"
                        variant="outline"
                      >
                        {t("outline.merge.apply")}
                      </Button>
                      <Button
                        disabled={working || suggestion.status === "dismissed"}
                        onClick={() =>
                          resolveMergeSuggestion(suggestion, "dismissed")
                        }
                        size="sm"
                        type="button"
                        variant="ghost"
                      >
                        {t("outline.merge.dismiss")}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed p-6 text-center text-muted-foreground text-sm">
                {t("outline.merge.empty")}
              </div>
            )}
          </section>
        </>
      ) : null}

      <AlertDialog
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        open={Boolean(deleteTarget)}
      >
        <AlertDialogPopup>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("outline.edit.deleteTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("outline.edit.deleteDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogClose render={<Button type="button" variant="ghost" />}>
              {t("outline.cancel")}
            </AlertDialogClose>
            <AlertDialogClose
              render={
                <Button
                  loading={working}
                  onClick={deleteScene}
                  type="button"
                  variant="destructive"
                />
              }
            >
              {t("outline.edit.deleteConfirm")}
            </AlertDialogClose>
          </AlertDialogFooter>
        </AlertDialogPopup>
      </AlertDialog>
    </section>
  );
}
