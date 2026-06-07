import {
  ClapperboardIcon,
  ListFilterIcon,
  RefreshCwIcon,
  SparklesIcon,
} from "lucide-react";
import type * as React from "react";
import { useMemo, useState } from "react";
import { Link, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/project-script";
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
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { Label } from "~/components/ui/label";
import { Separator } from "~/components/ui/separator";
import { Switch } from "~/components/ui/switch";
import {
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupSeparator,
} from "~/components/ui/toggle-group";
import { toastManager } from "~/components/ui/toast";
import { BeatBadges, BeatBody } from "~/components/screenplay-beat-view";
import { SceneHeader, SceneSummary } from "~/components/screenplay-scene-view";
import { api } from "~/lib/api/client";
import { api as loaderApi } from "~/lib/api/client";
import {
  ApiError,
  type Beat,
  type BeatsFilterResponse,
  type Character,
  type Flag,
  type ProjectId,
  type ScreenplayScene,
} from "~/lib/api/types";
import {
  beatSummary,
  beatToneClass,
  sceneTitle,
  sourceRefLabel,
} from "~/lib/screenplay-format";
import { cn } from "~/lib/utils";
import { stagePath } from "~/lib/stages";

type BeatFilter = "all" | Flag;

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
  const requests = await Promise.all([
    getOrNull(loaderApi.screenplay.get(projectId)),
    getOrNull(loaderApi.outline.get(projectId)),
    getOrNull(loaderApi.characters.get(projectId)),
  ]);
  const aiInferredBeats = requests[0]
    ? await getOrNull(loaderApi.screenplay.getBeats(projectId, "ai_inferred"))
    : null;

  return {
    aiInferredBeats,
    characters: requests[2],
    outline: requests[1],
    projectId,
    screenplay: requests[0],
  };
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

function scrollToBeat(sceneId: string, beatIndex: number): void {
  const target =
    document.getElementById(`beat-${sceneId}-${beatIndex}`) ??
    document.getElementById(`scene-${sceneId}`);
  target?.scrollIntoView({ behavior: "smooth", block: "center" });
}

export default function ProjectScript({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const revalidator = useRevalidator();
  const { aiInferredBeats, characters, outline, projectId, screenplay } =
    loaderData;
  const [working, setWorking] = useState(false);
  const [refreshingAiList, setRefreshingAiList] = useState(false);
  const [filter, setFilter] = useState<BeatFilter>("all");
  const [aiListOverride, setAiListOverride] =
    useState<BeatsFilterResponse | null>(null);
  const [shotHints, setShotHints] = useState(
    screenplay?.data.shot_hints.enabled ?? false,
  );
  const outlineConfirmed = outline?.state === "confirmed";
  const scenes = useMemo(() => screenplay?.data.scenes ?? [], [screenplay]);
  const beatCount = scenes.reduce(
    (count, scene) => count + scene.beats.length,
    0,
  );
  const aiList = aiListOverride ?? aiInferredBeats;
  const sceneById = useMemo(() => {
    return new Map(scenes.map((scene) => [scene.id, scene] as const));
  }, [scenes]);
  const characterNameById = useMemo(() => {
    const entries =
      characters?.data.characters.map(
        (character: Character) => [character.id, character.name] as const,
      ) ?? [];
    return new Map(entries);
  }, [characters]);

  async function refresh(): Promise<void> {
    await revalidator.revalidate();
  }

  async function generateScreenplay(): Promise<void> {
    try {
      setWorking(true);
      const generated = await api.screenplay.generate(projectId, {
        shot_hints: shotHints,
      });
      setAiListOverride(null);
      setFilter("all");
      setShotHints(generated.data.shot_hints.enabled);
      toastManager.add({
        title: t("script.generateSuccess"),
        type: "success",
      });
      await refresh();
    } catch (error) {
      toastManager.add({
        description:
          error instanceof ApiError && error.code === "state_gate_blocked"
            ? t("script.gateBlocked")
            : getErrorMessage(error),
        title: t("script.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function refreshAiInferredList(): Promise<void> {
    try {
      setRefreshingAiList(true);
      const response = await api.screenplay.getBeats(projectId, "ai_inferred");
      setAiListOverride(response);
      toastManager.add({
        title: t("script.aiList.refreshSuccess"),
        type: "success",
      });
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("script.actionError"),
        type: "error",
      });
    } finally {
      setRefreshingAiList(false);
    }
  }

  return (
    <section className="space-y-4">
      {!outlineConfirmed ? (
        <Alert variant="warning">
          <AlertTitle>{t("script.lockedTitle")}</AlertTitle>
          <AlertDescription>{t("script.lockedDescription")}</AlertDescription>
          <AlertAction>
            <Button
              render={<Link to={stagePath(projectId, "outline")} />}
              size="sm"
              variant="outline"
            >
              {t("script.outlineCta")}
            </Button>
          </AlertAction>
        </Alert>
      ) : null}

      {outlineConfirmed && !screenplay ? (
        <Empty className="rounded-xl border bg-card">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <ClapperboardIcon />
            </EmptyMedia>
            <EmptyTitle>{t("script.emptyTitle")}</EmptyTitle>
            <EmptyDescription>{t("script.emptyDescription")}</EmptyDescription>
          </EmptyHeader>
          <EmptyContent className="w-full max-w-xl">
            <ShotHintsSwitch
              checked={shotHints}
              description={t("script.shotHintsDescription")}
              id="screenplay-shot-hints-empty"
              label={t("script.shotHintsLabel")}
              onCheckedChange={setShotHints}
            />
            <div className="mt-4 flex justify-center">
              <Button loading={working} onClick={generateScreenplay}>
                <SparklesIcon />
                {t("script.generate")}
              </Button>
            </div>
          </EmptyContent>
        </Empty>
      ) : null}

      {screenplay ? (
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 space-y-1">
              <h1 className="app-heading text-xl">{t("script.cardTitle")}</h1>
              <p className="text-muted-foreground text-sm">
                {t("script.cardDescription", {
                  beatCount,
                  sceneCount: scenes.length,
                })}
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2">
              <AlertDialog>
                <AlertDialogTrigger
                  render={
                    <Button disabled={working} size="sm" variant="outline" />
                  }
                >
                  <RefreshCwIcon />
                  {t("script.regenerate")}
                </AlertDialogTrigger>
                <AlertDialogPopup>
                  <AlertDialogHeader>
                    <AlertDialogTitle>
                      {t("script.regenerateTitle")}
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                      {t("script.regenerateDescription")}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogClose render={<Button variant="ghost" />}>
                      {t("script.cancel")}
                    </AlertDialogClose>
                    <AlertDialogClose
                      render={
                        <Button
                          loading={working}
                          onClick={generateScreenplay}
                          variant="destructive"
                        />
                      }
                    >
                      {t("script.regenerateConfirm")}
                    </AlertDialogClose>
                  </AlertDialogFooter>
                </AlertDialogPopup>
              </AlertDialog>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
            <ShotHintsSwitch
              checked={shotHints}
              description={t("script.shotHintsDescription")}
              id="screenplay-shot-hints-existing"
              label={t("script.shotHintsLabel")}
              onCheckedChange={setShotHints}
            />
            <Badge
              className="justify-self-start md:justify-self-end"
              variant="secondary"
            >
              {t("script.shotHintsState", {
                state: t(
                  screenplay.data.shot_hints.enabled
                    ? "script.shotHintsOn"
                    : "script.shotHintsOff",
                ),
              })}
            </Badge>
          </div>
          <Separator />
          <BeatFilterControl filter={filter} onFilterChange={setFilter} />
          <Separator />
          <div className="divide-y">
            {scenes.map((scene, index) => (
              <ScreenplaySceneCard
                characterNameById={characterNameById}
                filter={filter}
                key={scene.id}
                scene={scene}
                sceneNumber={index + 1}
              />
            ))}
          </div>

          <AiInferredListCard
            aiList={aiList}
            onRefresh={refreshAiInferredList}
            refreshing={refreshingAiList}
            sceneById={sceneById}
          />
        </>
      ) : null}
    </section>
  );
}

function BeatFilterControl({
  filter,
  onFilterChange,
}: {
  filter: BeatFilter;
  onFilterChange: (filter: BeatFilter) => void;
}): React.ReactElement {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="grid gap-1">
        <div className="flex items-center gap-2 font-medium text-sm">
          <ListFilterIcon className="size-4" aria-hidden />
          {t("script.filter.label")}
        </div>
        <p className="text-muted-foreground text-sm">
          {t("script.filter.description")}
        </p>
      </div>
      <ToggleGroup
        aria-label={t("script.filter.label")}
        className="w-fit rounded-lg"
        onValueChange={(value) => {
          const nextValue = value[0];
          if (
            nextValue === "all" ||
            nextValue === "from_source" ||
            nextValue === "ai_inferred"
          ) {
            onFilterChange(nextValue);
          }
        }}
        value={[filter]}
        variant="outline"
      >
        <ToggleGroupItem value="all">{t("script.filter.all")}</ToggleGroupItem>
        <ToggleGroupSeparator />
        <ToggleGroupItem value="from_source">
          {t("script.filter.from_source")}
        </ToggleGroupItem>
        <ToggleGroupSeparator />
        <ToggleGroupItem value="ai_inferred">
          {t("script.filter.ai_inferred")}
        </ToggleGroupItem>
      </ToggleGroup>
    </div>
  );
}

function ShotHintsSwitch({
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

function ScreenplaySceneCard({
  characterNameById,
  filter,
  scene,
  sceneNumber,
}: {
  characterNameById: Map<string, string>;
  filter: BeatFilter;
  scene: ScreenplayScene;
  sceneNumber: number;
}): React.ReactElement {
  const { t } = useTranslation();
  const matchingBeatCount =
    filter === "all"
      ? scene.beats.length
      : scene.beats.filter((beat) => beat.flag === filter).length;

  return (
    <article
      className={cn(
        "py-6 first:pt-0 last:pb-0 transition-opacity",
        filter !== "all" && matchingBeatCount === 0 ? "opacity-70" : null,
      )}
      id={`scene-${scene.id}`}
    >
      <SceneHeader
        characterNameById={characterNameById}
        scene={scene}
        sceneNumber={sceneNumber}
      />
      <div className="mt-4 space-y-4">
        <SceneSummary scene={scene} />
        <div className="grid gap-3">
          {scene.beats.map((beat, index) => (
            <BeatBlock
              beat={beat}
              characterNameById={characterNameById}
              filter={filter}
              index={index}
              key={`${scene.id}-${index}`}
              sceneId={scene.id}
            />
          ))}
        </div>
        {filter !== "all" && matchingBeatCount === 0 ? (
          <p className="rounded-lg border border-dashed p-3 text-muted-foreground text-sm">
            {t("script.filter.noSceneMatches")}
          </p>
        ) : null}
      </div>
    </article>
  );
}

function BeatBlock({
  beat,
  characterNameById,
  filter,
  index,
  sceneId,
}: {
  beat: Beat;
  characterNameById: Map<string, string>;
  filter: BeatFilter;
  index: number;
  sceneId: string;
}): React.ReactElement {
  const isFiltering = filter !== "all";
  const isMatch = !isFiltering || beat.flag === filter;

  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-[box-shadow,opacity]",
        beatToneClass(beat),
        isFiltering && isMatch ? "ring-2 ring-primary/32" : null,
        isFiltering && !isMatch ? "opacity-40" : null,
      )}
      id={`beat-${sceneId}-${index}`}
    >
      <BeatBadges beat={beat} index={index} />
      <BeatBody beat={beat} characterNameById={characterNameById} />
    </div>
  );
}

function AiInferredListCard({
  aiList,
  onRefresh,
  refreshing,
  sceneById,
}: {
  aiList: BeatsFilterResponse | null;
  onRefresh: () => Promise<void>;
  refreshing: boolean;
  sceneById: Map<string, ScreenplayScene>;
}): React.ReactElement {
  const { t } = useTranslation();
  const items = aiList?.items ?? [];

  return (
    <section className="space-y-4 border-t pt-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h2 className="font-medium text-base">{t("script.aiList.title")}</h2>
          <p className="text-muted-foreground text-sm">
            {t("script.aiList.description")}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge variant="warning">
            {t("script.aiList.count", { count: aiList?.count ?? 0 })}
          </Badge>
          <Button
            loading={refreshing}
            onClick={onRefresh}
            size="sm"
            variant="outline"
          >
            <RefreshCwIcon />
            {t("script.aiList.refresh")}
          </Button>
        </div>
      </div>
      {items.length > 0 ? (
        <div className="grid gap-3">
          {items.map((item) => {
            const scene = sceneById.get(item.scene_id);
            const title = scene
              ? sceneTitle(scene)
              : t("script.aiList.unknownScene", { id: item.scene_id });
            return (
              <div
                className="rounded-lg border bg-warning/8 p-4"
                key={`${item.scene_id}-${item.beat_index}`}
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="space-y-2">
                    <div className="font-medium text-sm">
                      {t("script.aiList.itemTitle", {
                        number: item.beat_index + 1,
                        sceneTitle: title,
                      })}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="warning">
                        {t("script.flags.ai_inferred")}
                      </Badge>
                      <Badge variant="secondary">
                        {t(`script.beatTypes.${item.beat.type}`)}
                      </Badge>
                      <Badge variant="secondary">
                        {sourceRefLabel(t, item.beat.source_ref)}
                      </Badge>
                    </div>
                    <p className="text-sm leading-relaxed">
                      {beatSummary(item.beat) || t("script.emptyField")}
                    </p>
                  </div>
                  <Button
                    onClick={() => scrollToBeat(item.scene_id, item.beat_index)}
                    size="sm"
                    variant="outline"
                  >
                    {t("script.aiList.review")}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="rounded-lg border border-dashed p-3 text-muted-foreground text-sm">
          {t("script.aiList.empty")}
        </p>
      )}
    </section>
  );
}
