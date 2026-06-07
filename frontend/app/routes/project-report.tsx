import {
  AlertTriangleIcon,
  BotIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  CheckCircle2Icon,
  DownloadIcon,
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
import { Spinner } from "~/components/ui/spinner";
import { toastManager } from "~/components/ui/toast";
import { TrustChips } from "~/components/trust-chips";
import { api } from "~/lib/api/client";
import { api as loaderApi } from "~/lib/api/client";
import {
  ApiError,
  type ArtifactEnvelope,
  type ExportFormat,
  type ExportJob,
  type ExternalizationEntry,
  type ProjectId,
  type ReportData,
  type ReportEntry,
  type ReportMergedEntry,
  type ResolveResponse,
  type ReviewRecommendation,
  type ScreenplayData,
  type ScreenplayScene,
  type SourceRef,
} from "~/lib/api/types";
import {
  flagVariant,
  paragraphLabel,
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

function countFlags(screenplay: ScreenplayData): {
  ai_inferred: number;
  from_source: number;
} {
  return screenplay.scenes.reduce(
    (counts, scene) => {
      for (const beat of scene.beats) {
        if (beat.type === "todo") continue;
        if (beat.flag === "from_source") counts.from_source += 1;
        if (beat.flag === "ai_inferred") counts.ai_inferred += 1;
      }
      return counts;
    },
    { ai_inferred: 0, from_source: 0 },
  );
}

type SourcePreviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { response: ResolveResponse; status: "success" }
  | { status: "error" };

const exportFileExtensions: Record<ExportFormat, string> = {
  yaml: "yaml",
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForExportJob(
  projectId: ProjectId,
  initialJob: ExportJob,
): Promise<ExportJob> {
  let job = initialJob;
  for (let attempt = 0; attempt < 20 && job.status === "running"; attempt += 1) {
    await sleep(1000);
    if (!api.export) throw new Error("Export API is unavailable");
    job = await api.export.get(projectId, job.id);
  }
  return job;
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default function ProjectReport({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const revalidator = useRevalidator();
  const { projectId, report, screenplay } = loaderData;
  const [working, setWorking] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(
    null,
  );
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

  async function exportReport(format: ExportFormat): Promise<void> {
    if (!report || !screenplay || !api.export) return;

    try {
      setExportingFormat(format);
      const created = await api.export.create(projectId, {
        format,
        shot_hints: screenplay.data.shot_hints.enabled,
        version: report.version,
      });
      const job = await waitForExportJob(projectId, created.export);

      if (job.status !== "completed") {
        throw new Error(t("report.export.notReady"));
      }

      const blob = await api.export.downloadFile(projectId, job.id);
      downloadBlob(
        blob,
        `cardenio-${projectId}.${exportFileExtensions[format]}`,
      );
      toastManager.add({
        title: t("report.export.success", {
          format: t(`report.export.formats.${format}`),
        }),
        type: "success",
      });
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("report.export.error"),
        type: "error",
      });
    } finally {
      setExportingFormat(null);
    }
  }

  return (
    <section className="space-y-4">
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
            exportingFormat={exportingFormat}
            onExport={exportReport}
            onRegenerate={generateReport}
            report={report}
            working={working}
          />
          <ReportConsistencyAlert
            onRegenerate={generateReport}
            report={report.data}
            screenplay={screenplay.data}
            working={working}
          />
          <ReportSections
            projectId={projectId}
            report={report.data}
            sceneById={sceneById}
            screenplay={screenplay.data}
          />
        </>
      ) : null}
    </section>
  );
}

function ReportConsistencyAlert({
  onRegenerate,
  report,
  screenplay,
  working,
}: {
  onRegenerate: () => Promise<void>;
  report: ReportData;
  screenplay: ScreenplayData;
  working: boolean;
}): React.ReactElement {
  const { t } = useTranslation();
  const recomputed = countFlags(screenplay);
  const consistent =
    recomputed.from_source === report.from_source_lines &&
    recomputed.ai_inferred === report.ai_inferred_lines;

  if (consistent) {
    return (
      <Alert variant="success">
        <CheckCircle2Icon />
        <AlertTitle>{t("report.consistency.consistentTitle")}</AlertTitle>
        <AlertDescription>
          {t("report.consistency.consistentDescription", {
            aiInferred: recomputed.ai_inferred,
            fromSource: recomputed.from_source,
          })}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Alert variant="warning">
      <AlertTriangleIcon />
      <AlertTitle>{t("report.consistency.staleTitle")}</AlertTitle>
      <AlertDescription>
        <span>{t("report.consistency.staleDescription")}</span>
        <span>
          {t("report.consistency.fromSourceDiff", {
            actual: recomputed.from_source,
            reported: report.from_source_lines,
          })}
        </span>
        <span>
          {t("report.consistency.aiInferredDiff", {
            actual: recomputed.ai_inferred,
            reported: report.ai_inferred_lines,
          })}
        </span>
      </AlertDescription>
      <AlertAction>
        <Button
          disabled={working}
          loading={working}
          onClick={onRegenerate}
          size="sm"
        >
          <RefreshCwIcon />
          {t("report.consistency.regenerate")}
        </Button>
      </AlertAction>
    </Alert>
  );
}

function ReportSummaryCard({
  exportingFormat,
  onExport,
  onRegenerate,
  report,
  working,
}: {
  exportingFormat: ExportFormat | null;
  onExport: (format: ExportFormat) => Promise<void>;
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
          <div className="flex flex-wrap justify-end gap-2">
            <Button
              disabled={working || exportingFormat !== null}
              loading={exportingFormat === "yaml"}
              onClick={() => void onExport("yaml")}
              size="sm"
              variant="outline"
            >
              <DownloadIcon />
              {t("report.export.button")}
            </Button>
            <AlertDialog>
              <AlertDialogTrigger
                render={
                  <Button disabled={working} size="sm" variant="outline" />
                }
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
          </div>
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
  projectId,
  report,
  sceneById,
  screenplay,
}: {
  projectId: ProjectId;
  report: ReportData;
  sceneById: Map<string, ScreenplayScene>;
  screenplay: ScreenplayData;
}): React.ReactElement {
  return (
    <div className="grid gap-4">
      <ReportEntrySection
        entries={report.kept}
        icon={FileTextIcon}
        projectId={projectId}
        sceneById={sceneById}
        titleKey="report.sections.kept"
      />
      <ReportEntrySection
        entries={report.added}
        icon={BotIcon}
        projectId={projectId}
        sceneById={sceneById}
        titleKey="report.sections.added"
      />
      <ReportEntrySection
        entries={report.deleted}
        icon={Trash2Icon}
        projectId={projectId}
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
  projectId,
  sceneById,
  titleKey,
}: {
  entries: ReportEntry[];
  icon: React.ComponentType<{ className?: string }>;
  projectId: ProjectId;
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
              projectId={projectId}
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
  projectId,
  sceneById,
}: {
  entry: ReportEntry;
  index: number;
  projectId: ProjectId;
  sceneById: Map<string, ScreenplayScene>;
}): React.ReactElement {
  const { t } = useTranslation();
  const scene = sceneLabel(t, sceneById, entry.scene_id);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [preview, setPreview] = useState<SourcePreviewState>({
    status: "idle",
  });

  async function loadSourcePreview(sourceRef: SourceRef): Promise<void> {
    if (preview.status !== "idle") return;
    try {
      setPreview({ status: "loading" });
      const response = await api.source.resolve(
        projectId,
        sourceRef.chapter,
        paragraphLabel(sourceRef.paragraphs),
      );
      setPreview({ response, status: "success" });
    } catch {
      setPreview({ status: "error" });
    }
  }

  function handlePreviewOpen(open: boolean): void {
    setPreviewOpen(open);
    if (open && entry.source_ref) {
      void loadSourcePreview(entry.source_ref);
    }
  }

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
      {entry.source_ref ? (
        <Collapsible onOpenChange={handlePreviewOpen} open={previewOpen}>
          <CollapsibleTrigger render={<Button size="sm" variant="ghost" />}>
            {previewOpen ? (
              <ChevronDownIcon aria-hidden />
            ) : (
              <ChevronRightIcon aria-hidden />
            )}
            {t(previewOpen ? "report.preview.hide" : "report.preview.show")}
          </CollapsibleTrigger>
          <CollapsiblePanel className="mt-1">
            <SourcePreviewPanel preview={preview} />
          </CollapsiblePanel>
        </Collapsible>
      ) : null}
    </div>
  );
}

function SourcePreviewPanel({
  preview,
}: {
  preview: SourcePreviewState;
}): React.ReactElement {
  const { t } = useTranslation();

  if (preview.status === "idle" || preview.status === "loading") {
    return (
      <div className="flex items-center gap-2 rounded-lg border bg-muted/32 p-3 text-muted-foreground text-sm">
        <Spinner aria-label={t("report.preview.loading")} className="size-4" />
        {t("report.preview.loading")}
      </div>
    );
  }

  if (preview.status === "error") {
    return (
      <Alert variant="warning">
        <AlertTriangleIcon />
        <AlertTitle>{t("report.preview.missing")}</AlertTitle>
      </Alert>
    );
  }

  return (
    <div className="grid gap-2 rounded-lg border bg-muted/32 p-3">
      {preview.response.paragraphs.map((paragraph) => (
        <div
          className="grid gap-1 rounded-md bg-background p-3"
          key={paragraph.index}
        >
          <Badge className="w-fit" variant="secondary">
            {t("report.preview.paragraph", { index: paragraph.index })}
          </Badge>
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            {paragraph.text}
          </p>
        </div>
      ))}
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
