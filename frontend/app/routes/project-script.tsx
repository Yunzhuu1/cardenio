import {
  ClapperboardIcon,
  FileTextIcon,
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
import { Label } from "~/components/ui/label";
import { Separator } from "~/components/ui/separator";
import { Switch } from "~/components/ui/switch";
import { toastManager } from "~/components/ui/toast";
import { api } from "~/lib/api/client";
import { api as loaderApi } from "~/lib/api/client";
import {
  ApiError,
  type ArtifactEnvelope,
  type Beat,
  type Character,
  type Flag,
  type ProjectId,
  type ScreenplayData,
  type ScreenplayScene,
  type SourceRef,
} from "~/lib/api/types";
import { cn } from "~/lib/utils";
import { stagePath } from "~/lib/stages";

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

  return {
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

function statusVariant(
  state: ArtifactEnvelope<ScreenplayData>["state"] | "empty",
): "default" | "secondary" | "success" | "warning" {
  if (state === "confirmed") return "success";
  if (state === "draft") return "warning";
  if (state === "needs_recompute") return "warning";
  return "secondary";
}

function paragraphLabel(paragraphs: number[]): string {
  if (paragraphs.length === 0) return "";
  const sorted = [...paragraphs].sort((a, b) => a - b);
  const ranges: string[] = [];
  let rangeStart = sorted[0];
  let previous = sorted[0];

  for (const paragraph of sorted.slice(1)) {
    if (paragraph === previous + 1) {
      previous = paragraph;
      continue;
    }
    ranges.push(
      rangeStart === previous ? `${rangeStart}` : `${rangeStart}-${previous}`,
    );
    rangeStart = paragraph;
    previous = paragraph;
  }
  ranges.push(
    rangeStart === previous ? `${rangeStart}` : `${rangeStart}-${previous}`,
  );
  return ranges.join(", ");
}

function sourceRefLabel(
  t: ReturnType<typeof useTranslation>["t"],
  sourceRef: SourceRef | null,
): string {
  if (!sourceRef) return t("script.noSourceRef");
  return t("script.sourceRef", {
    chapter: sourceRef.chapter,
    paragraphs: paragraphLabel(sourceRef.paragraphs),
  });
}

function flagVariant(flag: Flag | null): "secondary" | "success" | "warning" {
  if (flag === "from_source") return "success";
  if (flag === "ai_inferred") return "warning";
  return "secondary";
}

function beatToneClass(beat: Beat): string {
  if (beat.type === "todo") {
    return "border-warning/40 bg-warning/10";
  }
  if (beat.type === "note") {
    return "border-info/32 bg-info/8";
  }
  if (beat.flag === "ai_inferred") {
    return "border-warning/32 bg-warning/8";
  }
  return "border-border bg-card";
}

function characterName(
  characterNameById: Map<string, string>,
  characterId: string | null,
): string {
  if (!characterId) return "";
  return characterNameById.get(characterId) ?? characterId;
}

function charactersLabel(
  characters: string[],
  characterNameById: Map<string, string>,
  separator: string,
): string {
  if (characters.length === 0) return "";
  return characters
    .map((characterId) => characterNameById.get(characterId) ?? characterId)
    .join(separator);
}

function optionKindKey(kind: string): string {
  if (
    kind === "voice_over" ||
    kind === "action" ||
    kind === "dialogue" ||
    kind === "annotation"
  ) {
    return kind;
  }
  return "unknown";
}

export default function ProjectScript({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const revalidator = useRevalidator();
  const { characters, outline, projectId, screenplay } = loaderData;
  const [working, setWorking] = useState(false);
  const [shotHints, setShotHints] = useState(
    screenplay?.data.shot_hints.enabled ?? false,
  );
  const outlineConfirmed = outline?.state === "confirmed";
  const status = screenplay?.state ?? "empty";
  const scenes = screenplay?.data.scenes ?? [];
  const beatCount = scenes.reduce(
    (count, scene) => count + scene.beats.length,
    0,
  );
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

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="mb-2 text-muted-foreground text-sm font-medium">
            {t("pages.script.milestone")}
          </div>
          <h2 className="app-heading text-2xl">{t("pages.script.title")}</h2>
          <p className="mt-2 max-w-3xl text-muted-foreground text-sm">
            {t("pages.script.description")}
          </p>
        </div>
        <Badge variant={statusVariant(status)}>
          {t(`script.status.${status}`)}
        </Badge>
      </div>

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
          <Card>
            <CardHeader>
              <CardTitle>{t("script.cardTitle")}</CardTitle>
              <CardDescription>
                {t("script.cardDescription", {
                  beatCount,
                  sceneCount: scenes.length,
                })}
              </CardDescription>
              <CardAction className="flex flex-wrap gap-2">
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
                <Button
                  render={<Link to={stagePath(projectId, "editor")} />}
                  size="sm"
                >
                  {t("script.editorCta")}
                </Button>
              </CardAction>
            </CardHeader>
            <CardPanel className="space-y-4">
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
              <div className="grid gap-4">
                {scenes.map((scene, index) => (
                  <ScreenplaySceneCard
                    characterNameById={characterNameById}
                    key={scene.id}
                    scene={scene}
                    sceneNumber={index + 1}
                  />
                ))}
              </div>
            </CardPanel>
          </Card>
        </>
      ) : null}
    </section>
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
  scene,
  sceneNumber,
}: {
  characterNameById: Map<string, string>;
  scene: ScreenplayScene;
  sceneNumber: number;
}): React.ReactElement {
  const { t } = useTranslation();
  const characterSeparator = t("script.characterSeparator");
  const cast = charactersLabel(
    scene.characters,
    characterNameById,
    characterSeparator,
  );

  return (
    <Card className="rounded-xl shadow-none">
      <CardHeader className="border-b">
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <span>{t("script.sceneNumber", { number: sceneNumber })}</span>
          <Badge variant="outline">
            {t(`script.int_ext.${scene.heading.int_ext}`)}
          </Badge>
          <Badge variant="outline">{scene.heading.location}</Badge>
          <Badge variant="outline">
            {t(`script.time.${scene.heading.time}`)}
          </Badge>
        </CardTitle>
        <CardDescription className="flex flex-wrap gap-2">
          <Badge variant="secondary">
            {sourceRefLabel(t, scene.source_ref)}
          </Badge>
          {scene.mood ? <Badge variant="secondary">{scene.mood}</Badge> : null}
          {cast ? <Badge variant="secondary">{cast}</Badge> : null}
        </CardDescription>
      </CardHeader>
      <CardPanel className="space-y-4">
        <SceneSummary scene={scene} />
        <div className="grid gap-3">
          {scene.beats.map((beat, index) => (
            <BeatBlock
              beat={beat}
              characterNameById={characterNameById}
              index={index}
              key={`${scene.id}-${index}`}
            />
          ))}
        </div>
      </CardPanel>
    </Card>
  );
}

