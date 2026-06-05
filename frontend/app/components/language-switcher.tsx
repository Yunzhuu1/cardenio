import { LanguagesIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "~/components/ui/button";
import { uiLanguages, type UiLanguage } from "~/i18n/languages";

export function LanguageSwitcher(): React.ReactElement {
  const { i18n, t } = useTranslation();
  const currentLanguage = (i18n.resolvedLanguage || "zh-CN") as UiLanguage;

  return (
    <div
      aria-label={t("language.label")}
      className="inline-flex items-center gap-1 rounded-lg border border-border bg-card p-1"
      role="group"
    >
      <LanguagesIcon
        aria-hidden
        className="mx-2 size-4 text-muted-foreground"
      />
      {uiLanguages.map((language) => (
        <Button
          aria-pressed={currentLanguage === language}
          key={language}
          onClick={() => void i18n.changeLanguage(language)}
          size="sm"
          variant={currentLanguage === language ? "secondary" : "ghost"}
        >
          {t(`language.${language}`)}
        </Button>
      ))}
    </div>
  );
}
