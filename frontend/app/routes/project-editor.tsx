import {
  ClapperboardIcon,
  CrosshairIcon,
  FileTextIcon,
  LinkIcon,
} from "lucide-react";
import type * as React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useMatches } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/project-editor";
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
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { Label } from "~/components/ui/label";
import { ScrollArea } from "~/components/ui/scroll-area";
import { Separator } from "~/components/ui/separator";
import { Switch } from "~/components/ui/switch";
import { toastManager } from "~/components/ui/toast";
import { BeatBadges, BeatBody } from "~/components/screenplay-beat-view";
import { SceneHeader, SceneSummary } from "~/components/screenplay-scene-view";
import { TrustChips } from "~/components/trust-chips";
import { api } from "~/lib/api/client";
import { api as loaderApi } from "~/lib/api/client";
import {
  ApiError,
  type Chapter,
  type Character,
  type Project,
  type ProjectId,
  type ScreenplayScene,
  type SourceRef,
} from "~/lib/api/types";
import { beatToneClass } from "~/lib/screenplay-format";
import { stagePath } from "~/lib/stages";
import { cn } from "~/lib/utils";

type ActiveSource = {
  chapter: number;
  paragraphs: number[];
};

type ProjectLayoutData = {
  project: Project;
};

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
  const [screenplay, source, characters] = await Promise.all([
    getOrNull(loaderApi.screenplay.get(projectId)),
    loaderApi.source.get(projectId),
    getOrNull(loaderApi.characters.get(projectId)),
  ]);

  return {
    characters,
    projectId,
    screenplay,
    source,
  };
}

function sourceElementId(chapter: number, paragraph: number): string {
  return `src-${chapter}-${paragraph}`;
}

function sceneElementId(sceneId: string): string {
  return `scene-${sceneId}`;
}

function beatElementId(sceneId: string, beatIndex: number): string {
  return `beat-${sceneId}-${beatIndex}`;
}

function scrollElementIntoView(id: string): void {
  document
    .getElementById(id)
    ?.scrollIntoView({ behavior: "smooth", block: "center" });
}

function sceneMatchesSource(
  scene: ScreenplayScene,
  chapter: number,
  paragraph: number,
): boolean {
  return (
    scene.source_ref.chapter === chapter &&
    scene.source_ref.paragraphs.includes(paragraph)
  );
}

function refIncludesParagraph(
  sourceRef: SourceRef | null,
  chapter: number,
  paragraph: number,
): boolean {
  return (
    sourceRef?.chapter === chapter && sourceRef.paragraphs.includes(paragraph)
  );
}

function getScrollViewport(root: HTMLDivElement | null): HTMLElement | null {
  return (
    root?.querySelector<HTMLElement>('[data-slot="scroll-area-viewport"]') ??
    null
  );
}

function syncScroll(source: HTMLElement, target: HTMLElement): void {
  const sourceScrollable = source.scrollHeight - source.clientHeight;
  const targetScrollable = target.scrollHeight - target.clientHeight;
  const ratio = sourceScrollable > 0 ? source.scrollTop / sourceScrollable : 0;
  target.scrollTop = targetScrollable * ratio;
}

function projectStatusVariant(
  state: Project["state"] | undefined,
): "secondary" | "success" | "warning" {
  if (state === "editing") return "success";
  if (state === "generated") return "warning";
  return "secondary";
}

function hasProjectData(data: unknown): data is ProjectLayoutData {
  return typeof data === "object" && data !== null && "project" in data;
}

