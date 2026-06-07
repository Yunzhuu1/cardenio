import {
  AlertCircleIcon,
  ArrowDownIcon,
  ArrowUpIcon,
  ClapperboardIcon,
  CrosshairIcon,
  FileTextIcon,
  LinkIcon,
  PencilIcon,
  PlusIcon,
  SaveIcon,
  SparklesIcon,
  Trash2Icon,
} from "lucide-react";
import type * as React from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useMatches, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import YAML from "yaml";
import type { Route } from "./+types/project-editor";
import { Alert, AlertDescription } from "~/components/ui/alert";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import {
  AlertDialog,
  AlertDialogClose,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogPopup,
  AlertDialogTitle,
} from "~/components/ui/alert-dialog";
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
import {
  Dialog,
  DialogClose,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPanel,
  DialogPopup,
  DialogTitle,
} from "~/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "~/components/ui/field";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Menu, MenuItem, MenuPopup, MenuTrigger } from "~/components/ui/menu";
import { ScrollArea } from "~/components/ui/scroll-area";
import {
  Select,
  SelectItem,
  SelectPopup,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { Separator } from "~/components/ui/separator";
import { Switch } from "~/components/ui/switch";
import { Textarea } from "~/components/ui/textarea";
import {
  ToggleGroup,
  ToggleGroupItem,
  ToggleGroupSeparator,
} from "~/components/ui/toggle-group";
import { Tabs, TabsList, TabsPanel, TabsTab } from "~/components/ui/tabs";
import { toastManager } from "~/components/ui/toast";
import { BeatBadges, BeatBody } from "~/components/screenplay-beat-view";
import { SceneHeader, SceneSummary } from "~/components/screenplay-scene-view";
import { TrustChips } from "~/components/trust-chips";
import { api } from "~/lib/api/client";
import { api as loaderApi } from "~/lib/api/client";
import {
  ApiError,
  type Beat,
  type BeatType,
  type Chapter,
  type Character,
  type Flag,
  type IntExt,
  type Project,
  type ProjectId,
  type ScreenplayData,
  type ScreenplayScene,
  type SourceRef,
  type TimeOfDay,
} from "~/lib/api/types";
import { beatToneClass, sourceRefLabel } from "~/lib/screenplay-format";
import { stagePath } from "~/lib/stages";
import { cn } from "~/lib/utils";

type ActiveSource = {
  chapter: number;
  paragraphs: number[];
};

type ProjectLayoutData = {
  project: Project;
};

type SelectOption<T extends string> = {
  label: string;
  value: T;
};

type PendingEditAction =
  | { type: "edit"; scene: ScreenplayScene }
  | { type: "rewrite"; sceneId: string };

type EditorTab = "wysiwyg" | "yaml";
type ScreenplayYamlObject = Partial<ScreenplayData> & {
  scenes: ScreenplayScene[];
};

const INT_EXT_VALUES: IntExt[] = ["INT", "EXT"];
const TIME_VALUES: TimeOfDay[] = ["DAY", "NIGHT", "DAWN", "DUSK"];
const EDITABLE_BEAT_TYPES: BeatType[] = [
  "action",
  "dialogue",
  "voice_over",
  "off_screen",
  "note",
  "todo",
];
const FLAG_VALUES: Flag[] = ["from_source", "ai_inferred"];

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

function cloneScene(scene: ScreenplayScene): ScreenplayScene {
  return {
    ...scene,
    beats: scene.beats.map((beat) => ({
      ...beat,
      options: beat.options
        ? beat.options.map((option) => ({ ...option }))
        : null,
      source_ref: beat.source_ref
        ? {
            chapter: beat.source_ref.chapter,
            paragraphs: [...beat.source_ref.paragraphs],
          }
        : null,
    })),
    characters: [...scene.characters],
    foreshadowing: [...scene.foreshadowing],
    heading: { ...scene.heading },
    relation_changes: scene.relation_changes.map((change) => ({
      ...change,
      characters: [...change.characters],
    })),
    source_ref: {
      chapter: scene.source_ref.chapter,
      paragraphs: [...scene.source_ref.paragraphs],
    },
  };
}

function normalizeOptionalText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function makeBeat(type: BeatType, sourceRef: SourceRef): Beat {
  const base: Beat = {
    character: null,
    dialogue: null,
    flag: type === "todo" ? null : "ai_inferred",
    options: null,
    parenthetical: null,
    source_ref:
      type === "todo"
        ? null
        : {
            chapter: sourceRef.chapter,
            paragraphs: [...sourceRef.paragraphs],
          },
    subtext: null,
    text: "",
    type,
  };

  if (type === "dialogue" || type === "voice_over" || type === "off_screen") {
    return { ...base, dialogue: "" };
  }

  return base;
}

function missingTrustFields(scene: ScreenplayScene): number[] {
  return scene.beats
    .map((beat, index) =>
      beat.type !== "todo" && (!beat.source_ref || !beat.flag) ? index : null,
    )
    .filter((index): index is number => index !== null);
}

function isMissingTrustError(error: unknown): boolean {
  return (
    error instanceof ApiError && error.message.includes("missing_trust_fields")
  );
}

function screenplayToYaml(data: ScreenplayData): string {
  return YAML.stringify(data);
}

function isScreenplayYamlObject(value: unknown): value is ScreenplayYamlObject {
  return (
    typeof value === "object" &&
    value !== null &&
    Array.isArray((value as Partial<ScreenplayData>).scenes)
  );
}

function parseScreenplayYaml(
  text: string,
  fallbackShotHints: ScreenplayData["shot_hints"],
): ScreenplayData {
  const parsed: unknown = YAML.parse(text);
  if (!isScreenplayYamlObject(parsed)) {
    throw new Error("invalid_shape");
  }

  return {
    ...parsed,
    scenes: parsed.scenes,
    shot_hints: parsed.shot_hints ?? fallbackShotHints,
  };
}

export default function ProjectEditor(
  props: Route.ComponentProps,
): React.ReactElement {
  const { t } = useTranslation();
  const matches = useMatches();
  const revalidator = useRevalidator();
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
  const [rewriteSceneId, setRewriteSceneId] = useState<string | null>(null);
  const [rewriteInstruction, setRewriteInstruction] = useState("");
  const [rewriteTouched, setRewriteTouched] = useState(false);
  const [rewritingSceneId, setRewritingSceneId] = useState<string | null>(null);
  const [rewrittenSceneId, setRewrittenSceneId] = useState<string | null>(null);
  const [editingSceneId, setEditingSceneId] = useState<string | null>(null);
  const [draftScene, setDraftScene] = useState<ScreenplayScene | null>(null);
  const [savingSceneId, setSavingSceneId] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [pendingEditAction, setPendingEditAction] =
    useState<PendingEditAction | null>(null);
  const [editorTab, setEditorTab] = useState<EditorTab>("wysiwyg");
  const [yamlText, setYamlText] = useState(() =>
    screenplay ? screenplayToYaml(screenplay.data) : "",
  );
  const [sourceError, setSourceError] = useState<string | null>(null);
  const [applyingSource, setApplyingSource] = useState(false);
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
  const rewritingScene = scenes.find((scene) => scene.id === rewriteSceneId);
  const rewritingSceneNumber = rewritingScene
    ? scenes.findIndex((scene) => scene.id === rewritingScene.id) + 1
    : null;
  const rewriteInstructionTrimmed = rewriteInstruction.trim();
  const showRewriteError = rewriteTouched && rewriteInstructionTrimmed === "";
  const isEditing = draftScene !== null;

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

  function setRewriteOpen(open: boolean): void {
    if (!open) {
      setRewriteSceneId(null);
      setRewriteInstruction("");
      setRewriteTouched(false);
    }
  }

  function openRewriteDialog(sceneId: string): void {
    if (isEditing) {
      setPendingEditAction({ sceneId, type: "rewrite" });
      return;
    }
    setRewriteSceneId(sceneId);
    setRewriteInstruction("");
    setRewriteTouched(false);
  }

  function startEditingScene(scene: ScreenplayScene): void {
    if (isEditing && editingSceneId !== scene.id) {
      setPendingEditAction({ scene, type: "edit" });
      return;
    }
    setEditingSceneId(scene.id);
    setDraftScene(cloneScene(scene));
    setEditError(null);
    setRewrittenSceneId(null);
  }

  function cancelEditing(): void {
    setEditingSceneId(null);
    setDraftScene(null);
    setEditError(null);
  }

  function discardAndContinue(): void {
    const action = pendingEditAction;
    cancelEditing();
    setPendingEditAction(null);
    if (!action) return;
    if (action.type === "edit") {
      startEditingScene(action.scene);
      return;
    }
    openRewriteDialog(action.sceneId);
  }

  function updateDraftScene(nextScene: ScreenplayScene): void {
    setDraftScene(nextScene);
    setEditError(null);
  }

  async function saveDraftScene(): Promise<void> {
    if (!draftScene || !editingSceneId) return;
    const missingIndexes = missingTrustFields(draftScene);
    if (missingIndexes.length > 0) {
      setEditError(t("editor.edit.missingTrustFields"));
      return;
    }

    try {
      setSavingSceneId(editingSceneId);
      await api.screenplay.updateScene(projectId, editingSceneId, draftScene);
      toastManager.add({
        description: t("editor.edit.successDescription"),
        title: t("editor.edit.successTitle"),
        type: "success",
      });
      cancelEditing();
      await revalidator.revalidate();
    } catch (error) {
      setEditError(
        isMissingTrustError(error)
          ? t("editor.edit.missingTrustFields")
          : error instanceof Error
            ? error.message
            : t("editor.edit.failureDescription"),
      );
      toastManager.add({
        description:
          isMissingTrustError(error) || !(error instanceof Error)
            ? t("editor.edit.failureDescription")
            : error.message,
        title: t("editor.edit.failureTitle"),
        type: "error",
      });
    } finally {
      setSavingSceneId(null);
    }
  }

  function resetYamlSource(): void {
    if (!screenplay) return;
    setYamlText(screenplayToYaml(screenplay.data));
    setSourceError(null);
  }

  function handleEditorTabChange(value: string | number | null): void {
    const nextTab = value === "yaml" ? "yaml" : "wysiwyg";
    setEditorTab(nextTab);
    if (nextTab === "yaml") {
      resetYamlSource();
    }
  }

  async function applyYamlSource(): Promise<void> {
    if (!screenplay) return;
    setSourceError(null);
    let parsed: ScreenplayData;
    try {
      parsed = parseScreenplayYaml(yamlText, screenplay.data.shot_hints);
    } catch (error) {
      setSourceError(
        error instanceof Error && error.message === "invalid_shape"
          ? t("editor.source.invalidShape")
          : t("editor.source.syntaxError", {
              message: error instanceof Error ? error.message : String(error),
            }),
      );
      return;
    }

    try {
      setApplyingSource(true);
      await api.screenplay.updateScreenplay(projectId, parsed);
      toastManager.add({
        description: t("editor.source.successDescription"),
        title: t("editor.source.successTitle"),
        type: "success",
      });
      setEditorTab("wysiwyg");
      await revalidator.revalidate();
    } catch (error) {
      const message = isMissingTrustError(error)
        ? t("editor.source.missingTrustFields")
        : error instanceof Error
          ? error.message
          : t("editor.source.failureDescription");
      setSourceError(message);
      toastManager.add({
        description: message,
        title: t("editor.source.failureTitle"),
        type: "error",
      });
    } finally {
      setApplyingSource(false);
    }
  }

  async function submitRewrite(): Promise<void> {
    if (!rewritingScene) return;
    setRewriteTouched(true);
    if (!rewriteInstructionTrimmed) return;

    try {
      setRewritingSceneId(rewritingScene.id);
      await api.screenplay.rewriteScene(
        projectId,
        rewritingScene.id,
        rewriteInstructionTrimmed,
      );
      setRewrittenSceneId(rewritingScene.id);
      toastManager.add({
        description: t("editor.rewrite.successDescription"),
        title: t("editor.rewrite.successTitle"),
        type: "success",
      });
      setRewriteOpen(false);
      await revalidator.revalidate();
    } catch (error) {
      toastManager.add({
        description:
          error instanceof Error
            ? error.message
            : t("editor.rewrite.failureDescription"),
        title: t("editor.rewrite.failureTitle"),
        type: "error",
      });
    } finally {
      setRewritingSceneId(null);
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

      <Tabs onValueChange={handleEditorTabChange} value={editorTab}>
        <TabsList>
          <TabsTab value="wysiwyg">{t("editor.source.wysiwygTab")}</TabsTab>
          <TabsTab value="yaml">{t("editor.source.yamlTab")}</TabsTab>
        </TabsList>
        <TabsPanel value="wysiwyg">
          <Card>
            <CardHeader>
              <CardTitle>{t("editor.dualPaneTitle")}</CardTitle>
              <CardDescription>
                {t("editor.dualPaneDescription")}
              </CardDescription>
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
                      draftScene={draftScene}
                      editError={editError}
                      editingSceneId={editingSceneId}
                      locatingSceneId={locatingSceneId}
                      onCancelEdit={cancelEditing}
                      onDraftSceneChange={updateDraftScene}
                      onEditScene={startEditingScene}
                      onLocateScene={locateSceneSource}
                      onRewriteScene={openRewriteDialog}
                      onSaveDraft={() => void saveDraftScene()}
                      onSceneClick={highlightSceneSource}
                      rewrittenSceneId={rewrittenSceneId}
                      savingSceneId={savingSceneId}
                      scenes={scenes}
                    />
                  </ScrollArea>
                </section>
              </div>
            </CardPanel>
          </Card>
        </TabsPanel>
        <TabsPanel value="yaml">
          <YamlSourcePane
            applying={applyingSource}
            error={sourceError}
            onApply={() => void applyYamlSource()}
            onLoadCurrent={resetYamlSource}
            onReset={resetYamlSource}
            onTextChange={(text) => {
              setYamlText(text);
              setSourceError(null);
            }}
            text={yamlText}
          />
        </TabsPanel>
      </Tabs>

      <Dialog
        open={rewriteSceneId !== null}
        onOpenChange={(open) => setRewriteOpen(open)}
      >
        <DialogPopup className="max-w-xl">
          <DialogHeader>
            <DialogTitle>
              {t("editor.rewrite.title", {
                location: rewritingScene?.heading.location ?? "",
                number: rewritingSceneNumber ?? "",
              })}
            </DialogTitle>
            <DialogDescription>
              {t("editor.rewrite.description")}
            </DialogDescription>
          </DialogHeader>
          <DialogPanel>
            <Field validationMode="onSubmit">
              <FieldLabel htmlFor="editor-rewrite-instruction">
                {t("editor.rewrite.instructionLabel")}
              </FieldLabel>
              <Textarea
                aria-invalid={showRewriteError || undefined}
                disabled={rewritingSceneId !== null}
                id="editor-rewrite-instruction"
                onBlur={() => setRewriteTouched(true)}
                onChange={(event) =>
                  setRewriteInstruction(event.currentTarget.value)
                }
                placeholder={t("editor.rewrite.instructionPlaceholder")}
                value={rewriteInstruction}
              />
              <FieldDescription>
                {t("editor.rewrite.instructionDescription")}
              </FieldDescription>
              {showRewriteError ? (
                <FieldError>{t("editor.rewrite.emptyInstruction")}</FieldError>
              ) : null}
            </Field>
          </DialogPanel>
          <DialogFooter>
            <DialogClose render={<Button variant="ghost" />}>
              {t("editor.rewrite.cancel")}
            </DialogClose>
            <Button
              disabled={!rewriteInstructionTrimmed}
              loading={rewritingSceneId !== null}
              onClick={() => void submitRewrite()}
            >
              <SparklesIcon />
              {t("editor.rewrite.submit")}
            </Button>
          </DialogFooter>
        </DialogPopup>
      </Dialog>

      <AlertDialog
        open={pendingEditAction !== null}
        onOpenChange={(open) => {
          if (!open) setPendingEditAction(null);
        }}
      >
        <AlertDialogPopup>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("editor.edit.discardTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("editor.edit.discardDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogClose render={<Button variant="ghost" />}>
              {t("editor.edit.keepEditing")}
            </AlertDialogClose>
            <Button onClick={discardAndContinue} variant="destructive">
              {t("editor.edit.discard")}
            </Button>
          </AlertDialogFooter>
        </AlertDialogPopup>
      </AlertDialog>
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

function YamlSourcePane({
  applying,
  error,
  onApply,
  onLoadCurrent,
  onReset,
  onTextChange,
  text,
}: {
  applying: boolean;
  error: string | null;
  onApply: () => void;
  onLoadCurrent: () => void;
  onReset: () => void;
  onTextChange: (text: string) => void;
  text: string;
}): React.ReactElement {
  const { t } = useTranslation();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("editor.source.title")}</CardTitle>
        <CardDescription>{t("editor.source.yamlTab")}</CardDescription>
      </CardHeader>
      <CardPanel className="space-y-4">
        <Alert variant="info">
          <AlertCircleIcon />
          <AlertDescription>{t("editor.source.description")}</AlertDescription>
        </Alert>
        {error ? (
          <Alert variant="error">
            <AlertCircleIcon />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        <Textarea
          className="min-h-[calc(100vh-18rem)] resize-y whitespace-pre font-mono text-sm"
          onChange={(event) => onTextChange(event.currentTarget.value)}
          spellCheck={false}
          value={text}
        />
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <Button onClick={onLoadCurrent} type="button" variant="outline">
            {t("editor.source.loadCurrent")}
          </Button>
          <div className="flex flex-wrap gap-2 sm:justify-end">
            <Button onClick={onReset} type="button" variant="ghost">
              {t("editor.source.reset")}
            </Button>
            <Button loading={applying} onClick={onApply} type="button">
              <SaveIcon />
              {t("editor.source.apply")}
            </Button>
          </div>
        </div>
      </CardPanel>
    </Card>
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
  draftScene,
  editError,
  editingSceneId,
  locatingSceneId,
  onCancelEdit,
  onDraftSceneChange,
  onEditScene,
  onLocateScene,
  onRewriteScene,
  onSaveDraft,
  onSceneClick,
  rewrittenSceneId,
  savingSceneId,
  scenes,
}: {
  activeSceneIds: Set<string>;
  activeSource: ActiveSource | null;
  characterNameById: Map<string, string>;
  draftScene: ScreenplayScene | null;
  editError: string | null;
  editingSceneId: string | null;
  locatingSceneId: string | null;
  onCancelEdit: () => void;
  onDraftSceneChange: (scene: ScreenplayScene) => void;
  onEditScene: (scene: ScreenplayScene) => void;
  onLocateScene: (scene: ScreenplayScene) => Promise<void>;
  onRewriteScene: (sceneId: string) => void;
  onSaveDraft: () => void;
  onSceneClick: (scene: ScreenplayScene) => void;
  rewrittenSceneId: string | null;
  savingSceneId: string | null;
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
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    onClick={(event) => {
                      event.stopPropagation();
                      onEditScene(scene);
                    }}
                    size="sm"
                    variant="outline"
                  >
                    <PencilIcon />
                    {t("editor.edit.button")}
                  </Button>
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
                  <Button
                    onClick={(event) => {
                      event.stopPropagation();
                      onRewriteScene(scene.id);
                    }}
                    size="sm"
                    variant="outline"
                  >
                    <SparklesIcon />
                    {t("editor.rewrite.button")}
                  </Button>
                </div>
                <Badge variant="secondary">
                  <LinkIcon className="mr-1 inline size-3" aria-hidden />
                  {scene.source_ref.paragraphs.join(", ")}
                </Badge>
              </div>
              {rewrittenSceneId === scene.id ? (
                <div className="rounded-lg border border-primary/24 bg-primary/8 px-3 py-2 text-primary text-sm">
                  {t("editor.rewrite.reviewHint")}
                </div>
              ) : null}
              {editingSceneId === scene.id && draftScene ? (
                <SceneEditForm
                  characterNameById={characterNameById}
                  editError={editError}
                  onCancel={onCancelEdit}
                  onChange={onDraftSceneChange}
                  onSave={onSaveDraft}
                  saving={savingSceneId === scene.id}
                  scene={draftScene}
                />
              ) : (
                <>
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
                </>
              )}
            </CardPanel>
          </Card>
        );
      })}
    </div>
  );
}

function SceneEditForm({
  characterNameById,
  editError,
  onCancel,
  onChange,
  onSave,
  saving,
  scene,
}: {
  characterNameById: Map<string, string>;
  editError: string | null;
  onCancel: () => void;
  onChange: (scene: ScreenplayScene) => void;
  onSave: () => void;
  saving: boolean;
  scene: ScreenplayScene;
}): React.ReactElement {
  const { t } = useTranslation();
  const intExtItems = INT_EXT_VALUES.map((value) => ({
    label: t(`editor.edit.intExt.${value}`),
    value,
  }));
  const timeItems = TIME_VALUES.map((value) => ({
    label: t(`editor.edit.time.${value}`),
    value,
  }));

  function updateScene(patch: Partial<ScreenplayScene>): void {
    onChange({ ...scene, ...patch });
  }

  function updateBeat(index: number, beat: Beat): void {
    onChange({
      ...scene,
      beats: scene.beats.map((item, itemIndex) =>
        itemIndex === index ? beat : item,
      ),
    });
  }

  function removeBeat(index: number): void {
    onChange({
      ...scene,
      beats: scene.beats.filter((_, itemIndex) => itemIndex !== index),
    });
  }

  function moveBeat(index: number, direction: -1 | 1): void {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= scene.beats.length) return;
    const beats = [...scene.beats];
    const current = beats[index];
    const next = beats[nextIndex];
    if (!current || !next) return;
    beats[index] = next;
    beats[nextIndex] = current;
    onChange({ ...scene, beats });
  }

  function addBeat(type: BeatType): void {
    onChange({
      ...scene,
      beats: [...scene.beats, makeBeat(type, scene.source_ref)],
    });
  }

  return (
    <div className="space-y-4 rounded-xl border bg-background/64 p-4">
      {editError ? (
        <div className="rounded-lg border border-destructive/32 bg-destructive/8 px-3 py-2 text-destructive-foreground text-sm">
          {editError}
        </div>
      ) : null}
      <div className="grid gap-3 lg:grid-cols-2">
        <SelectField
          items={intExtItems}
          label={t("editor.edit.intExtLabel")}
          onChange={(value) =>
            updateScene({
              heading: { ...scene.heading, int_ext: value },
            })
          }
          value={scene.heading.int_ext}
        />
        <SelectField
          items={timeItems}
          label={t("editor.edit.timeLabel")}
          onChange={(value) =>
            updateScene({
              heading: { ...scene.heading, time: value },
            })
          }
          value={scene.heading.time}
        />
        <TextField
          label={t("editor.edit.locationLabel")}
          onChange={(value) =>
            updateScene({
              heading: { ...scene.heading, location: value },
            })
          }
          value={scene.heading.location}
        />
        <TextField
          label={t("editor.edit.moodLabel")}
          onChange={(value) =>
            updateScene({ mood: normalizeOptionalText(value) })
          }
          value={scene.mood ?? ""}
        />
      </div>

      <div className="grid gap-3">
        {scene.beats.map((beat, index) => (
          <BeatEditCard
            beat={beat}
            canMoveDown={index < scene.beats.length - 1}
            canMoveUp={index > 0}
            characterNameById={characterNameById}
            index={index}
            key={`${scene.id}-draft-${index}`}
            onChange={(nextBeat) => updateBeat(index, nextBeat)}
            onMoveDown={() => moveBeat(index, 1)}
            onMoveUp={() => moveBeat(index, -1)}
            onRemove={() => removeBeat(index)}
          />
        ))}
      </div>

      <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
        <AddBeatMenu onAdd={addBeat} />
        <div className="flex flex-wrap justify-end gap-2">
          <Button onClick={onCancel} variant="ghost">
            {t("editor.edit.cancel")}
          </Button>
          <Button loading={saving} onClick={onSave}>
            <SaveIcon />
            {t("editor.edit.save")}
          </Button>
        </div>
      </div>
    </div>
  );
}

