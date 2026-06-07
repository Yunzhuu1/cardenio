import { FileTextIcon } from "lucide-react";
import type * as React from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import {
  Collapsible,
  CollapsiblePanel,
  CollapsibleTrigger,
} from "~/components/ui/collapsible";
import type { Beat } from "~/lib/api/types";
import {
  characterName,
  flagVariant,
  optionKindKey,
  sourceRefLabel,
} from "~/lib/screenplay-format";

export function BeatBadges({
  beat,
  index,
}: {
  beat: Beat;
  index: number;
}): React.ReactElement {
  const { t } = useTranslation();
  const flagLabel = beat.flag
    ? t(`script.flags.${beat.flag}`)
    : t("script.flags.unknown");

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <Badge variant="outline">{index + 1}</Badge>
      <Badge variant={beat.type === "todo" ? "warning" : "secondary"}>
        {t(`script.beatTypes.${beat.type}`)}
      </Badge>
      {beat.type === "todo" ? (
        <Badge variant="warning">{t("script.todoBadge")}</Badge>
      ) : null}
      <Badge variant={flagVariant(beat.flag)}>{flagLabel}</Badge>
      <Badge variant="secondary">{sourceRefLabel(t, beat.source_ref)}</Badge>
    </div>
  );
}

export function DialogueBeatBody({
  beat,
  characterNameById,
}: {
  beat: Beat;
  characterNameById: Map<string, string>;
}): React.ReactElement {
  const { t } = useTranslation();
  const speaker = characterName(characterNameById, beat.character);
  const suffix =
    beat.type === "voice_over" || beat.type === "off_screen"
      ? t(`script.dialogueSuffix.${beat.type}`)
      : null;

  return (
    <div className="grid gap-2">
      <div className="flex flex-wrap items-center gap-2 font-semibold">
        {speaker ? <span>{speaker}</span> : null}
        {suffix ? <Badge variant="outline">{suffix}</Badge> : null}
        {beat.parenthetical ? (
          <span className="font-normal text-muted-foreground">
            {beat.parenthetical}
          </span>
        ) : null}
      </div>
      <p className="whitespace-pre-wrap leading-relaxed">
        {beat.dialogue ?? beat.text ?? t("script.emptyField")}
      </p>
    </div>
  );
}

export function NoteBeatBody({ beat }: { beat: Beat }): React.ReactElement {
  const { t } = useTranslation();
  const options = beat.options ?? [];

  return (
    <div className="grid gap-3">
      <div>
        <div className="mb-1 font-medium">{t("script.noteTitle")}</div>
        <p className="whitespace-pre-wrap leading-relaxed">
          {beat.text ?? t("script.emptyField")}
        </p>
      </div>
      {options.length > 0 ? (
        <Collapsible>
          <CollapsibleTrigger render={<Button size="xs" variant="outline" />}>
            <FileTextIcon />
            {t("script.optionsToggle", { count: options.length })}
          </CollapsibleTrigger>
          <CollapsiblePanel className="mt-3">
            <div className="grid gap-2">
              {options.map((option, index) => (
                <div
                  className="rounded-md border bg-background p-3"
                  key={index}
                >
                  <Badge className="mb-2" variant="secondary">
                    {t(`script.optionKinds.${optionKindKey(option.kind)}`)}
                  </Badge>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">
                    {option.text}
                  </p>
                </div>
              ))}
            </div>
          </CollapsiblePanel>
        </Collapsible>
      ) : null}
    </div>
  );
}

export function BeatBody({
  beat,
  characterNameById,
}: {
  beat: Beat;
  characterNameById: Map<string, string>;
}): React.ReactElement {
  const { t } = useTranslation();

  return (
    <>
      {beat.type === "dialogue" ||
      beat.type === "voice_over" ||
      beat.type === "off_screen" ? (
        <DialogueBeatBody beat={beat} characterNameById={characterNameById} />
      ) : beat.type === "note" ? (
        <NoteBeatBody beat={beat} />
      ) : (
        <p className="whitespace-pre-wrap leading-relaxed">
          {beat.text ?? t("script.emptyField")}
        </p>
      )}

      {beat.subtext ? (
        <p className="mt-3 text-muted-foreground text-sm">
          <span className="font-medium">{t("script.subtext")}：</span>
          {beat.subtext}
        </p>
      ) : null}
    </>
  );
}
