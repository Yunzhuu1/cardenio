import type { Route } from "./+types/home";
import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "~/components/language-switcher";
import { ThemeToggle } from "~/components/theme-toggle";

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
      <div className="mx-auto flex min-h-dvh w-full max-w-5xl flex-col px-6 py-6">
        <header className="flex items-center justify-end gap-3">
          <LanguageSwitcher />
          <ThemeToggle />
        </header>

        <section className="flex flex-1 flex-col justify-center py-16">
          <p className="mb-4 text-sm font-medium text-primary">
            {t("home.eyebrow")}
          </p>
          <h1 className="max-w-3xl text-4xl font-semibold tracking-normal text-foreground">
            {t("home.title")}
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground">
            {t("home.summary")}
          </p>
        </section>
      </div>
    </main>
  );
}
