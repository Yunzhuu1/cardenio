import {
  DatabaseIcon,
  LockKeyholeIcon,
  SaveIcon,
  SettingsIcon,
  Trash2Icon,
} from "lucide-react";
import type * as React from "react";
import { useState } from "react";
import { useNavigate, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/project-settings";
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
import { Field, FieldDescription, FieldLabel } from "~/components/ui/field";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import {
  Select,
  SelectItem,
  SelectPopup,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { Separator } from "~/components/ui/separator";
import { Switch } from "~/components/ui/switch";
import { toastManager } from "~/components/ui/toast";
import { api } from "~/lib/api/client";
import {
  ApiError,
  type AdaptationDirection,
  type ArtifactEnvelope,
  type CreateProjectInput,
  type MvpDirection,
  type Project,
  type ProjectId,
  type ProjectSettingsData,
  type SourceLanguage,
} from "~/lib/api/types";

type SettingsStatus = ArtifactEnvelope<ProjectSettingsData>["state"] | "empty";
type SelectOption<T extends string> = {
  label: string;
  value: T;
};
type ProjectFormState = {
  adaptation_direction: AdaptationDirection | null;
  output_language: CreateProjectInput["output_language"];
  source_language: SourceLanguage;
  title: string;
};

const sourceLanguageOptions: SourceLanguage[] = [
  "zh-CN",
  "en",
  "mixed",
  "unknown",
];
const outputLanguageOptions: CreateProjectInput["output_language"][] = [
  "zh-CN",
  "en",
];
const directionOptions: MvpDirection[] = [
  "faithful",
  "cinematic",
  "short_drama",
];

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

function statusVariant(
  state: SettingsStatus,
): "default" | "secondary" | "success" | "warning" {
  if (state === "confirmed") return "success";
  if (state === "draft") return "warning";
  if (state === "needs_recompute") return "warning";
  return "secondary";
}

function fallbackSettings(project: Project): ProjectSettingsData {
  return {
    ui_language: project.meta.ui_language,
    source_language: project.meta.source_language,
    output_language: project.meta.output_language,
    data_storage_location: "configured_sqlite_database",
    data_storage_notice: "",
    allow_model_training: false,
    training_notice: "",
    local_processing_reserved: true,
    local_processing_notice: "",
    shot_hints_enabled: false,
  };
}

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const projectId = params.projectId as ProjectId;
  const [settings, project] = await Promise.all([
    getOrNull(api.settings.get(projectId)),
    api.projects.get(projectId),
  ]);
  return { project, projectId, settings };
}

export default function ProjectSettings({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const revalidator = useRevalidator();
  const { project, projectId, settings } = loaderData;
  const settingsData = settings?.data ?? fallbackSettings(project);
  const status: SettingsStatus = settings?.state ?? "empty";
  const [projectForm, setProjectForm] = useState<ProjectFormState>({
    adaptation_direction: project.meta.adaptation_direction,
    output_language: project.meta.output_language,
    source_language: project.meta.source_language,
    title: project.title,
  });
  const [form, setForm] = useState({
    shot_hints_enabled: settingsData.shot_hints_enabled,
  });
  const [working, setWorking] = useState(false);
  const [projectWorking, setProjectWorking] = useState(false);
  const [deleteWorking, setDeleteWorking] = useState(false);

  async function saveSettings(): Promise<void> {
    try {
      setWorking(true);
      const payload: ProjectSettingsData = {
        ...settingsData,
        shot_hints_enabled: form.shot_hints_enabled,
      };
      await api.settings.update(projectId, payload);
      toastManager.add({
        title: t("settings.save.successTitle"),
        type: "success",
      });
      await revalidator.revalidate();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("settings.save.errorTitle"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function saveProject(): Promise<void> {
    try {
      setProjectWorking(true);
      const title = projectForm.title.trim();
      await api.projects.patch(projectId, {
        adaptation_direction: projectForm.adaptation_direction,
        output_language: projectForm.output_language,
        source_language: projectForm.source_language,
        title: title || project.title,
      });
      toastManager.add({
        title: t("settings.project.saveSuccessTitle"),
        type: "success",
      });
      await revalidator.revalidate();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("settings.project.saveErrorTitle"),
        type: "error",
      });
    } finally {
      setProjectWorking(false);
    }
  }

  async function deleteProject(): Promise<void> {
    try {
      setDeleteWorking(true);
      await api.projects.remove(projectId);
      toastManager.add({
        title: t("settings.danger.deleteSuccessTitle"),
        type: "success",
      });
      navigate("/", { replace: true });
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("settings.danger.deleteErrorTitle"),
        type: "error",
      });
      setDeleteWorking(false);
    }
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="mb-2 text-sm font-medium text-muted-foreground">
            {t("pages.settings.milestone")}
          </div>
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-lg border border-border bg-card text-primary">
              <SettingsIcon aria-hidden className="size-5" />
            </span>
            <h2 className="app-heading text-2xl">
              {t("pages.settings.title")}
            </h2>
          </div>
          <p className="mt-2 max-w-3xl text-muted-foreground text-sm">
            {t("pages.settings.description")}
          </p>
        </div>
        <Badge variant={statusVariant(status)}>
          {t(`settings.status.${status}`)}
        </Badge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(22rem,0.8fr)]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t("settings.project.title")}</CardTitle>
              <CardDescription>
                {t("settings.project.description")}
              </CardDescription>
              <CardAction>
                <Button loading={projectWorking} onClick={saveProject}>
                  <SaveIcon aria-hidden />
                  {t("settings.project.saveButton")}
                </Button>
              </CardAction>
            </CardHeader>
            <CardPanel className="grid gap-4 sm:grid-cols-2">
              <Field className="sm:col-span-2">
                <FieldLabel htmlFor="project-title">
                  {t("settings.project.name")}
                </FieldLabel>
                <Input
                  id="project-title"
                  onChange={(event) =>
                    setProjectForm((current) => ({
                      ...current,
                      title: event.target.value,
                    }))
                  }
                  value={projectForm.title}
                />
              </Field>
              <SelectField
                items={sourceLanguageOptions.map((value) => ({
                  label: t(`settings.languages.values.${value}`),
                  value,
                }))}
                label={t("settings.languages.source")}
                onChange={(source_language) =>
                  setProjectForm((current) => ({ ...current, source_language }))
                }
                value={projectForm.source_language}
              />
              <SelectField
                items={outputLanguageOptions.map((value) => ({
                  label: t(`settings.languages.values.${value}`),
                  value,
                }))}
                label={t("settings.languages.output")}
                onChange={(output_language) =>
                  setProjectForm((current) => ({ ...current, output_language }))
                }
                value={projectForm.output_language}
              />
              <SelectField
                items={[
                  {
                    label: t("settings.direction.none"),
                    value: "none",
                  },
                  ...directionOptions.map((value) => ({
                    label: t(`settings.direction.values.${value}`),
                    value,
                  })),
                ]}
                label={t("settings.direction.label")}
                onChange={(value) =>
                  setProjectForm((current) => ({
                    ...current,
                    adaptation_direction:
                      value === "none" ? null : (value as MvpDirection),
                  }))
                }
                value={projectForm.adaptation_direction ?? "none"}
              />
            </CardPanel>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("settings.privacy.title")}</CardTitle>
              <CardDescription>
                {t("settings.privacy.description")}
              </CardDescription>
            </CardHeader>
            <CardPanel className="space-y-4">
              <SettingSwitchRow
                checked={false}
                description={t("settings.privacy.training.description")}
                disabled
                id="allow-model-training"
                label={t("settings.privacy.training.label")}
                notice={settingsData.training_notice}
                status={
                  <Badge variant="success">
                    {t("settings.privacy.training.badge")}
                  </Badge>
                }
              />

              <Separator />

              <InfoRow
                description={t("settings.privacy.storage.description")}
                icon={<DatabaseIcon aria-hidden className="size-4" />}
                label={t("settings.privacy.storage.label")}
                notice={settingsData.data_storage_notice}
                value={t(
                  `settings.privacy.storage.locations.${settingsData.data_storage_location}`,
                )}
              />

              <Separator />

              <InfoRow
                description={t("settings.privacy.local.description")}
                icon={<LockKeyholeIcon aria-hidden className="size-4" />}
                label={t("settings.privacy.local.label")}
                notice={settingsData.local_processing_notice}
                status={
                  <Badge variant="success">
                    {t("settings.privacy.local.badge")}
                  </Badge>
                }
              />
            </CardPanel>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("settings.generation.title")}</CardTitle>
              <CardDescription>
                {t("settings.generation.description")}
              </CardDescription>
              <CardAction>
                <Button loading={working} onClick={saveSettings}>
                  <SaveIcon aria-hidden />
                  {t("settings.save.button")}
                </Button>
              </CardAction>
            </CardHeader>
            <CardPanel>
              <SettingSwitchRow
                checked={form.shot_hints_enabled}
                description={t("settings.generation.shotHints.description")}
                id="shot-hints-enabled"
                label={t("settings.generation.shotHints.label")}
                onCheckedChange={(value) =>
                  setForm((current) => ({
                    ...current,
                    shot_hints_enabled: value,
                  }))
                }
              />
            </CardPanel>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{t("settings.languages.title")}</CardTitle>
            <CardDescription>
              {t("settings.languages.description")}
            </CardDescription>
          </CardHeader>
          <CardPanel className="space-y-4">
            <LanguageField
              label={t("settings.languages.ui")}
              value={project.meta.ui_language}
            />
            <LanguageField
              label={t("settings.languages.source")}
              value={projectForm.source_language}
            />
            <LanguageField
              label={t("settings.languages.output")}
              value={projectForm.output_language}
            />
            <p className="rounded-lg border border-dashed bg-muted/24 px-3 py-2 text-muted-foreground text-xs">
              {t("settings.languages.readonlyNote")}
            </p>
          </CardPanel>
        </Card>

        <Card className="border-destructive/32 xl:col-start-2">
          <CardHeader>
            <CardTitle>{t("settings.danger.title")}</CardTitle>
            <CardDescription>
              {t("settings.danger.description")}
            </CardDescription>
            <CardAction>
              <AlertDialog>
                <AlertDialogTrigger
                  render={
                    <Button type="button" variant="destructive">
                      <Trash2Icon aria-hidden />
                      {t("settings.danger.deleteButton")}
                    </Button>
                  }
                />
                <AlertDialogPopup>
                  <AlertDialogHeader>
                    <AlertDialogTitle>
                      {t("settings.danger.deleteTitle")}
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                      {t("settings.danger.deleteDescription", {
                        title: project.title,
                      })}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogClose
                      render={<Button type="button" variant="outline" />}
                    >
                      {t("settings.danger.cancel")}
                    </AlertDialogClose>
                    <Button
                      loading={deleteWorking}
                      onClick={() => void deleteProject()}
                      type="button"
                      variant="destructive"
                    >
                      {t("settings.danger.confirmDelete")}
                    </Button>
                  </AlertDialogFooter>
                </AlertDialogPopup>
              </AlertDialog>
            </CardAction>
          </CardHeader>
        </Card>
      </div>
    </section>
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
    <Field>
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

