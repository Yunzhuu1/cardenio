import * as React from "react";
import {
  CheckCircleIcon,
  ChevronDownIcon,
  FileTextIcon,
  MoreHorizontalIcon,
  PencilIcon,
  PlusIcon,
  ScissorsIcon,
  Trash2Icon,
  TriangleAlertIcon,
  UploadIcon,
} from "lucide-react";
import { Form, Link, useNavigation, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/project-import";
import {
  Accordion,
  AccordionItem,
  AccordionPanel,
  AccordionTrigger,
} from "~/components/ui/accordion";
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
  CardHeader,
  CardPanel,
  CardTitle,
} from "~/components/ui/card";
import { Checkbox } from "~/components/ui/checkbox";
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
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { Field, FieldDescription, FieldLabel } from "~/components/ui/field";
import { Input } from "~/components/ui/input";
import {
  Menu,
  MenuGroup,
  MenuItem,
  MenuPopup,
  MenuSeparator,
  MenuTrigger,
} from "~/components/ui/menu";
import {
  NumberField,
  NumberFieldDecrement,
  NumberFieldGroup,
  NumberFieldIncrement,
  NumberFieldInput,
} from "~/components/ui/number-field";
import { Separator } from "~/components/ui/separator";
import { Textarea } from "~/components/ui/textarea";
import { toastManager } from "~/components/ui/toast";
import {
  ApiError,
  type Chapter,
  type ImportChapterPreview,
  type ProjectId,
  type SourceParagraph,
} from "~/lib/api/types";
import { api } from "~/lib/api/client";
import { i18next } from "~/i18n/config";
import { stagePath } from "~/lib/stages";
import { cn } from "~/lib/utils";

type ActionResult = {
  ok: boolean;
  error?: string;
};

type PreviewChapterDraft = {
  title: string;
  text: string;
  char_count?: number;
  paragraphs?: [number, number];
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}

function splitParagraphs(text: string): SourceParagraph[] {
  return text
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .map((paragraph, index) => ({
      index: index + 1,
      text: paragraph,
    }));
}

function paragraphsToText(chapter: Chapter): string {
  return chapter.paragraphs.map((paragraph) => paragraph.text).join("\n\n");
}

function countChars(paragraphs: SourceParagraph[]): number {
  return paragraphs.reduce(
    (total, paragraph) => total + paragraph.text.length,
    0,
  );
}

function toPreviewDraft(chapter: ImportChapterPreview): PreviewChapterDraft {
  return {
    char_count: chapter.char_count,
    paragraphs: chapter.paragraphs,
    text: chapter.text,
    title: chapter.title,
  };
}

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const projectId = params.projectId as ProjectId;
  const source = await api.source.get(projectId);
  return { source };
}

export async function clientAction({
  params,
  request,
}: Route.ClientActionArgs): Promise<ActionResult> {
  const projectId = params.projectId as ProjectId;
  const form = await request.formData();
  const intent = String(form.get("intent") || "");

  try {
    if (intent === "add-chapter") {
      const title = String(form.get("title") || "").trim();
      const text = String(form.get("text") || "").trim();

      if (!text) {
        throw new Error("Chapter text is required.");
      }

      await api.source.addChapter(projectId, {
        title: title || "Untitled",
        text,
      });
      toastManager.add({
        title: i18next.t("import.addSuccess"),
        type: "success",
      });
      return { ok: true };
    }

    if (intent === "delete-chapter") {
      const chapterId = String(form.get("chapterId") || "");

      if (!chapterId) {
        throw new Error("Missing chapter id.");
      }

      await api.source.deleteChapter(projectId, chapterId);
      toastManager.add({
        title: i18next.t("import.deleteSuccess"),
        type: "success",
      });
      return { ok: true };
    }

    throw new Error("Unknown import action.");
  } catch (error) {
    const message = getErrorMessage(error);
    toastManager.add({
      description: message,
      title: i18next.t("import.actionError"),
      type: "error",
    });
    return { error: message, ok: false };
  }
}

