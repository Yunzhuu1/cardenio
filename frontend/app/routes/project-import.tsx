import {
  CheckCircleIcon,
  ChevronDownIcon,
  FileTextIcon,
  InfoIcon,
  PlusIcon,
  Trash2Icon,
  TriangleAlertIcon,
} from "lucide-react";
import { Form, Link, useNavigation } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/project-import";
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
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { Field, FieldDescription, FieldLabel } from "~/components/ui/field";
import { Input } from "~/components/ui/input";
import { Separator } from "~/components/ui/separator";
import { Textarea } from "~/components/ui/textarea";
import { toastManager } from "~/components/ui/toast";
import { ApiError, type Chapter, type ProjectId } from "~/lib/api/types";
import { api } from "~/lib/api/client";
import { i18next } from "~/i18n/config";
import { stagePath } from "~/lib/stages";

type ActionResult = {
  ok: boolean;
  error?: string;
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
  const projectId = params.projectId as ProjectId;
  const activeIntent = String(navigation.formData?.get("intent") || "");
  const addingChapter =
    navigation.state !== "idle" && activeIntent === "add-chapter";
  const deletingChapterId =
    navigation.state !== "idle" && activeIntent === "delete-chapter"
      ? String(navigation.formData?.get("chapterId") || "")
      : null;
  const currentChapters = source.stats.chapter_count;
  const minimumChapters = source.threshold.min_chapters;
  const neededChapters = Math.max(0, minimumChapters - currentChapters);

  return (
    <div className="flex flex-col gap-8">
      <header className="flex max-w-3xl flex-col gap-3">
        <div className="text-sm font-medium text-muted-foreground">
          {t("pages.import.milestone")}
        </div>
        <div className="flex flex-col gap-2">
          <h1 className="app-heading text-3xl font-semibold text-foreground">
            {t("pages.import.title")}
          </h1>
          <p className="max-w-2xl text-muted-foreground">
            {t("pages.import.description")}
          </p>
        </div>
      </header>

      <Alert variant="info">
        <InfoIcon />
        <AlertTitle>{t("import.titleNotPersistedHint")}</AlertTitle>
        <AlertDescription>{t("import.paragraphSpacingHint")}</AlertDescription>
      </Alert>

      <Form className="flex max-w-3xl flex-col gap-5" method="post">
        <input name="intent" type="hidden" value="add-chapter" />
        <Field>
          <FieldLabel htmlFor="chapter-title">
            {t("import.titleLabel")}
          </FieldLabel>
          <Input
            id="chapter-title"
            name="title"
            placeholder={t("import.titlePlaceholder")}
            type="text"
          />
        </Field>
        <Field>
          <FieldLabel htmlFor="chapter-text">
            {t("import.textLabel")}
          </FieldLabel>
          <Textarea
            id="chapter-text"
            name="text"
            placeholder={t("import.textPlaceholder")}
            required
            rows={12}
            size="lg"
          />
          <FieldDescription>
            {t("import.paragraphSpacingHint")}
          </FieldDescription>
        </Field>
        <div>
          <Button loading={addingChapter} type="submit">
            <PlusIcon aria-hidden data-icon="inline-start" />
            {t("import.addChapter")}
          </Button>
        </div>
      </Form>

      <Separator />

      <section className="flex flex-col gap-4">
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
          <div className="grid gap-4">
            {source.chapters.map((chapter) => (
              <ChapterCard
                chapter={chapter}
                deleting={deletingChapterId === chapter.id}
                key={chapter.id}
              />
            ))}
          </div>
        )}
      </section>

      <ThresholdGate
        currentChapters={currentChapters}
        minimumChapters={minimumChapters}
        neededChapters={neededChapters}
        passed={source.threshold.passed}
        projectId={projectId}
      />
    </div>
  );
}

function ChapterCard({
  chapter,
  deleting,
}: {
  chapter: Chapter;
  deleting: boolean;
}): React.ReactElement {
  const { t } = useTranslation();
  const formId = `delete-${chapter.id}`;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("import.chapterLabel", { n: chapter.order })}</CardTitle>
        <CardDescription className="flex flex-wrap gap-2">
          <Badge variant="secondary">
            {t("import.charCount", { count: chapter.char_count })}
          </Badge>
          <Badge variant="outline">
            {t("import.paragraphCount", {
              count: chapter.paragraphs.length,
            })}
          </Badge>
        </CardDescription>
        <CardAction>
          <AlertDialog>
            <AlertDialogTrigger
              render={
                <Button
                  aria-label={t("import.delete")}
                  size="icon"
                  variant="destructive-outline"
                />
              }
            >
              <Trash2Icon aria-hidden data-icon="inline-start" />
            </AlertDialogTrigger>
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
                <AlertDialogClose
                  render={<Button type="button" variant="ghost" />}
                >
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
        </CardAction>
      </CardHeader>
      <CardPanel>
        <Collapsible>
          <CollapsibleTrigger className="inline-flex items-center gap-2 text-sm font-medium text-foreground hover:text-primary">
            {t("import.previewToggle")}
            <ChevronDownIcon aria-hidden data-icon="inline-end" />
          </CollapsibleTrigger>
          <CollapsiblePanel>
            <div className="mt-4 flex flex-col gap-3 rounded-lg border border-border bg-muted/40 p-4">
              <div className="text-sm font-medium text-foreground">
                {t("import.sourcePreview")}
              </div>
              <div className="flex flex-col gap-4">
                {chapter.paragraphs.map((paragraph) => (
                  <p
                    className="whitespace-pre-wrap text-sm leading-7 text-foreground"
                    key={paragraph.index}
                  >
                    {paragraph.text}
                  </p>
                ))}
              </div>
            </div>
          </CollapsiblePanel>
        </Collapsible>
      </CardPanel>
    </Card>
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
