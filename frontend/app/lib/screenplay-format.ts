import type { TFunction } from "i18next";
import type { Beat, Flag, ScreenplayScene, SourceRef } from "~/lib/api/types";

export function paragraphLabel(paragraphs: number[]): string {
  if (paragraphs.length === 0) return "";
  const sorted = [...paragraphs].sort((a, b) => a - b);
  const ranges: string[] = [];
  let rangeStart = sorted[0];
  let previous = sorted[0];

  for (const paragraph of sorted.slice(1)) {
    if (paragraph === previous + 1) {
      previous = paragraph;
      continue;
    }
    ranges.push(
      rangeStart === previous ? `${rangeStart}` : `${rangeStart}-${previous}`,
    );
    rangeStart = paragraph;
    previous = paragraph;
  }
  ranges.push(
    rangeStart === previous ? `${rangeStart}` : `${rangeStart}-${previous}`,
  );
  return ranges.join(", ");
}

export function sourceRefLabel(
  t: TFunction,
  sourceRef: SourceRef | null,
): string {
  if (!sourceRef) return t("script.noSourceRef");
  return t("script.sourceRef", {
    chapter: sourceRef.chapter,
    paragraphs: paragraphLabel(sourceRef.paragraphs),
  });
}

export function flagVariant(
  flag: Flag | null,
): "secondary" | "success" | "warning" {
  if (flag === "from_source") return "success";
  if (flag === "ai_inferred") return "warning";
  return "secondary";
}

export function beatToneClass(beat: Beat): string {
  if (beat.type === "todo") {
    return "border-warning/40 bg-warning/10";
  }
  if (beat.type === "note") {
    return "border-info/32 bg-info/8";
  }
  if (beat.flag === "ai_inferred") {
    return "border-warning/32 bg-warning/8";
  }
  return "border-border bg-card";
}

export function optionKindKey(kind: string): string {
  if (
    kind === "voice_over" ||
    kind === "action" ||
    kind === "dialogue" ||
    kind === "annotation"
  ) {
    return kind;
  }
  return "unknown";
}

export function sceneTitle(scene: ScreenplayScene): string {
  return `${scene.heading.location} · ${scene.synopsis ?? scene.id}`;
}

export function beatSummary(beat: Beat): string {
  return (
    beat.dialogue ??
    beat.text ??
    beat.options?.map((option) => option.text).join(" / ") ??
    ""
  );
}

export function characterName(
  characterNameById: Map<string, string>,
  characterId: string | null,
): string {
  if (!characterId) return "";
  return characterNameById.get(characterId) ?? characterId;
}

export function charactersLabel(
  characters: string[],
  characterNameById: Map<string, string>,
  separator: string,
): string {
  if (characters.length === 0) return "";
  return characters
    .map((characterId) => characterNameById.get(characterId) ?? characterId)
    .join(separator);
}