function SceneSummary({
  scene,
}: {
  scene: ScreenplayScene;
}): React.ReactElement {
  const { t } = useTranslation();
  const items = [
    ["synopsis", scene.synopsis],
    ["goal", scene.goal],
    ["conflict", scene.conflict],
    ["ending_state", scene.ending_state],
  ] as const;

  return (
    <div className="grid gap-2 rounded-lg bg-muted/32 p-3 text-sm md:grid-cols-2">
      {items.map(([key, value]) =>
        value ? (
          <div className="grid gap-1" key={key}>
            <div className="font-medium text-muted-foreground">
              {t(`script.fields.${key}`)}
            </div>
            <div>{value}</div>
          </div>
        ) : null,
      )}
    </div>
  );
}

function BeatBlock({
  beat,
  characterNameById,
  index,
}: {
  beat: Beat;
  characterNameById: Map<string, string>;
  index: number;
}): React.ReactElement {
  const { t } = useTranslation();
  const flagLabel = beat.flag
    ? t(`script.flags.${beat.flag}`)
    : t("script.flags.unknown");

  return (
    <div className={cn("rounded-lg border p-4", beatToneClass(beat))}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge variant="outline">{index + 1}</Badge>
        <Badge variant={beat.type === "todo" ? "warning" : "secondary"}>
          {t(`script.beatTypes.${beat.type}`)}
        </Badge>
        {beat.type === "todo" ? (
          <Badge variant="warning">{t("script.todoBadge")}</Badge>
        ) : null}
        <Badge variant={flagVariant(beat.flag)}>{flagLabel}</Badge>
        <Badge variant="secondary">{sourceRefLabel(t, beat.source_ref)}</Badge>
      </div>

      {beat.type === "dialogue" ||
      beat.type === "voice_over" ||
      beat.type === "off_screen" ? (
        <DialogueBeat beat={beat} characterNameById={characterNameById} />
      ) : beat.type === "note" ? (
        <NoteBeat beat={beat} />
      ) : (
        <p className="whitespace-pre-wrap leading-relaxed">
          {beat.text ?? t("script.emptyField")}
        </p>
      )}

      {beat.subtext ? (
        <p className="mt-3 text-muted-foreground text-sm">
          <span className="font-medium">{t("script.subtext")}：</span>
          {beat.subtext}
        </p>
      ) : null}
    </div>
  );
}

function DialogueBeat({
  beat,
  characterNameById,
}: {
  beat: Beat;
  characterNameById: Map<string, string>;
}): React.ReactElement {
  const { t } = useTranslation();
  const speaker = characterName(characterNameById, beat.character);
  const suffix =
    beat.type === "voice_over" || beat.type === "off_screen"
      ? t(`script.dialogueSuffix.${beat.type}`)
      : null;

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center gap-2 font-semibold">
        {speaker ? <span>{speaker}</span> : null}
        {suffix ? <Badge variant="outline">{suffix}</Badge> : null}
        {beat.parenthetical ? (
          <span className="font-normal text-muted-foreground">
            {beat.parenthetical}
          </span>
        ) : null}
      </div>
      <p className="whitespace-pre-wrap leading-relaxed">
        {beat.dialogue ?? beat.text ?? t("script.emptyField")}
      </p>
    </div>
  );
}

function NoteBeat({ beat }: { beat: Beat }): React.ReactElement {
  const { t } = useTranslation();
  const options = beat.options ?? [];

  return (
    <div className="grid gap-3">
      <div>
        <div className="mb-1 font-medium">{t("script.noteTitle")}</div>
        <p className="whitespace-pre-wrap leading-relaxed">
          {beat.text ?? t("script.emptyField")}
        </p>
      </div>
      {options.length > 0 ? (
        <Collapsible>
          <CollapsibleTrigger render={<Button size="xs" variant="outline" />}>
            <FileTextIcon />
            {t("script.optionsToggle", { count: options.length })}
          </CollapsibleTrigger>
          <CollapsiblePanel className="mt-3">
            <div className="grid gap-2">
              {options.map((option, index) => (
                <div
                  className="rounded-md border bg-background p-3"
                  key={index}
                >
                  <Badge className="mb-2" variant="secondary">
                    {t(`script.optionKinds.${optionKindKey(option.kind)}`)}
                  </Badge>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">
                    {option.text}
                  </p>
                </div>
              ))}
            </div>
          </CollapsiblePanel>
        </Collapsible>
      ) : null}
    </div>
  );
}