function SettingSwitchRow({
  checked,
  description,
  disabled = false,
  id,
  label,
  notice,
  onCheckedChange,
  status,
}: {
  checked: boolean;
  description: string;
  disabled?: boolean;
  id: string;
  label: string;
  notice?: string;
  onCheckedChange?: (checked: boolean) => void;
  status?: React.ReactNode;
}): React.ReactElement {
  return (
    <div className="flex items-start justify-between gap-4 rounded-lg border bg-background p-3">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <Label htmlFor={id}>{label}</Label>
          {status}
        </div>
        <p className="text-muted-foreground text-sm">{description}</p>
        {notice ? (
          <p className="text-muted-foreground/80 text-xs">{notice}</p>
        ) : null}
      </div>
      <Switch
        checked={checked}
        disabled={disabled}
        id={id}
        onCheckedChange={onCheckedChange}
      />
    </div>
  );
}

function InfoRow({
  description,
  icon,
  label,
  notice,
  status,
  value,
}: {
  description: string;
  icon: React.ReactNode;
  label: string;
  notice?: string;
  status?: React.ReactNode;
  value?: string;
}): React.ReactElement {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md border bg-muted/32 text-muted-foreground">
        {icon}
      </span>
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <div className="font-medium text-sm">{label}</div>
          {value ? <Badge variant="secondary">{value}</Badge> : null}
          {status}
        </div>
        <p className="text-muted-foreground text-sm">{description}</p>
        {notice ? (
          <p className="text-muted-foreground/80 text-xs">{notice}</p>
        ) : null}
      </div>
    </div>
  );
}

function LanguageField({
  label,
  value,
}: {
  label: string;
  value: string;
}): React.ReactElement {
  const { t } = useTranslation();
  return (
    <Field>
      <FieldLabel>{label}</FieldLabel>
      <Badge variant="secondary">
        {t(`settings.languages.values.${value}`)}
      </Badge>
      <FieldDescription>{value}</FieldDescription>
    </Field>
  );
}