export default function ProjectImport({
  loaderData,
  params,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const { source } = loaderData;
  const navigation = useNavigation();
  const revalidator = useRevalidator();
  const projectId = params.projectId as ProjectId;
  const [previewOpen, setPreviewOpen] = React.useState(false);
  const [previewChapters, setPreviewChapters] = React.useState<
    PreviewChapterDraft[]
  >([]);
  const [previewWarnings, setPreviewWarnings] = React.useState<string[]>([]);
  const [uploading, setUploading] = React.useState(false);
  const [entryMode, setEntryMode] = React.useState<"upload" | "manual">(
    "upload",
  );
  const [confirmingImport, setConfirmingImport] = React.useState(false);
  const [selectedChapterIds, setSelectedChapterIds] = React.useState<string[]>(
    [],
  );
  const [editingChapter, setEditingChapter] = React.useState<Chapter | null>(
    null,
  );
  const [editingText, setEditingText] = React.useState("");
  const [splittingChapter, setSplittingChapter] =
    React.useState<Chapter | null>(null);
  const [splitAt, setSplitAt] = React.useState<number | null>(2);
  const [working, setWorking] = React.useState(false);
  const activeIntent = String(navigation.formData?.get("intent") || "");
  const addingChapter =
    navigation.state !== "idle" && activeIntent === "add-chapter";
  const deletingChapterId =
    navigation.state !== "idle" && activeIntent === "delete-chapter"
      ? String(navigation.formData?.get("chapterId") || "")
      : null;
  const currentChapters = source.stats.chapter_count;
  const hasChapters = currentChapters > 0;
  const minimumChapters = source.threshold.min_chapters;
  const neededChapters = Math.max(0, minimumChapters - currentChapters);
  const validSelectedChapterIds = selectedChapterIds.filter((id) =>
    source.chapters.some((chapter) => chapter.id === id),
  );

  React.useEffect(() => {
    document
      .querySelector('[data-slot="scroll-area-viewport"]')
      ?.scrollTo({ top: 0 });
  }, [entryMode]);

  async function refreshSource(): Promise<void> {
    await revalidator.revalidate();
  }

  async function handleFileSelect(file: File | undefined): Promise<void> {
    if (!file) return;

    try {
      setUploading(true);
      const preview = await api.source.importFile(projectId, file);
      setPreviewChapters(preview.chapters.map(toPreviewDraft));
      setPreviewWarnings(preview.warnings);
      setPreviewOpen(true);
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("import.actionError"),
        type: "error",
      });
    } finally {
      setUploading(false);
    }
  }

  async function handleFileChange(
    event: React.ChangeEvent<HTMLInputElement>,
  ): Promise<void> {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    await handleFileSelect(file);
  }

  async function confirmImport(): Promise<void> {
    try {
      setConfirmingImport(true);
      await api.source.confirmImport(projectId, {
        chapters: previewChapters.map((chapter, index) => ({
          order: index + 1,
          text: chapter.text,
          title: chapter.title || t("import.chapterLabel", { n: index + 1 }),
        })),
      });
      toastManager.add({
        title: t("import.importSuccess"),
        type: "success",
      });
      setPreviewOpen(false);
      setPreviewChapters([]);
      setPreviewWarnings([]);
      setSelectedChapterIds([]);
      await refreshSource();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("import.actionError"),
        type: "error",
      });
    } finally {
      setConfirmingImport(false);
    }
  }

  async function updateChapter(chapter: Chapter, text: string): Promise<void> {
    const paragraphs = splitParagraphs(text);

    try {
      setWorking(true);
      await api.source.updateChapter(projectId, chapter.id, {
        id: chapter.id,
        title: chapter.title,
        order: chapter.order,
        char_count: countChars(paragraphs),
        paragraphs,
      });
      toastManager.add({
        title: t("import.editSuccess"),
        type: "success",
      });
      setEditingChapter(null);
      await refreshSource();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("import.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function splitChapter(): Promise<void> {
    if (!splittingChapter || !splitAt) return;

    try {
      setWorking(true);
      await api.source.resegment(projectId, {
        at_paragraph: splitAt,
        chapter_id: splittingChapter.id,
        op: "split",
      });
      toastManager.add({
        title: t("import.splitSuccess"),
        type: "success",
      });
      setSplittingChapter(null);
      await refreshSource();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("import.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function mergeSelectedChapters(): Promise<void> {
    if (validSelectedChapterIds.length < 2) return;

    const orderedIds = source.chapters
      .filter((chapter) => validSelectedChapterIds.includes(chapter.id))
      .map((chapter) => chapter.id);

    try {
      setWorking(true);
      await api.source.resegment(projectId, {
        chapter_ids: orderedIds,
        new_title: t("import.newMergedTitle"),
        op: "merge",
      });
      toastManager.add({
        title: t("import.mergeSuccess"),
        type: "success",
      });
      setSelectedChapterIds([]);
      await refreshSource();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("import.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  function toggleChapterSelection(chapterId: string, checked: boolean): void {
    setSelectedChapterIds((current) =>
      checked
        ? [...new Set([...current, chapterId])]
        : current.filter((id) => id !== chapterId),
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <section
        className={cn(
          "flex items-center justify-center overflow-hidden transition-[min-height] duration-300 ease-out motion-reduce:transition-none",
          hasChapters ? "min-h-0" : "min-h-[calc(100dvh-11rem)]",
        )}
      >
        {entryMode === "upload" ? (
          <div className="flex w-full max-w-3xl flex-col items-center gap-4">
            <FileUploadCard
              onFileChange={handleFileChange}
              onFileSelect={(file) => void handleFileSelect(file)}
              uploading={uploading}
            />
            <button
              className="text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              onClick={() => setEntryMode("manual")}
              type="button"
            >
              {t("import.manualEntryPrompt")}
            </button>
          </div>
        ) : (
          <div className="flex w-full max-w-3xl flex-col items-center gap-4">
            <ChapterEntryForm
              addingChapter={addingChapter}
              chapterCount={currentChapters}
            />
            <button
              className="text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              onClick={() => setEntryMode("upload")}
              type="button"
            >
              {t("import.uploadEntryPrompt")}
            </button>
          </div>
        )}
      </section>

      <Separator />

      <section className="flex flex-col gap-4">
        {source.chapters.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-muted-foreground">
              {t("import.mergeSelected", {
                count: validSelectedChapterIds.length,
              })}
            </div>
            <AlertDialog>
              <AlertDialogTrigger
                render={
                  <Button
                    disabled={validSelectedChapterIds.length < 2}
                    type="button"
                    variant="outline"
                  />
                }
              >
                {t("import.merge")}
              </AlertDialogTrigger>
              <AlertDialogPopup>
                <AlertDialogHeader>
                  <AlertDialogTitle>{t("import.mergeTitle")}</AlertDialogTitle>
                  <AlertDialogDescription>
                    {t("import.mergeDescription")}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogClose
                    render={<Button type="button" variant="ghost" />}
                  >
                    {t("import.previewCancel")}
                  </AlertDialogClose>
                  <AlertDialogClose
                    render={
                      <Button
                        loading={working}
                        onClick={() => void mergeSelectedChapters()}
                        type="button"
                        variant="destructive"
                      />
                    }
                  >
                    {t("import.mergeConfirm")}
                  </AlertDialogClose>
                </AlertDialogFooter>
              </AlertDialogPopup>
            </AlertDialog>
          </div>
        )}

        {source.chapters.length === 0 ? (
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <FileTextIcon aria-hidden />
              </EmptyMedia>
              <EmptyTitle>{t("steps.import")}</EmptyTitle>
              <EmptyDescription>{t("import.empty")}</EmptyDescription>
            </EmptyHeader>
          </Empty>
        ) : (
          <Accordion multiple>
            {source.chapters.map((chapter) => (
              <ChapterAccordionItem
                chapter={chapter}
                deleting={deletingChapterId === chapter.id}
                key={chapter.id}
                onEdit={() => {
                  setEditingText(paragraphsToText(chapter));
                  setEditingChapter(chapter);
                }}
                onSelect={(checked) =>
                  toggleChapterSelection(chapter.id, checked)
                }
                onSplit={() => {
                  setSplittingChapter(chapter);
                  setSplitAt(2);
                }}
                selected={validSelectedChapterIds.includes(chapter.id)}
              />
            ))}
          </Accordion>
        )}
      </section>

      <ThresholdGate
        currentChapters={currentChapters}
        minimumChapters={minimumChapters}
        neededChapters={neededChapters}
        passed={source.threshold.passed}
        projectId={projectId}
      />

      <ImportPreviewDialog
        confirming={confirmingImport}
        onConfirm={confirmImport}
        onOpenChange={setPreviewOpen}
        onPreviewChange={setPreviewChapters}
        open={previewOpen}
        previewChapters={previewChapters}
        warnings={previewWarnings}
      />

      <EditChapterDialog
        chapter={editingChapter}
        onOpenChange={(open) => {
          if (!open) setEditingChapter(null);
        }}
        onSave={(text) => {
          if (editingChapter) void updateChapter(editingChapter, text);
        }}
        saving={working}
        setText={setEditingText}
        text={editingText}
      />

      <SplitChapterDialog
        chapter={splittingChapter}
        onOpenChange={(open) => {
          if (!open) setSplittingChapter(null);
        }}
        onSplit={() => void splitChapter()}
        setSplitAt={setSplitAt}
        splitAt={splitAt}
        splitting={working}
      />
    </div>
  );
}

function ChapterEntryForm({
  addingChapter,
  chapterCount,
}: {
  addingChapter: boolean;
  chapterCount: number;
}): React.ReactElement {
  const { t } = useTranslation();
  const [title, setTitle] = React.useState("");
  const [text, setText] = React.useState("");
  const previousChapterCount = React.useRef(chapterCount);

  React.useEffect(() => {
    if (chapterCount > previousChapterCount.current) {
      setTitle("");
      setText("");
    }
    previousChapterCount.current = chapterCount;
  }, [chapterCount]);

  return (
    <Form className="flex w-full flex-col gap-5" method="post">
      <input name="intent" type="hidden" value="add-chapter" />
      <Field>
        <FieldLabel htmlFor="chapter-title">
          {t("import.titleLabel")}
        </FieldLabel>
        <Input
          id="chapter-title"
          name="title"
          onChange={(event) => setTitle(event.target.value)}
          placeholder={t("import.titlePlaceholder")}
          type="text"
          value={title}
        />
      </Field>
      <Field>
        <FieldLabel htmlFor="chapter-text">{t("import.textLabel")}</FieldLabel>
        <Textarea
          id="chapter-text"
          name="text"
          onChange={(event) => setText(event.target.value)}
          placeholder={t("import.textPlaceholder")}
          required
          rows={12}
          size="lg"
          value={text}
        />
        <FieldDescription>{t("import.paragraphSpacingHint")}</FieldDescription>
      </Field>
      <div>
        <Button loading={addingChapter} type="submit">
          <PlusIcon aria-hidden data-icon="inline-start" />
          {t("import.addChapter")}
        </Button>
      </div>
    </Form>
  );
}

function FileUploadCard({
  onFileChange,
  onFileSelect,
  uploading,
}: {
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onFileSelect: (file: File | undefined) => void;
  uploading: boolean;
}): React.ReactElement {
  const { t } = useTranslation();
  const [dragging, setDragging] = React.useState(false);

  function handleDragOver(event: React.DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    if (!uploading) setDragging(true);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>): void {
    event.preventDefault();
    setDragging(false);
    if (uploading) return;
    onFileSelect(event.dataTransfer.files[0]);
  }

  return (
    <Card
      className={cn(
        "w-full border-dashed transition-colors",
        dragging && "border-primary bg-primary/5",
      )}
      onDragLeave={() => setDragging(false)}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <CardPanel className="flex flex-col items-center gap-4 px-6 py-10 text-center">
        <div className="flex size-11 items-center justify-center rounded-lg border bg-background text-muted-foreground">
          <UploadIcon aria-hidden className="size-5" />
        </div>
        <div className="flex flex-col gap-1">
          <div className="font-medium text-foreground">
            {t("import.uploadDropTitle")}
          </div>
          <div className="text-sm text-muted-foreground">
            {t("import.uploadDropDescription")}
          </div>
        </div>
        <Input
          accept=".txt,.docx"
          className="sr-only"
          disabled={uploading}
          id="source-file"
          name="file"
          onChange={onFileChange}
          type="file"
        />
        <Button loading={uploading} render={<label htmlFor="source-file" />}>
          {t("import.uploadButton")}
        </Button>
        <div className="text-xs text-muted-foreground">
          {t("import.uploadHint")}
        </div>
      </CardPanel>
    </Card>
  );
}

function ChapterAccordionItem({
  chapter,
  deleting,
  onEdit,
  onSelect,
  onSplit,
  selected,
}: {
  chapter: Chapter;
  deleting: boolean;
  onEdit: () => void;
  onSelect: (checked: boolean) => void;
  onSplit: () => void;
  selected: boolean;
}): React.ReactElement {
  const { t } = useTranslation();
  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const formId = `delete-${chapter.id}`;
  const canSplit = chapter.paragraphs.length >= 2;

  return (
    <>
      <AccordionItem value={chapter.id}>
        <div className="flex items-center gap-3 py-4">
          <div className="flex shrink-0 items-center">
            <Checkbox
              aria-label={`${t("import.selectChapter")} ${chapter.order}`}
              checked={selected}
              onCheckedChange={(checked) => onSelect(checked === true)}
            />
          </div>
          <AccordionTrigger className="group gap-3 self-stretch">
            <div className="flex min-w-0 flex-1 items-center gap-2">
              <div className="shrink-0 text-sm font-normal leading-none text-foreground">
                {t("import.chapterLabel", { n: chapter.order })}
              </div>
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <Badge variant="secondary">
                  {t("import.charCount", { count: chapter.char_count })}
                </Badge>
                <Badge variant="outline">
                  {t("import.paragraphCount", {
                    count: chapter.paragraphs.length,
                  })}
                </Badge>
              </div>
            </div>
            <ChevronDownIcon
              aria-hidden
              className="size-4 shrink-0 text-muted-foreground transition-transform group-data-[panel-open]:rotate-180"
            />
          </AccordionTrigger>
          <Menu>
            <MenuTrigger
              render={
                <Button
                  aria-label={t("import.chapterActions")}
                  className="shrink-0"
                  size="icon"
                  variant="ghost"
                />
              }
            >
              <MoreHorizontalIcon aria-hidden />
            </MenuTrigger>
            <MenuPopup align="end">
              <MenuGroup>
                <MenuItem onClick={onEdit}>
                  <PencilIcon aria-hidden />
                  {t("import.edit")}
                </MenuItem>
                <MenuItem disabled={!canSplit} onClick={onSplit}>
                  <ScissorsIcon aria-hidden />
                  {canSplit ? t("import.split") : t("import.splitUnavailable")}
                </MenuItem>
              </MenuGroup>
              <MenuSeparator />
              <MenuItem
                onClick={() => setDeleteOpen(true)}
                variant="destructive"
              >
                <Trash2Icon aria-hidden />
                {t("import.delete")}
              </MenuItem>
            </MenuPopup>
          </Menu>
        </div>
        <AccordionPanel>
          <div className="flex flex-col gap-4 pb-5 pl-9 pr-3">
            {chapter.paragraphs.map((paragraph) => (
              <p
                className="whitespace-pre-wrap text-sm leading-7 text-foreground"
                key={paragraph.index}
              >
                {paragraph.text}
              </p>
            ))}
          </div>
        </AccordionPanel>
      </AccordionItem>
      <AlertDialog onOpenChange={setDeleteOpen} open={deleteOpen}>
        <AlertDialogPopup>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("import.delete")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("import.deleteConfirm")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <Form className="contents" id={formId} method="post">
            <input name="intent" type="hidden" value="delete-chapter" />
            <input name="chapterId" type="hidden" value={chapter.id} />
          </Form>
          <AlertDialogFooter>
            <AlertDialogClose render={<Button type="button" variant="ghost" />}>
              {t("import.deleteCancel")}
            </AlertDialogClose>
            <AlertDialogClose
              render={
                <Button
                  form={formId}
                  loading={deleting}
                  type="submit"
                  variant="destructive"
                />
              }
            >
              {t("import.deleteConfirmAction")}
            </AlertDialogClose>
          </AlertDialogFooter>
        </AlertDialogPopup>
      </AlertDialog>
    </>
  );
}

function ImportPreviewDialog({
  confirming,
  onConfirm,
  onOpenChange,
  onPreviewChange,
  open,
  previewChapters,
  warnings,
}: {
  confirming: boolean;
  onConfirm: () => Promise<void>;
  onOpenChange: (open: boolean) => void;
  onPreviewChange: React.Dispatch<React.SetStateAction<PreviewChapterDraft[]>>;
  open: boolean;
  previewChapters: PreviewChapterDraft[];
  warnings: string[];
}): React.ReactElement {
  const { t } = useTranslation();
  const [replaceConfirmOpen, setReplaceConfirmOpen] = React.useState(false);

  function updatePreviewChapter(
    index: number,
    field: keyof Pick<PreviewChapterDraft, "text" | "title">,
    value: string,
  ): void {
    onPreviewChange((current) =>
      current.map((chapter, chapterIndex) =>
        chapterIndex === index ? { ...chapter, [field]: value } : chapter,
      ),
    );
  }

  async function handleReplaceConfirm(): Promise<void> {
    await onConfirm();
    setReplaceConfirmOpen(false);
  }

  return (
    <>
      <Dialog onOpenChange={onOpenChange} open={open}>
        <DialogPopup className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>{t("import.previewTitle")}</DialogTitle>
            <DialogDescription>
              {t("import.previewDescription")}
            </DialogDescription>
          </DialogHeader>
          <DialogPanel className="flex max-h-[65dvh] flex-col gap-5">
            {warnings.length > 0 && (
              <Alert variant="warning">
                <TriangleAlertIcon />
                <AlertTitle>{t("import.uploadWarnings")}</AlertTitle>
                <AlertDescription>
                  {warnings.map((warning) => (
                    <span key={warning}>{warning}</span>
                  ))}
                </AlertDescription>
              </Alert>
            )}
            {previewChapters.map((chapter, index) => (
              <Card key={`${index}-${chapter.title}`}>
                <CardHeader>
                  <CardTitle>
                    {t("import.chapterLabel", { n: index + 1 })}
                  </CardTitle>
                  <CardAction>
                    <Button
                      aria-label={t("import.previewRemove")}
                      onClick={() =>
                        onPreviewChange((current) =>
                          current.filter(
                            (_, chapterIndex) => chapterIndex !== index,
                          ),
                        )
                      }
                      size="icon"
                      type="button"
                      variant="ghost"
                    >
                      <Trash2Icon aria-hidden />
                    </Button>
                  </CardAction>
                </CardHeader>
                <CardPanel className="flex flex-col gap-4">
                  <Field>
                    <FieldLabel htmlFor={`preview-title-${index}`}>
                      {t("import.titleLabel")}
                    </FieldLabel>
                    <Input
                      id={`preview-title-${index}`}
                      onChange={(event) =>
                        updatePreviewChapter(index, "title", event.target.value)
                      }
                      type="text"
                      value={chapter.title}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor={`preview-text-${index}`}>
                      {t("import.textLabel")}
                    </FieldLabel>
                    <Textarea
                      id={`preview-text-${index}`}
                      onChange={(event) =>
                        updatePreviewChapter(index, "text", event.target.value)
                      }
                      rows={10}
                      size="lg"
                      value={chapter.text}
                    />
                    <FieldDescription>
                      {t("import.paragraphSpacingHint")}
                    </FieldDescription>
                  </Field>
                </CardPanel>
              </Card>
            ))}
          </DialogPanel>
          <DialogFooter>
            <DialogClose render={<Button type="button" variant="ghost" />}>
              {t("import.previewCancel")}
            </DialogClose>
            <Button
              disabled={previewChapters.length === 0}
              onClick={() => setReplaceConfirmOpen(true)}
              type="button"
              variant="destructive"
            >
              {t("import.previewConfirm")}
            </Button>
          </DialogFooter>
        </DialogPopup>
      </Dialog>
      <AlertDialog
        onOpenChange={setReplaceConfirmOpen}
        open={replaceConfirmOpen}
      >
        <AlertDialogPopup>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("import.replaceWarningTitle")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t("import.replaceWarning")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogClose render={<Button type="button" variant="ghost" />}>
              {t("import.previewCancel")}
            </AlertDialogClose>
            <Button
              loading={confirming}
              onClick={() => void handleReplaceConfirm()}
              type="button"
              variant="destructive"
            >
              {t("import.replaceConfirm")}
            </Button>
          </AlertDialogFooter>
        </AlertDialogPopup>
      </AlertDialog>
    </>
  );
}

function EditChapterDialog({
  chapter,
  onOpenChange,
  onSave,
  saving,
  setText,
  text,
}: {
  chapter: Chapter | null;
  onOpenChange: (open: boolean) => void;
  onSave: (text: string) => void;
  saving: boolean;
  setText: (text: string) => void;
  text: string;
}): React.ReactElement {
  const { t } = useTranslation();

  return (
    <Dialog onOpenChange={onOpenChange} open={Boolean(chapter)}>
      <DialogPopup className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("import.editTitle")}</DialogTitle>
          <DialogDescription>{t("import.editDescription")}</DialogDescription>
        </DialogHeader>
        <DialogPanel>
          <Field>
            <FieldLabel htmlFor="edit-chapter-text">
              {t("import.textLabel")}
            </FieldLabel>
            <Textarea
              id="edit-chapter-text"
              onChange={(event) => setText(event.target.value)}
              rows={14}
              size="lg"
              value={text}
            />
            <FieldDescription>
              {t("import.paragraphSpacingHint")}
            </FieldDescription>
          </Field>
        </DialogPanel>
        <DialogFooter>
          <DialogClose render={<Button type="button" variant="ghost" />}>
            {t("import.previewCancel")}
          </DialogClose>
          <Button
            disabled={!text.trim()}
            loading={saving}
            onClick={() => onSave(text)}
            type="button"
          >
            {t("import.editSave")}
          </Button>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

function SplitChapterDialog({
  chapter,
  onOpenChange,
  onSplit,
  setSplitAt,
  splitAt,
  splitting,
}: {
  chapter: Chapter | null;
  onOpenChange: (open: boolean) => void;
  onSplit: () => void;
  setSplitAt: (value: number | null) => void;
  splitAt: number | null;
  splitting: boolean;
}): React.ReactElement {
  const { t } = useTranslation();
  const maxParagraph = chapter?.paragraphs.length ?? 2;

  return (
    <Dialog onOpenChange={onOpenChange} open={Boolean(chapter)}>
      <DialogPopup>
        <DialogHeader>
          <DialogTitle>{t("import.splitTitle")}</DialogTitle>
          <DialogDescription>{t("import.splitDescription")}</DialogDescription>
        </DialogHeader>
        <DialogPanel>
          <Field>
            <FieldLabel>{t("import.splitAt")}</FieldLabel>
            <NumberField
              max={maxParagraph}
              min={2}
              onValueChange={setSplitAt}
              value={splitAt}
            >
              <NumberFieldGroup>
                <NumberFieldDecrement />
                <NumberFieldInput />
                <NumberFieldIncrement />
              </NumberFieldGroup>
            </NumberField>
            <FieldDescription>
              {t("import.splitAtDescription")}
            </FieldDescription>
          </Field>
        </DialogPanel>
        <DialogFooter>
          <DialogClose render={<Button type="button" variant="ghost" />}>
            {t("import.previewCancel")}
          </DialogClose>
          <Button
            disabled={!splitAt || splitAt < 2 || splitAt > maxParagraph}
            loading={splitting}
            onClick={onSplit}
            type="button"
          >
            {t("import.splitSave")}
          </Button>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

function ThresholdGate({
  currentChapters,
  minimumChapters,
  neededChapters,
  passed,
  projectId,
}: {
  currentChapters: number;
  minimumChapters: number;
  neededChapters: number;
  passed: boolean;
  projectId: ProjectId;
}): React.ReactElement {
  const { t } = useTranslation();

  if (passed) {
    return (
      <Alert variant="success">
        <CheckCircleIcon />
        <AlertTitle>
          {t("import.thresholdMet", { min: minimumChapters })}
        </AlertTitle>
        <AlertDescription>{t("pages.analysis.description")}</AlertDescription>
        <AlertAction>
          <Button render={<Link to={stagePath(projectId, "analysis")} />}>
            {t("import.nextStep")}
          </Button>
        </AlertAction>
      </Alert>
    );
  }

  return (
    <Alert variant="warning">
      <TriangleAlertIcon />
      <AlertTitle>
        {t("import.thresholdUnmet", {
          current: currentChapters,
          need: neededChapters,
        })}
      </AlertTitle>
      <AlertDescription>{t("pages.import.description")}</AlertDescription>
      <AlertAction>
        <Button disabled type="button">
          {t("import.nextStep")}
        </Button>
      </AlertAction>
    </Alert>
  );
}
