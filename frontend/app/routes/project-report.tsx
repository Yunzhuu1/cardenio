import {
  BotIcon,
  FileTextIcon,
  GitMergeIcon,
  ListChecksIcon,
  LightbulbIcon,
  RefreshCwIcon,
  ScissorsIcon,
  ScrollTextIcon,
  SparklesIcon,
  Trash2Icon,
} from "lucide-react";
import type * as React from "react";
import { useMemo, useState } from "react";
import { Link, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import type { Route } from "./+types/project-report";
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
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { Separator } from "~/components/ui/separator";
import { toastManager } from "~/components/ui/toast";
import { TrustChips } from "~/components/trust-chips";
import { api } from "~/lib/api/client";
import { api as loaderApi } from "~/lib/api/client";
import {
  ApiError,
  type ArtifactEnvelope,
  type ExternalizationEntry,
  type ProjectId,
  type ReportData,
  type ReportEntry,
  type ReportMergedEntry,
  type ReviewRecommendation,
  type ScreenplayData,
  type ScreenplayScene,
} from "~/lib/api/types";
import {
  flagVariant,
  sceneTitle,
  sourceRefLabel,
} from "~/lib/screenplay-format";
import { stagePath } from "~/lib/stages";
import { cn } from "~/lib/utils";

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
  const [screenplay, report] = await Promise.all([
    getOrNull(loaderApi.screenplay.get(projectId)),
    getOrNull(loaderApi.report.get(projectId)),
  ]);

  return {
    projectId,
    report,
    screenplay,
  };
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

function statusVariant(
  state: ArtifactEnvelope<ReportData>["state"] | "empty",
): "default" | "secondary" | "success" | "warning" {
  if (state === "confirmed") return "success";
  if (state === "draft") return "warning";
  if (state === "needs_recompute") return "warning";
  return "secondary";
}

function localizedReportError(error: unknown, t: TFunction): string {
  if (error instanceof ApiError && error.code === "report_flag_mismatch") {
    return t("report.generate.flagMismatch");
  }
  if (error instanceof ApiError && error.message === "Screenplay not found") {
    return t("report.generate.missingScreenplay");
  }
  return getErrorMessage(error);
}

function reportTypeLabel(t: TFunction, type: string): string {
  const knownTypes = new Set([
    "non_visualizable_source",
    "voice_over",
    "action",
    "dialogue",
    "note",
  ]);
  if (!knownTypes.has(type)) return type;
  return t(`report.sections.types.${type}`);
}

function sceneLabel(
  t: TFunction,
  sceneById: Map<string, ScreenplayScene>,
  sceneId: string | null,
): string | null {
  if (!sceneId) return null;
  const scene = sceneById.get(sceneId);
  return scene
    ? sceneTitle(scene)
    : t("report.sections.unknownScene", { id: sceneId });
}

export default function ProjectReport({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const revalidator = useRevalidator();
  const { projectId, report, screenplay } = loaderData;
  const [working, setWorking] = useState(false);
  const status = report?.state ?? "empty";
  const sceneById = useMemo(() => {
    return new Map(
      screenplay?.data.scenes.map((scene) => [scene.id, scene] as const) ?? [],
    );
  }, [screenplay]);

  async function refresh(): Promise<void> {
    await revalidator.revalidate();
  }

  async function generateReport(): Promise<void> {
    try {
      setWorking(true);
      await api.report.generate(projectId);
      toastManager.add({
        title: t("report.generate.success"),
        type: "success",
      });
      await refresh();
    } catch (error) {
      toastManager.add({
        description: localizedReportError(error, t),
        title: t("report.generate.error"),
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
            {t("pages.report.milestone")}
          </div>
          <h2 className="app-heading text-2xl">{t("pages.report.title")}</h2>
          <p className="mt-2 max-w-3xl text-muted-foreground text-sm">
            {t("pages.report.description")}
          </p>
        </div>
        <Badge variant={statusVariant(status)}>
          {t(`report.status.${status}`)}
        </Badge>
      </div>

      {!screenplay ? (
        <Empty className="rounded-xl border bg-card">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <ScrollTextIcon />
            </EmptyMedia>
            <EmptyTitle>{t("report.gate.screenplayTitle")}</EmptyTitle>
            <EmptyDescription>
              {t("report.gate.screenplayDescription")}
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button render={<Link to={stagePath(projectId, "script")} />}>
              {t("report.gate.screenplayCta")}
            </Button>
          </EmptyContent>
        </Empty>
      ) : null}

      {screenplay && !report ? (
        <Empty className="rounded-xl border bg-card">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FileTextIcon />
            </EmptyMedia>
            <EmptyTitle>{t("report.gate.emptyTitle")}</EmptyTitle>
            <EmptyDescription>
              {t("report.gate.emptyDescription")}
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button loading={working} onClick={generateReport}>
              <SparklesIcon />
              {t("report.gate.generateCta")}
            </Button>
          </EmptyContent>
        </Empty>
      ) : null}

      {screenplay && report ? (
        <>
          <ReportSummaryCard
            onRegenerate={generateReport}
            report={report}
            working={working}
          />
          <ReportSections
            report={report.data}
            sceneById={sceneById}
            screenplay={screenplay.data}
          />
        </>
      ) : null}
    </section>
  );
}

function ReportSummaryCard({
  onRegenerate,
  report,
  working,
}: {
  onRegenerate: () => Promise<void>;
  report: ArtifactEnvelope<ReportData>;
  working: boolean;
}): React.ReactElement {
  const { t } = useTranslation();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("report.summary.title")}</CardTitle>
        <CardDescription>{t("report.summary.description")}</CardDescription>
        <CardAction>
          <AlertDialog>
            <AlertDialogTrigger
              render={<Button disabled={working} size="sm" variant="outline" />}
            >
              <RefreshCwIcon />
              {t("report.generate.regenerate")}
            </AlertDialogTrigger>
            <AlertDialogPopup>
              <AlertDialogHeader>
                <AlertDialogTitle>
                  {t("report.generate.title")}
                </AlertDialogTitle>
                <AlertDialogDescription>
                  {t("report.generate.description")}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogClose render={<Button variant="ghost" />}>
                  {t("report.generate.cancel")}
                </AlertDialogClose>
                <AlertDialogClose
                  render={
                    <Button
                      loading={working}
                      onClick={onRegenerate}
                      variant="destructive"
                    />
                  }
                >
                  {t("report.generate.confirm")}
                </AlertDialogClose>
              </AlertDialogFooter>
            </AlertDialogPopup>
          </AlertDialog>
        </CardAction>
      </CardHeader>
      <CardPanel className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="success">
            {t("report.summary.fromSource", {
              count: report.data.from_source_lines,
            })}
          </Badge>
          <Badge variant="warning">
            {t("report.summary.aiInferred", {
              count: report.data.ai_inferred_lines,
            })}
          </Badge>
          <Badge variant="secondary">{t("report.summary.artifact")}</Badge>
        </div>
        <Separator />
        <TrustChips />
      </CardPanel>
    </Card>
  );
}

function ReportSections({
  report,
  sceneById,
  screenplay,
}: {
  report: ReportData;
  sceneById: Map<string, ScreenplayScene>;
  screenplay: ScreenplayData;
}): React.ReactElement {
  return (
    <div className="grid gap-4">
      <ReportEntrySection
        entries={report.kept}
        icon={FileTextIcon}
        sceneById={sceneById}
        titleKey="report.sections.kept"
      />
      <ReportEntrySection
        entries={report.added}
        icon={BotIcon}
        sceneById={sceneById}
        titleKey="report.sections.added"
      />
      <ReportEntrySection
        entries={report.deleted}
        icon={Trash2Icon}
        sceneById={sceneById}
        titleKey="report.sections.deleted"
      />
      <MergedSection entries={report.merged} sceneById={sceneById} />
      <ExternalizedSection
        entries={report.externalized}
        sceneById={sceneById}
      />
      <ForeshadowingSection items={report.kept_foreshadowing} />
      <ReviewSection
        entries={report.review_recommended}
        sceneById={sceneById}
        screenplay={screenplay}
      />
    </div>
  );
}

function SectionCard({
  children,
  count,
  icon: Icon,
  titleKey,
}: {
  children: React.ReactNode;
  count: number;
  icon: React.ComponentType<{ className?: string }>;
  titleKey: string;
}): React.ReactElement {
  const { t } = useTranslation();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon aria-hidden className="size-4 text-muted-foreground" />
          {t(titleKey)}
        </CardTitle>
        <CardAction>
          <Badge variant="secondary">
            {t("report.sections.count", { count })}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardPanel>{children}</CardPanel>
    </Card>
  );
}

function EmptySection(): React.ReactElement {
  const { t } = useTranslation();

  return (
    <p className="rounded-lg border border-dashed p-3 text-muted-foreground text-sm">
      {t("report.sections.empty")}
    </p>
  );
}

function ReportEntrySection({
  entries,
  icon,
  sceneById,
  titleKey,
}: {
  entries: ReportEntry[];
  icon: React.ComponentType<{ className?: string }>;
  sceneById: Map<string, ScreenplayScene>;
  titleKey: string;
}): React.ReactElement {
  return (
    <SectionCard count={entries.length} icon={icon} titleKey={titleKey}>
      {entries.length > 0 ? (
        <div className="grid gap-3">
          {entries.map((entry, index) => (
            <ReportEntryRow
              entry={entry}
              index={index}
              key={`${entry.scene_id ?? "no-scene"}-${index}-${entry.item}`}
              sceneById={sceneById}
            />
          ))}
        </div>
      ) : (
        <EmptySection />
      )}
    </SectionCard>
  );
}

function ReportEntryRow({
  entry,
  index,
  sceneById,
}: {
  entry: ReportEntry;
  index: number;
  sceneById: Map<string, ScreenplayScene>;
}): React.ReactElement {
  const { t } = useTranslation();
  const scene = sceneLabel(t, sceneById, entry.scene_id);

  return (
    <div
      className={cn(
        "grid gap-3 rounded-lg border p-4",
        entry.flag === "ai_inferred" ? "bg-warning/8" : "bg-card",
      )}
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="font-medium text-sm leading-relaxed">
            {entry.item || t("script.emptyField")}
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">#{index + 1}</Badge>
            <Badge variant={flagVariant(entry.flag)}>
              {t(`script.flags.${entry.flag ?? "unknown"}`)}
            </Badge>
            {scene ? (
              <Badge variant="secondary">
                {t("report.sections.scene", { title: scene })}
              </Badge>
            ) : null}
            <Badge variant="secondary">
              {t("report.sections.source", {
                source: sourceRefLabel(t, entry.source_ref),
              })}
            </Badge>
          </div>
        </div>
      </div>
    </div>
  );
}

function MergedSection({
  entries,
  sceneById,
}: {
  entries: ReportMergedEntry[];
  sceneById: Map<string, ScreenplayScene>;
}): React.ReactElement {
  const { t } = useTranslation();

  return (
    <SectionCard
      count={entries.length}
      icon={GitMergeIcon}
      titleKey="report.sections.merged"
    >
      {entries.length > 0 ? (
        <div className="grid gap-3">
          {entries.map((entry, index) => {
            const sceneNames = entry.scene_ids
              .map((sceneId) => sceneLabel(t, sceneById, sceneId))
              .filter((item): item is string => Boolean(item))
              .join(t("script.characterSeparator"));
            return (
              <div className="grid gap-2 rounded-lg border p-4" key={index}>
                <div className="font-medium text-sm">
                  {t("report.sections.mergedInto", { into: entry.into })}
                </div>
                <p className="text-muted-foreground text-sm">
                  {t("report.sections.mergedScenes", { scenes: sceneNames })}
                </p>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptySection />
      )}
    </SectionCard>
  );
}

function ExternalizedSection({
  entries,
  sceneById,
}: {
  entries: ExternalizationEntry[];
  sceneById: Map<string, ScreenplayScene>;
}): React.ReactElement {
  const { t } = useTranslation();

  return (
    <SectionCard
      count={entries.length}
      icon={LightbulbIcon}
      titleKey="report.sections.externalized"
    >
      {entries.length > 0 ? (
        <div className="grid gap-3">
          {entries.map((entry, index) => (
            <div
              className="grid gap-2 rounded-lg border bg-info/8 p-4"
              key={`${entry.scene_id}-${index}`}
            >
              <div className="font-medium text-sm">
                {sceneLabel(t, sceneById, entry.scene_id) ?? entry.scene_id}
              </div>
              <p className="text-muted-foreground text-sm">
                {t("report.sections.externalizedFromTo", {
                  from: reportTypeLabel(t, entry.from_type),
                  to: reportTypeLabel(t, entry.to_type),
                })}
              </p>
              <Badge className="w-fit" variant="secondary">
                {entry.scene_id}
              </Badge>
            </div>
          ))}
        </div>
      ) : (
        <EmptySection />
      )}
    </SectionCard>
  );
}

function ForeshadowingSection({
  items,
}: {
  items: string[];
}): React.ReactElement {
  return (
    <SectionCard
      count={items.length}
      icon={ScissorsIcon}
      titleKey="report.sections.foreshadowing"
    >
      {items.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {items.map((item, index) => (
            <Badge key={`${item}-${index}`} variant="secondary">
              {item}
            </Badge>
          ))}
        </div>
      ) : (
        <EmptySection />
      )}
    </SectionCard>
  );
}

function ReviewSection({
  entries,
  sceneById,
  screenplay,
}: {
  entries: ReviewRecommendation[];
  sceneById: Map<string, ScreenplayScene>;
  screenplay: ScreenplayData;
}): React.ReactElement {
  const { t } = useTranslation();
  const sceneOrder = new Map(
    screenplay.scenes.map((scene, index) => [scene.id, index + 1] as const),
  );

  return (
    <SectionCard
      count={entries.length}
      icon={ListChecksIcon}
      titleKey="report.sections.review"
    >
      {entries.length > 0 ? (
        <div className="grid gap-3">
          {entries.map((entry) => {
            const scene = sceneLabel(t, sceneById, entry.scene_id);
            const order = sceneOrder.get(entry.scene_id);
            return (
              <div
                className="grid gap-2 rounded-lg border p-4"
                key={entry.scene_id}
              >
                <div className="font-medium text-sm">
                  {order
                    ? t("script.sceneNumber", { number: order })
                    : entry.scene_id}
                  {scene ? ` · ${scene}` : null}
                </div>
                <p className="text-muted-foreground text-sm">
                  {t("report.sections.reviewReason", {
                    reason: entry.reason,
                  })}
                </p>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptySection />
      )}
    </SectionCard>
  );
}