export default function ProjectEditor(
  props: Route.ComponentProps,
): React.ReactElement {
  const { t } = useTranslation();
  const matches = useMatches();
  const { loaderData } = props;
  const { characters, projectId, screenplay, source } = loaderData;
  const project = matches.find((match) => hasProjectData(match.data))?.data as
    | ProjectLayoutData
    | undefined;
  const [scrollSync, setScrollSync] = useState(true);
  const [activeSource, setActiveSource] = useState<ActiveSource | null>(null);
  const [activeSceneIds, setActiveSceneIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [locatingSceneId, setLocatingSceneId] = useState<string | null>(null);
  const sourceScrollRef = useRef<HTMLDivElement>(null);
  const screenplayScrollRef = useRef<HTMLDivElement>(null);
  const syncingScrollRef = useRef(false);

  const scenes = screenplay?.data.scenes ?? [];
  const characterNameById = useMemo(() => {
    const entries =
      characters?.data.characters.map(
        (character: Character) => [character.id, character.name] as const,
      ) ?? [];
    return new Map(entries);
  }, [characters]);

  const sortedChapters = useMemo(
    () => [...source.chapters].sort((a, b) => a.order - b.order),
    [source.chapters],
  );

  useEffect(() => {
    const sourceViewport = getScrollViewport(sourceScrollRef.current);
    const screenplayViewport = getScrollViewport(screenplayScrollRef.current);
    if (!sourceViewport || !screenplayViewport) return;

    function syncFromSource(): void {
      if (!scrollSync || syncingScrollRef.current) return;
      syncingScrollRef.current = true;
      syncScroll(
        sourceViewport as HTMLElement,
        screenplayViewport as HTMLElement,
      );
      window.requestAnimationFrame(() => {
        syncingScrollRef.current = false;
      });
    }

    function syncFromScreenplay(): void {
      if (!scrollSync || syncingScrollRef.current) return;
      syncingScrollRef.current = true;
      syncScroll(
        screenplayViewport as HTMLElement,
        sourceViewport as HTMLElement,
      );
      window.requestAnimationFrame(() => {
        syncingScrollRef.current = false;
      });
    }

    sourceViewport.addEventListener("scroll", syncFromSource, {
      passive: true,
    });
    screenplayViewport.addEventListener("scroll", syncFromScreenplay, {
      passive: true,
    });

    return () => {
      sourceViewport.removeEventListener("scroll", syncFromSource);
      screenplayViewport.removeEventListener("scroll", syncFromScreenplay);
    };
  }, [scrollSync]);

  function clearHighlights(): void {
    setActiveSource(null);
    setActiveSceneIds(new Set());
  }

  function highlightSceneSource(
    scene: ScreenplayScene,
    sourceRef?: SourceRef,
  ): void {
    const targetRef = sourceRef ?? scene.source_ref;
    setActiveSource({
      chapter: targetRef.chapter,
      paragraphs: targetRef.paragraphs,
    });
    setActiveSceneIds(new Set([scene.id]));
    const firstParagraph = targetRef.paragraphs[0];
    if (firstParagraph) {
      scrollElementIntoView(sourceElementId(targetRef.chapter, firstParagraph));
    }
  }

  function highlightSourceParagraph(chapter: number, paragraph: number): void {
    const matches = scenes.filter((scene) =>
      sceneMatchesSource(scene, chapter, paragraph),
    );
    setActiveSource({ chapter, paragraphs: [paragraph] });
    setActiveSceneIds(new Set(matches.map((scene) => scene.id)));
    if (matches[0]) {
      scrollElementIntoView(sceneElementId(matches[0].id));
    }
  }

  async function locateSceneSource(scene: ScreenplayScene): Promise<void> {
    try {
      setLocatingSceneId(scene.id);
      highlightSceneSource(scene);
      const trace = await api.screenplay.getTrace(projectId, scene.id);
      highlightSceneSource(scene, {
        chapter: trace.source_ref.chapter,
        paragraphs: trace.paragraphs.map((paragraph) => paragraph.index),
      });
    } catch (error) {
      toastManager.add({
        description:
          error instanceof ApiError && error.status === 404
            ? t("editor.traceNotFoundDescription")
            : error instanceof Error
              ? error.message
              : String(error),
        title: t("editor.traceNotFoundTitle"),
        type: "error",
      });
    } finally {
      setLocatingSceneId(null);
    }
  }

  if (!screenplay) {
    return (
      <section className="space-y-4">
        <EditorHeader
          projectState={project?.project.state}
          showStatus={false}
        />
        <Empty className="rounded-xl border bg-card">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <ClapperboardIcon />
            </EmptyMedia>
            <EmptyTitle>{t("editor.emptyTitle")}</EmptyTitle>
            <EmptyDescription>{t("editor.emptyDescription")}</EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button render={<Link to={stagePath(projectId, "script")} />}>
              {t("editor.emptyCta")}
            </Button>
          </EmptyContent>
        </Empty>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <EditorHeader projectState={project?.project.state} showStatus />

      <Card>
        <CardHeader>
          <CardTitle>{t("editor.dualPaneTitle")}</CardTitle>
          <CardDescription>{t("editor.dualPaneDescription")}</CardDescription>
        </CardHeader>
        <CardPanel className="space-y-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <LinkedSwitch
              checked={scrollSync}
              description={t("editor.scrollSyncDescription")}
              id="editor-scroll-sync"
              label={t("editor.scrollSyncLabel")}
              onCheckedChange={setScrollSync}
            />
            <Button onClick={clearHighlights} size="sm" variant="outline">
              {t("editor.clearHighlights")}
            </Button>
          </div>
          <Separator />
          <div className="grid gap-4 md:grid-cols-2">
            <section className="min-w-0">
              <PaneTitle
                icon={<FileTextIcon />}
                title={t("editor.sourcePane")}
              />
              <ScrollArea
                className="mt-3 h-[calc(100vh-16rem)] min-h-[28rem] rounded-xl border bg-background"
                ref={sourceScrollRef}
                scrollbarGutter
              >
                <SourcePane
                  activeSceneIds={activeSceneIds}
                  activeSource={activeSource}
                  chapters={sortedChapters}
                  onParagraphClick={highlightSourceParagraph}
                  scenes={scenes}
                />
              </ScrollArea>
            </section>

            <section className="min-w-0">
              <PaneTitle
                icon={<ClapperboardIcon />}
                title={t("editor.screenplayPane")}
              />
              <ScrollArea
                className="mt-3 h-[calc(100vh-16rem)] min-h-[28rem] rounded-xl border bg-background"
                ref={screenplayScrollRef}
                scrollbarGutter
              >
                <ScreenplayPane
                  activeSceneIds={activeSceneIds}
                  activeSource={activeSource}
                  characterNameById={characterNameById}
                  locatingSceneId={locatingSceneId}
                  onLocateScene={locateSceneSource}
                  onSceneClick={highlightSceneSource}
                  scenes={scenes}
                />
              </ScrollArea>
            </section>
          </div>
        </CardPanel>
      </Card>
    </section>
  );
}

function EditorHeader({
  projectState,
  showStatus,
}: {
  projectState: Project["state"] | undefined;
  showStatus: boolean;
}): React.ReactElement {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <div className="mb-2 text-muted-foreground text-sm font-medium">
          {t("pages.editor.milestone")}
        </div>
        <h2 className="app-heading text-2xl">{t("pages.editor.title")}</h2>
        <p className="mt-2 max-w-3xl text-muted-foreground text-sm">
          {t("pages.editor.description")}
        </p>
        <div className="mt-3">
          <TrustChips />
        </div>
      </div>
      {showStatus ? (
        <Badge variant={projectStatusVariant(projectState)}>
          {t("editor.projectStatus", {
            state: projectState
              ? t(`editor.states.${projectState}`)
              : t("editor.states.unknown"),
          })}
        </Badge>
      ) : null}
    </div>
  );
}

function LinkedSwitch({
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
    <div className="flex max-w-xl items-start justify-between gap-4 rounded-lg border p-3">
      <div className="grid gap-1">
        <Label htmlFor={id}>{label}</Label>
        <p className="text-muted-foreground text-sm">{description}</p>
      </div>
      <Switch checked={checked} id={id} onCheckedChange={onCheckedChange} />
    </div>
  );
}

function PaneTitle({
  icon,
  title,
}: {
  icon: React.ReactNode;
  title: string;
}): React.ReactElement {
  return (
    <div className="flex items-center gap-2 font-medium text-sm">
      <span className="[&_svg]:size-4 [&_svg]:text-muted-foreground">
        {icon}
      </span>
      {title}
    </div>
  );
}

function SourcePane({
  activeSceneIds,
  activeSource,
  chapters,
  onParagraphClick,
  scenes,
}: {
  activeSceneIds: Set<string>;
  activeSource: ActiveSource | null;
  chapters: Chapter[];
  onParagraphClick: (chapter: number, paragraph: number) => void;
  scenes: ScreenplayScene[];
}): React.ReactElement {
  const { t } = useTranslation();

  if (chapters.length === 0) {
    return (
      <p className="p-4 text-muted-foreground text-sm">
        {t("editor.emptySource")}
      </p>
    );
  }

  return (
    <div className="space-y-5 p-4">
      {chapters.map((chapter) => (
        <article className="space-y-3" key={chapter.id}>
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-semibold text-sm">{chapter.title}</h3>
            <Badge variant="outline">
              {t("editor.chapterOrder", { order: chapter.order })}
            </Badge>
          </div>
          <div className="space-y-2">
            {chapter.paragraphs.map((paragraph) => {
              const matchingScenes = scenes.filter((scene) =>
                sceneMatchesSource(scene, chapter.order, paragraph.index),
              );
              const isActive =
                activeSource?.chapter === chapter.order &&
                activeSource.paragraphs.includes(paragraph.index);
              const isSceneActive = matchingScenes.some((scene) =>
                activeSceneIds.has(scene.id),
              );

              return (
                <button
                  className={cn(
                    "w-full rounded-lg border bg-card p-3 text-left text-sm leading-relaxed transition-[background-color,box-shadow,opacity]",
                    isActive || isSceneActive
                      ? "border-primary/40 bg-primary/10 ring-1 ring-primary/40"
                      : "border-border hover:bg-accent/40",
                  )}
                  id={sourceElementId(chapter.order, paragraph.index)}
                  key={paragraph.index}
                  onClick={() =>
                    onParagraphClick(chapter.order, paragraph.index)
                  }
                  type="button"
                >
                  <span className="mb-1 block text-muted-foreground text-xs">
                    {t("editor.paragraphNumber", {
                      number: paragraph.index,
                    })}
                  </span>
                  <span className="whitespace-pre-wrap">{paragraph.text}</span>
                </button>
              );
            })}
          </div>
        </article>
      ))}
    </div>
  );
}

function ScreenplayPane({
  activeSceneIds,
  activeSource,
  characterNameById,
  locatingSceneId,
  onLocateScene,
  onSceneClick,
  scenes,
}: {
  activeSceneIds: Set<string>;
  activeSource: ActiveSource | null;
  characterNameById: Map<string, string>;
  locatingSceneId: string | null;
  onLocateScene: (scene: ScreenplayScene) => Promise<void>;
  onSceneClick: (scene: ScreenplayScene) => void;
  scenes: ScreenplayScene[];
}): React.ReactElement {
  const { t } = useTranslation();

  if (scenes.length === 0) {
    return (
      <p className="p-4 text-muted-foreground text-sm">
        {t("editor.emptyScreenplay")}
      </p>
    );
  }

  return (
    <div className="space-y-4 p-4">
      {scenes.map((scene, sceneIndex) => {
        const isSceneActive = activeSceneIds.has(scene.id);
        const sourceActive =
          activeSource?.chapter === scene.source_ref.chapter &&
          scene.source_ref.paragraphs.some((paragraph) =>
            activeSource.paragraphs.includes(paragraph),
          );

        return (
          <Card
            className={cn(
              "rounded-xl shadow-none transition-[box-shadow,opacity]",
              isSceneActive || sourceActive ? "ring-2 ring-primary/32" : null,
            )}
            id={sceneElementId(scene.id)}
            key={scene.id}
            onClick={() => onSceneClick(scene)}
          >
            <SceneHeader
              characterNameById={characterNameById}
              scene={scene}
              sceneNumber={sceneIndex + 1}
            />
            <CardPanel className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Button
                  loading={locatingSceneId === scene.id}
                  onClick={(event) => {
                    event.stopPropagation();
                    void onLocateScene(scene);
                  }}
                  size="sm"
                  variant="outline"
                >
                  <CrosshairIcon />
                  {t("editor.locateSource")}
                </Button>
                <Badge variant="secondary">
                  <LinkIcon className="mr-1 inline size-3" aria-hidden />
                  {scene.source_ref.paragraphs.join(", ")}
                </Badge>
              </div>
              <SceneSummary scene={scene} />
              <div className="grid gap-3">
                {scene.beats.map((beat, beatIndex) => {
                  const beatActive = activeSource
                    ? activeSource.paragraphs.some((paragraph) =>
                        refIncludesParagraph(
                          beat.source_ref,
                          activeSource.chapter,
                          paragraph,
                        ),
                      )
                    : false;

                  return (
                    <div
                      className={cn(
                        "rounded-lg border p-4 transition-[box-shadow,opacity]",
                        beatToneClass(beat),
                        beatActive ? "ring-2 ring-primary/32" : null,
                      )}
                      id={beatElementId(scene.id, beatIndex)}
                      key={`${scene.id}-${beatIndex}`}
                    >
                      <BeatBadges beat={beat} index={beatIndex} />
                      <BeatBody
                        beat={beat}
                        characterNameById={characterNameById}
                      />
                    </div>
                  );
                })}
              </div>
            </CardPanel>
          </Card>
        );
      })}
    </div>
  );
}
