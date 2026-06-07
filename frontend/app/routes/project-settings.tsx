import {
  DatabaseIcon,
  LockKeyholeIcon,
  SaveIcon,
  SettingsIcon,
} from "lucide-react";
import type * as React from "react";
import { useState } from "react";
import { useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/project-settings";
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
import { Label } from "~/components/ui/label";
import { Separator } from "~/components/ui/separator";
import { Switch } from "~/components/ui/switch";
import { toastManager } from "~/components/ui/toast";
import { api } from "~/lib/api/client";
import {
  ApiError,
  type ArtifactEnvelope,
  type Project,
  type ProjectId,
  type ProjectSettingsData,
} from "~/lib/api/types";

type SettingsStatus = ArtifactEnvelope<ProjectSettingsData>["state"] | "empty";

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
  const revalidator = useRevalidator();
  const { project, projectId, settings } = loaderData;
  const settingsData = settings?.data ?? fallbackSettings(project);
  const status: SettingsStatus = settings?.state ?? "empty";
  const [form, setForm] = useState({
    shot_hints_enabled: settingsData.shot_hints_enabled,
  });
  const [working, setWorking] = useState(false);

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
              value={project.meta.source_language}
            />
            <LanguageField
              label={t("settings.languages.output")}
              value={project.meta.output_language}
            />
            <p className="rounded-lg border border-dashed bg-muted/24 px-3 py-2 text-muted-foreground text-xs">
              {t("settings.languages.readonlyNote")}
            </p>
          </CardPanel>
        </Card>
      </div>
    </section>
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
