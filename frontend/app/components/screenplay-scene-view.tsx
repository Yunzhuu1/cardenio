import type * as React from "react";
import { useTranslation } from "react-i18next";
import { Badge } from "~/components/ui/badge";
import { CardDescription, CardHeader, CardTitle } from "~/components/ui/card";
import type { ScreenplayScene } from "~/lib/api/types";
import { charactersLabel, sourceRefLabel } from "~/lib/screenplay-format";

export function SceneHeader({
  characterNameById,
  scene,
  sceneNumber,
}: {
  characterNameById: Map<string, string>;
  scene: ScreenplayScene;
  sceneNumber: number;
}): React.ReactElement {
  const { t } = useTranslation();
  const characterSeparator = t("script.characterSeparator");
  const cast = charactersLabel(
    scene.characters,
    characterNameById,
    characterSeparator,
  );

  return (
    <CardHeader className="border-b">
      <CardTitle className="flex flex-wrap items-center gap-2 text-base">
        <span>{t("script.sceneNumber", { number: sceneNumber })}</span>
        <Badge variant="outline">
          {t(`script.int_ext.${scene.heading.int_ext}`)}
        </Badge>
        <Badge variant="outline">{scene.heading.location}</Badge>
        <Badge variant="outline">
          {t(`script.time.${scene.heading.time}`)}
        </Badge>
      </CardTitle>
      <CardDescription className="flex flex-wrap gap-2">
        <Badge variant="secondary">{sourceRefLabel(t, scene.source_ref)}</Badge>
        {scene.mood ? <Badge variant="secondary">{scene.mood}</Badge> : null}
        {cast ? <Badge variant="secondary">{cast}</Badge> : null}
      </CardDescription>
    </CardHeader>
  );
}

export function SceneSummary({
  scene,
}: {
  scene: ScreenplayScene;
}): React.ReactElement {
  const { t } = useTranslation();
  const items = [
    ["synopsis", scene.synopsis],
    ["goal", scene.goal],
    ["conflict", scene.conflict],
    ["ending_state", scene.ending_state],
  ] as const;

  return (
    <div className="grid gap-2 rounded-lg bg-muted/32 p-3 text-sm md:grid-cols-2">
      {items.map(([key, value]) =>
        value ? (
          <div className="grid gap-1" key={key}>
            <div className="font-medium text-muted-foreground">
              {t(`script.fields.${key}`)}
            </div>
            <div>{value}</div>
          </div>
        ) : null,
      )}
    </div>
  );
}
