import { BotIcon, FileTextIcon, ListTodoIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "~/lib/utils";

type TrustChipProps = {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  tone: "source" | "inferred" | "todo";
};

const toneClassNames = {
  source: "border-primary/20 bg-primary text-primary-foreground",
  inferred: "border-inferred/30 bg-inferred text-inferred-foreground",
  todo: "border-todo border-dashed bg-transparent text-todo",
} satisfies Record<TrustChipProps["tone"], string>;

function TrustChip({
  icon: Icon,
  label,
  tone,
}: TrustChipProps): React.ReactElement {
  return (
    <span
      className={cn(
        "inline-flex h-8 items-center gap-2 rounded-md border px-3 text-sm font-medium",
        toneClassNames[tone],
      )}
    >
      <Icon aria-hidden className="size-4" />
      {label}
    </span>
  );
}

export function TrustChips(): React.ReactElement {
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap gap-2">
      <TrustChip icon={FileTextIcon} label={t("trust.source")} tone="source" />
      <TrustChip icon={BotIcon} label={t("trust.inferred")} tone="inferred" />
      <TrustChip icon={ListTodoIcon} label={t("trust.todo")} tone="todo" />
    </div>
  );
}