function BeatEditCard({
  beat,
  canMoveDown,
  canMoveUp,
  characterNameById,
  index,
  onChange,
  onMoveDown,
  onMoveUp,
  onRemove,
}: {
  beat: Beat;
  canMoveDown: boolean;
  canMoveUp: boolean;
  characterNameById: Map<string, string>;
  index: number;
  onChange: (beat: Beat) => void;
  onMoveDown: () => void;
  onMoveUp: () => void;
  onRemove: () => void;
}): React.ReactElement {
  const { t } = useTranslation();

  function updateBeat(patch: Partial<Beat>): void {
    onChange({ ...beat, ...patch });
  }

  return (
    <div className="space-y-3 rounded-lg border bg-card p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <BeatBadges beat={beat} index={index} />
        <div className="flex items-center gap-1">
          <Button
            aria-label={t("editor.edit.moveUp")}
            disabled={!canMoveUp}
            onClick={onMoveUp}
            size="icon-xs"
            variant="ghost"
          >
            <ArrowUpIcon />
          </Button>
          <Button
            aria-label={t("editor.edit.moveDown")}
            disabled={!canMoveDown}
            onClick={onMoveDown}
            size="icon-xs"
            variant="ghost"
          >
            <ArrowDownIcon />
          </Button>
          <Button
            aria-label={t("editor.edit.removeBeat")}
            onClick={onRemove}
            size="icon-xs"
            variant="ghost"
          >
            <Trash2Icon />
          </Button>
        </div>
      </div>

      {beat.type === "dialogue" ||
      beat.type === "voice_over" ||
      beat.type === "off_screen" ? (
        <div className="grid gap-3">
          <CharacterSelect
            characterNameById={characterNameById}
            onChange={(value) => updateBeat({ character: value })}
            value={beat.character}
          />
          <TextField
            label={t("editor.edit.parentheticalLabel")}
            onChange={(value) =>
              updateBeat({ parenthetical: normalizeOptionalText(value) })
            }
            value={beat.parenthetical ?? ""}
          />
          <TextAreaField
            label={t("editor.edit.dialogueLabel")}
            onChange={(value) => updateBeat({ dialogue: value })}
            value={beat.dialogue ?? ""}
          />
        </div>
      ) : (
        <TextAreaField
          label={t("editor.edit.textLabel")}
          onChange={(value) => updateBeat({ text: value })}
          value={beat.text ?? ""}
        />
      )}

      {beat.type === "note" && beat.options?.length ? (
        <div className="rounded-lg border bg-background/64 p-3 text-sm">
          <div className="mb-2 font-medium">
            {t("editor.edit.optionsReadonly")}
          </div>
          <ul className="space-y-1 text-muted-foreground">
            {beat.options.map((option, optionIndex) => (
              <li key={`${option.kind}-${optionIndex}`}>
                {option.kind}: {option.text}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {beat.type !== "todo" ? (
        <>
          <TextAreaField
            label={t("editor.edit.subtextLabel")}
            onChange={(value) =>
              updateBeat({ subtext: normalizeOptionalText(value) })
            }
            value={beat.subtext ?? ""}
          />
          <Field className="gap-2">
            <FieldLabel>{t("editor.edit.flagLabel")}</FieldLabel>
            <ToggleGroup
              aria-label={t("editor.edit.flagLabel")}
              onValueChange={(value) => {
                const nextValue = value[0];
                if (
                  nextValue === "from_source" ||
                  nextValue === "ai_inferred"
                ) {
                  updateBeat({ flag: nextValue });
                }
              }}
              value={beat.flag ? [beat.flag] : []}
              variant="outline"
            >
              {FLAG_VALUES.map((flag, flagIndex) => (
                <span className="contents" key={flag}>
                  {flagIndex > 0 ? <ToggleGroupSeparator /> : null}
                  <ToggleGroupItem value={flag}>
                    {t(`editor.edit.flag.${flag}`)}
                  </ToggleGroupItem>
                </span>
              ))}
            </ToggleGroup>
          </Field>
          <div className="text-muted-foreground text-xs">
            {beat.source_ref
              ? sourceRefLabel(t, beat.source_ref)
              : t("editor.edit.missingSourceRef")}
          </div>
        </>
      ) : null}
    </div>
  );
}

function TextField({
  label,
  onChange,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
}): React.ReactElement {
  return (
    <Field className="w-full">
      <FieldLabel>{label}</FieldLabel>
      <Input
        onChange={(event) => onChange(event.currentTarget.value)}
        value={value}
      />
    </Field>
  );
}

function TextAreaField({
  label,
  onChange,
  value,
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
}): React.ReactElement {
  return (
    <Field className="w-full">
      <FieldLabel>{label}</FieldLabel>
      <Textarea
        onChange={(event) => onChange(event.currentTarget.value)}
        value={value}
      />
    </Field>
  );
}

function SelectField<T extends string>({
  items,
  label,
  onChange,
  value,
}: {
  items: SelectOption<T>[];
  label: string;
  onChange: (value: T) => void;
  value: T;
}): React.ReactElement {
  const selectedItem = items.find((item) => item.value === value) ?? items[0];

  return (
    <Field className="w-full">
      <FieldLabel>{label}</FieldLabel>
      <Select
        itemToStringValue={(item) => item.value}
        items={items}
        onValueChange={(nextValue) => {
          if (nextValue) onChange(nextValue.value);
        }}
        value={selectedItem}
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectPopup>
          {items.map((item) => (
            <SelectItem key={item.value} value={item}>
              {item.label}
            </SelectItem>
          ))}
        </SelectPopup>
      </Select>
    </Field>
  );
}

function CharacterSelect({
  characterNameById,
  onChange,
  value,
}: {
  characterNameById: Map<string, string>;
  onChange: (value: string | null) => void;
  value: string | null;
}): React.ReactElement {
  const { t } = useTranslation();
  const items: SelectOption<string>[] = [
    { label: t("editor.edit.noCharacter"), value: "__none__" },
    ...Array.from(characterNameById.entries()).map(([id, name]) => ({
      label: name,
      value: id,
    })),
  ];
  const selectedValue = value ?? "__none__";

  return (
    <SelectField
      items={items}
      label={t("editor.edit.characterLabel")}
      onChange={(nextValue) =>
        onChange(nextValue === "__none__" ? null : nextValue)
      }
      value={selectedValue}
    />
  );
}

function AddBeatMenu({
  onAdd,
}: {
  onAdd: (type: BeatType) => void;
}): React.ReactElement {
  const { t } = useTranslation();

  return (
    <Menu>
      <MenuTrigger render={<Button variant="outline" />}>
        <PlusIcon />
        {t("editor.edit.addBeat")}
      </MenuTrigger>
      <MenuPopup align="start">
        {EDITABLE_BEAT_TYPES.map((type) => (
          <MenuItem key={type} onClick={() => onAdd(type)}>
            {t(`editor.edit.beatType.${type}`)}
          </MenuItem>
        ))}
      </MenuPopup>
    </Menu>
  );
}
