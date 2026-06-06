import type { LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { stages } from "~/lib/stages";

export function StagePlaceholder({
  stageKey,
  icon,
}: {
  stageKey: string;
  icon?: LucideIcon;
}): React.ReactElement {
  const { t } = useTranslation();
  const Icon = icon ?? stages.find((stage) => stage.key === stageKey)?.icon;

  return (
    <section className="flex min-h-[40dvh] flex-col items-start justify-center gap-4">
      <span className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
        {t(`pages.${stageKey}.milestone`)} · {t("placeholder.badge")}
      </span>
      <div className="flex items-center gap-3">
        {Icon && (
          <span className="flex size-10 items-center justify-center rounded-lg border border-border bg-card text-primary">
            <Icon aria-hidden className="size-5" />
          </span>
        )}
        <h2 className="text-xl font-semibold tracking-normal text-foreground">
          {t(`pages.${stageKey}.title`)}
        </h2>
      </div>
      <p className="max-w-2xl text-base leading-7 text-muted-foreground">
        {t(`pages.${stageKey}.description`)}
      </p>
      <p className="text-sm text-muted-foreground">{t("placeholder.note")}</p>
    </section>
  );
}
