import type { Route } from "./+types/home";
import { ArrowRightIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "~/components/language-switcher";
import { ThemeToggle } from "~/components/theme-toggle";
import { TrustChips } from "~/components/trust-chips";
import { Button } from "~/components/ui/button";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "Cardenio 入戏" },
    { name: "description", content: "AI-assisted novel-to-script adaptation." },
  ];
}

export default function Home(): React.ReactElement {
  const { t } = useTranslation();

  return (
    <main className="min-h-dvh bg-background text-foreground">
      <div className="mx-auto flex min-h-dvh w-full max-w-6xl flex-col px-5 py-5 sm:px-8 sm:py-6">
        <header className="flex items-center justify-between gap-3">
          <div className="text-sm font-semibold text-foreground">
            {t("app.name")}
          </div>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <ThemeToggle />
          </div>
        </header>

        <section className="grid flex-1 items-center gap-10 py-12 lg:grid-cols-[0.92fr_1.08fr] lg:py-16">
          <div>
            <p className="mb-4 text-sm font-medium text-primary">
              {t("home.eyebrow")}
            </p>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-normal text-foreground sm:text-5xl">
              {t("home.title")}
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground">
              {t("home.summary")}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button>
                {t("home.stage")}
                <ArrowRightIcon aria-hidden />
              </Button>
              <Button variant="outline">{t("trust.todo")}</Button>
            </div>
          </div>

          <div>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <TrustChips />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <article className="rounded-md border border-border bg-background p-4">
                <p className="mb-3 font-mono text-xs text-primary">
                  {t("trust.source")}
                </p>
                <p className="font-serif text-[17px] leading-8 text-foreground">
                  {t("home.sourceText")}
                </p>
              </article>
              <article className="rounded-md border border-inferred/30 bg-inferred/10 p-4">
                <p className="mb-3 font-mono text-xs text-inferred">
                  {t("trust.inferred")}
                </p>
                <p className="font-serif text-[17px] leading-8 text-foreground">
                  {t("home.scriptText")}
                </p>
              </article>
            </div>
            <p className="mt-4 rounded-md border border-todo border-dashed px-3 py-2 text-sm text-muted-foreground">
              {t("home.note")}
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
