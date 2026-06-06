import { PlusIcon } from "lucide-react";
import { Form, Link, redirect, useNavigation } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/overview";
import { Button } from "~/components/ui/button";
import { api } from "~/lib/api/client";
import { stagePath } from "~/lib/stages";
import type { UiLanguage } from "~/lib/api/types";

export function meta() {
  return [
    { title: "Cardenio 入戏" },
    { name: "description", content: "AI-assisted novel-to-script adaptation." },
  ];
}

export async function clientLoader() {
  const { items } = await api.projects.list();
  return { projects: items };
}

export async function clientAction({ request }: Route.ClientActionArgs) {
  const form = await request.formData();
  const title = String(form.get("title") || "Untitled");
  const language = String(form.get("language") || "zh-CN") as UiLanguage;
  const project = await api.projects.create({
    title,
    ui_language: language,
    source_language: language,
    output_language: language,
    adaptation_direction: null,
  });
  return redirect(stagePath(project.id, "import"));
}

export default function Overview({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t, i18n } = useTranslation();
  const { projects } = loaderData;
  const navigation = useNavigation();
  const creating = navigation.state !== "idle";

  return (
    <div className="mx-auto w-full max-w-5xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-balance text-foreground">
            {t("overview.title")}
          </h1>
          <p className="mt-2 max-w-2xl text-base leading-7 text-muted-foreground">
            {t("overview.description")}
          </p>
        </div>
        <Form method="post">
          <input
            name="title"
            type="hidden"
            value={t("overview.newProjectTitle")}
          />
          <input
            name="language"
            type="hidden"
            value={i18n.resolvedLanguage || "zh-CN"}
          />
          <Button loading={creating} type="submit">
            <PlusIcon aria-hidden />
            {t("overview.newProject")}
          </Button>
        </Form>
      </div>

      {projects.length === 0 ? (
        <div className="mt-10 rounded-lg border border-dashed border-border p-10 text-center text-muted-foreground">
          {t("overview.empty")}
        </div>
      ) : (
        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link
              className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/40"
              key={project.id}
              to={`/projects/${project.id}`}
            >
              <div className="app-heading font-medium text-balance text-foreground">
                {project.title}
              </div>
              <div className="text-sm text-muted-foreground">
                {t(`state.${project.state}`)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
