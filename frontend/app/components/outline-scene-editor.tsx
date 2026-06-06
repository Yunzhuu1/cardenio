import {
  ArrowDownIcon,
  ArrowUpIcon,
  ChevronDownIcon,
  MoreHorizontalIcon,
  PencilIcon,
  PlusIcon,
  Trash2Icon,
  XIcon,
} from "lucide-react";
import type * as React from "react";
import { useTranslation } from "react-i18next";
import { StringListEditor } from "~/components/string-list-editor";
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
import { Checkbox } from "~/components/ui/checkbox";
import {
  Collapsible,
  CollapsiblePanel,
  CollapsibleTrigger,
} from "~/components/ui/collapsible";
import {
  DialogClose,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPanel,
  DialogPopup,
  DialogTitle,
} from "~/components/ui/dialog";
import { Field, FieldDescription, FieldLabel } from "~/components/ui/field";
import { Input } from "~/components/ui/input";
import { Menu, MenuItem, MenuPopup, MenuTrigger } from "~/components/ui/menu";
import {
  Select,
  SelectItem,
  SelectPopup,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { Separator } from "~/components/ui/separator";
import { Textarea } from "~/components/ui/textarea";
import type {
  Character,
  IntExt,
  OutlineScene,
  RelationChange,
  Source,
  SourceRef,
  TimeOfDay,
} from "~/lib/api/types";

const intExtOptions: IntExt[] = ["INT", "EXT"];
const timeOptions: TimeOfDay[] = ["DAY", "NIGHT", "DAWN", "DUSK"];

type SelectOption = {
  label: string;
  value: string;
};

export type SceneFormState = {
  mode: "create" | "edit";
  scene: OutlineScene;
};

function formatParagraphs(paragraphs: number[]): string {
  if (paragraphs.length === 0) return "";
  const sorted = [...paragraphs].sort((a, b) => a - b);
  const ranges: string[] = [];
  let start = sorted[0];
  let previous = sorted[0];

  for (const paragraph of sorted.slice(1)) {
    if (paragraph === previous + 1) {
      previous = paragraph;
      continue;
    }
    ranges.push(start === previous ? String(start) : `${start}-${previous}`);
    start = paragraph;
    previous = paragraph;
  }

  ranges.push(start === previous ? String(start) : `${start}-${previous}`);
  return ranges.join(", ");
}

function formatSourceRef(sourceRef: SourceRef, template: string): string {
  return template
    .replace("{{chapter}}", String(sourceRef.chapter))
    .replace("{{paragraphs}}", formatParagraphs(sourceRef.paragraphs));
}

function sceneTitle(scene: OutlineScene): string {
  const firstSentence =
    scene.synopsis
      .split(/[。！？.!?]/)
      .map((part) => part.trim())
      .find(Boolean) ?? scene.synopsis;
  return `${scene.heading.location} · ${firstSentence}`;
}

function makeSceneId(scenes: OutlineScene[]): string {
  const usedIds = new Set(scenes.map((scene) => scene.id));
  const maxNumber = scenes.reduce((max, scene) => {
    const match = /^sc_(\d+)$/.exec(scene.id);
    return match ? Math.max(max, Number(match[1])) : max;
  }, 0);
  let nextNumber = maxNumber + 1;
  let candidate = `sc_${String(nextNumber).padStart(3, "0")}`;

  while (usedIds.has(candidate)) {
    nextNumber += 1;
    candidate = `sc_${String(nextNumber).padStart(3, "0")}`;
  }

  return candidate;
}

function firstSourceRef(source: Source): SourceRef {
  const firstChapter = source.chapters[0];
  const firstParagraph = firstChapter?.paragraphs[0]?.index;

  return {
    chapter: firstChapter?.order ?? 1,
    paragraphs: firstParagraph ? [firstParagraph] : [],
  };
}

export function createBlankScene({
  characters,
  scenes,
  source,
}: {
  characters: Character[];
  scenes: OutlineScene[];
  source: Source;
}): OutlineScene {
  return {
    characters: characters[0] ? [characters[0].id] : [],
    conflict: null,
    ending_state: null,
    foreshadowing: [],
    goal: null,
    heading: {
      int_ext: "INT",
      location: "",
      time: "DAY",
    },
    id: makeSceneId(scenes),
    mood: null,
    relation_changes: [],
    source_ref: firstSourceRef(source),
    synopsis: "",
  };
}

export function OutlineSceneCard({
  characterNameById,
  canMoveDown,
  canMoveUp,
  index,
  onDelete,
  onEdit,
  onMoveDown,
  onMoveUp,
  scene,
  source,
  working,
}: {
  characterNameById: Map<string, string>;
  canMoveDown: boolean;
  canMoveUp: boolean;
  index: number;
  onDelete: (scene: OutlineScene) => void;
  onEdit: (scene: OutlineScene) => void;
  onMoveDown: () => void;
  onMoveUp: () => void;
  scene: OutlineScene;
  source: Source;
  working: boolean;
}): React.ReactElement {
  const { t } = useTranslation();
  const chapter = source.chapters.find(
    (item) => item.order === scene.source_ref.chapter,
  );
  const sourceLabel = formatSourceRef(scene.source_ref, t("outline.sourceRef"));
  const detailRows = [
    ["synopsis", scene.synopsis],
    ["goal", scene.goal],
    ["conflict", scene.conflict],
    ["mood", scene.mood],
    ["ending_state", scene.ending_state],
  ].filter(([, value]) => value);

  return (
    <Card className="rounded-lg shadow-none">
      <CardHeader className="gap-3">
        <CardTitle className="text-base">
          {t("outline.sceneNumber", { number: index + 1 })} ·{" "}
          {sceneTitle(scene)}
        </CardTitle>
        <CardDescription>
          {chapter
            ? t("outline.chapterHint", {
                paragraphs: chapter.paragraphs.length,
                title: chapter.title,
              })
            : t("outline.chapterMissing")}
        </CardDescription>
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">
            {t(`outline.int_ext.${scene.heading.int_ext}`)}
          </Badge>
          <Badge variant="outline">
            {t(`outline.time.${scene.heading.time}`)}
          </Badge>
          <Badge variant="info">{sourceLabel}</Badge>
        </div>
        <CardAction className="flex items-center gap-1">
          <Button
            aria-label={t("outline.edit.moveUp")}
            disabled={!canMoveUp || working}
            onClick={onMoveUp}
            size="icon-sm"
            type="button"
            variant="ghost"
          >
            <ArrowUpIcon aria-hidden />
          </Button>
          <Button
            aria-label={t("outline.edit.moveDown")}
            disabled={!canMoveDown || working}
            onClick={onMoveDown}
            size="icon-sm"
            type="button"
            variant="ghost"
          >
            <ArrowDownIcon aria-hidden />
          </Button>
          <Menu>
            <MenuTrigger
              aria-label={t("outline.edit.sceneMenu")}
              render={<Button size="icon-sm" type="button" variant="ghost" />}
            >
              <MoreHorizontalIcon aria-hidden />
            </MenuTrigger>
            <MenuPopup align="end">
              <MenuItem onClick={() => onEdit(scene)}>
                <PencilIcon aria-hidden />
                {t("outline.edit.editScene")}
              </MenuItem>
              <MenuItem onClick={() => onDelete(scene)} variant="destructive">
                <Trash2Icon aria-hidden />
                {t("outline.edit.deleteScene")}
              </MenuItem>
            </MenuPopup>
          </Menu>
        </CardAction>
      </CardHeader>
      <CardPanel className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          {detailRows.map(([key, value]) => (
            <div className="rounded-lg border bg-muted/32 p-3" key={key}>
              <div className="text-muted-foreground text-xs">
                {t(`outline.fields.${key}`)}
              </div>
              <div className="mt-1 text-sm">{value}</div>
            </div>
          ))}
        </div>

        <Separator />

        <div className="grid gap-4 md:grid-cols-2">
          <TokenGroup
            empty={t("outline.emptyField")}
            label={t("outline.fields.characters")}
            values={scene.characters.map(
              (id) => characterNameById.get(id) ?? id,
            )}
          />
          <TokenGroup
            empty={t("outline.emptyField")}
            label={t("outline.fields.foreshadowing")}
            values={scene.foreshadowing}
          />
        </div>

        <Collapsible>
          <CollapsibleTrigger
            className="inline-flex items-center gap-1 text-muted-foreground text-sm hover:text-foreground"
            type="button"
          >
            <ChevronDownIcon className="size-4" />
            {t("outline.relationChangesToggle", {
              count: scene.relation_changes.length,
            })}
          </CollapsibleTrigger>
          <CollapsiblePanel>
            <div className="space-y-2 pt-3">
              {scene.relation_changes.length > 0 ? (
                scene.relation_changes.map((change, changeIndex) => (
                  <div
                    className="rounded-lg border bg-muted/32 p-3 text-sm"
                    key={`${scene.id}-relation-${changeIndex}`}
                  >
                    <span className="font-medium">
                      {change.characters
                        .map((id) => characterNameById.get(id) ?? id)
                        .join(t("outline.characterSeparator"))}
                    </span>
                    {t("outline.relationChangeSeparator")}
                    {change.change}
                  </div>
                ))
              ) : (
                <div className="text-muted-foreground text-sm">
                  {t("outline.noRelationChanges")}
                </div>
              )}
            </div>
          </CollapsiblePanel>
        </Collapsible>
      </CardPanel>
    </Card>
  );
}

export function SceneDialog({
  characters,
  form,
  onFormChange,
  onSave,
  source,
  working,
}: {
  characters: Character[];
  form: SceneFormState;
  onFormChange: React.Dispatch<React.SetStateAction<SceneFormState | null>>;
  onSave: () => Promise<void>;
  source: Source;
  working: boolean;
}): React.ReactElement {
  const { t } = useTranslation();
  const isEditing = form.mode === "edit";
  const scene = form.scene;
  const canSave = Boolean(
    scene.heading.location.trim() &&
    scene.synopsis.trim() &&
    scene.source_ref.paragraphs.length > 0,
  );

  function updateScene(patch: Partial<OutlineScene>): void {
    onFormChange((current) =>
      current ? { ...current, scene: { ...current.scene, ...patch } } : current,
    );
  }

  function updateHeading(patch: Partial<OutlineScene["heading"]>): void {
    updateScene({ heading: { ...scene.heading, ...patch } });
  }

  function updateSourceRef(sourceRef: SourceRef): void {
    updateScene({ source_ref: sourceRef });
  }

  return (
    <DialogPopup className="max-w-4xl">
      <DialogHeader>
        <DialogTitle>
          {isEditing ? t("outline.edit.editScene") : t("outline.edit.addScene")}
        </DialogTitle>
        <DialogDescription>
          {t("outline.edit.dialogDescription")}
        </DialogDescription>
      </DialogHeader>
      <DialogPanel className="max-h-[70dvh] space-y-5 overflow-y-auto">
        <div className="grid gap-4 md:grid-cols-[1fr_10rem_10rem]">
          <Field className="w-full">
            <FieldLabel>{t("outline.edit.fields.location")}</FieldLabel>
            <Input
              onChange={(event) =>
                updateHeading({ location: event.target.value })
              }
              placeholder={t("outline.edit.placeholders.location")}
              type="text"
              value={scene.heading.location}
            />
          </Field>
          <EnumSelect
            items={intExtOptions.map((value) => ({
              label: t(`outline.int_ext.${value}`),
              value,
            }))}
            label={t("outline.edit.fields.intExt")}
            onChange={(value) => updateHeading({ int_ext: value as IntExt })}
            value={scene.heading.int_ext}
          />
          <EnumSelect
            items={timeOptions.map((value) => ({
              label: t(`outline.time.${value}`),
              value,
            }))}
            label={t("outline.edit.fields.time")}
            onChange={(value) => updateHeading({ time: value as TimeOfDay })}
            value={scene.heading.time}
          />
        </div>

        <SourceRefEditor
          onChange={updateSourceRef}
          source={source}
          value={scene.source_ref}
        />

        <Field className="w-full">
          <FieldLabel>{t("outline.fields.synopsis")}</FieldLabel>
          <Textarea
            onChange={(event) => updateScene({ synopsis: event.target.value })}
            placeholder={t("outline.edit.placeholders.synopsis")}
            value={scene.synopsis}
          />
        </Field>

        <div className="grid gap-4 md:grid-cols-2">
          <Field className="w-full">
            <FieldLabel>{t("outline.fields.goal")}</FieldLabel>
            <Input
              onChange={(event) => updateScene({ goal: event.target.value })}
              placeholder={t("outline.edit.placeholders.goal")}
              type="text"
              value={scene.goal ?? ""}
            />
          </Field>
          <Field className="w-full">
            <FieldLabel>{t("outline.fields.conflict")}</FieldLabel>
            <Input
              onChange={(event) =>
                updateScene({ conflict: event.target.value })
              }
              placeholder={t("outline.edit.placeholders.conflict")}
              type="text"
              value={scene.conflict ?? ""}
            />
          </Field>
          <Field className="w-full">
            <FieldLabel>{t("outline.fields.mood")}</FieldLabel>
            <Input
              onChange={(event) => updateScene({ mood: event.target.value })}
              placeholder={t("outline.edit.placeholders.mood")}
              type="text"
              value={scene.mood ?? ""}
            />
          </Field>
          <Field className="w-full">
            <FieldLabel>{t("outline.fields.ending_state")}</FieldLabel>
            <Input
              onChange={(event) =>
                updateScene({ ending_state: event.target.value })
              }
              placeholder={t("outline.edit.placeholders.endingState")}
              type="text"
              value={scene.ending_state ?? ""}
            />
          </Field>
        </div>

        <CharacterCheckboxGroup
          characters={characters}
          label={t("outline.fields.characters")}
          onChange={(selected) => updateScene({ characters: selected })}
          selectedIds={scene.characters}
        />

        <StringListEditor
          label={t("outline.fields.foreshadowing")}
          onChange={(foreshadowing) => updateScene({ foreshadowing })}
          placeholder={t("outline.edit.placeholders.foreshadowing")}
          values={scene.foreshadowing}
        />

        <RelationChangeEditor
          characters={characters}
          onChange={(relation_changes) => updateScene({ relation_changes })}
          relationChanges={scene.relation_changes}
        />
      </DialogPanel>
      <DialogFooter>
        <DialogClose render={<Button type="button" variant="ghost" />}>
          {t("outline.cancel")}
        </DialogClose>
        <Button
          disabled={!canSave}
          loading={working}
          onClick={onSave}
          type="button"
        >
          {isEditing
            ? t("outline.edit.saveScene")
            : t("outline.edit.createScene")}
        </Button>
      </DialogFooter>
    </DialogPopup>
  );
}

function EnumSelect({
  items,
  label,
  onChange,
  value,
}: {
  items: SelectOption[];
  label: string;
  onChange: (value: string) => void;
  value: string;
}): React.ReactElement {
  const selectedItem = items.find((item) => item.value === value) ?? items[0];

  return (
    <Field className="w-full">
      <FieldLabel>{label}</FieldLabel>
      <Select
        itemToStringValue={(item) => item.value}
        items={items}
        onValueChange={(nextValue) => {
          if (nextValue) onChange(nextValue.value);
        }}
        value={selectedItem}
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectPopup>
          {items.map((item) => (
            <SelectItem key={item.value} value={item}>
              {item.label}
            </SelectItem>
          ))}
        </SelectPopup>
      </Select>
    </Field>
  );
}

function SourceRefEditor({
  onChange,
  source,
  value,
}: {
  onChange: (value: SourceRef) => void;
  source: Source;
  value: SourceRef;
}): React.ReactElement {
  const { t } = useTranslation();
  const chapterItems = source.chapters.map((chapter) => ({
    label: chapter.title,
    value: String(chapter.order),
  }));
  const selectedChapter =
    source.chapters.find((chapter) => chapter.order === value.chapter) ??
    source.chapters[0];
  const selectedChapterItem =
    chapterItems.find((item) => Number(item.value) === value.chapter) ??
    chapterItems[0];

  return (
    <div className="grid gap-4 md:grid-cols-[16rem_1fr]">
      <Field className="w-full">
        <FieldLabel>{t("outline.edit.fields.chapter")}</FieldLabel>
        <Select
          itemToStringValue={(item) => item.value}
          items={chapterItems}
          onValueChange={(nextValue) => {
            if (!nextValue) return;
            const chapter = source.chapters.find(
              (item) => item.order === Number(nextValue.value),
            );
            onChange({
              chapter: Number(nextValue.value),
              paragraphs: chapter?.paragraphs[0]
                ? [chapter.paragraphs[0].index]
                : [],
            });
          }}
          value={selectedChapterItem}
        >
          <SelectTrigger>
            <SelectValue placeholder={t("outline.edit.placeholders.chapter")} />
          </SelectTrigger>
          <SelectPopup>
            {chapterItems.map((item) => (
              <SelectItem key={item.value} value={item}>
                {item.label}
              </SelectItem>
            ))}
          </SelectPopup>
        </Select>
      </Field>

      <Field className="w-full">
        <FieldLabel>{t("outline.edit.fields.paragraphs")}</FieldLabel>
        <FieldDescription>
          {t("outline.edit.paragraphDescription")}
        </FieldDescription>
        <div className="grid max-h-40 gap-2 overflow-y-auto rounded-lg border p-3 sm:grid-cols-2 lg:grid-cols-3">
          {selectedChapter?.paragraphs.map((paragraph) => {
            const checked = value.paragraphs.includes(paragraph.index);
            return (
              <label
                className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
                key={paragraph.index}
              >
                <Checkbox
                  checked={checked}
                  onCheckedChange={(nextChecked) => {
                    const paragraphs = nextChecked
                      ? [...value.paragraphs, paragraph.index]
                      : value.paragraphs.filter(
                          (index) => index !== paragraph.index,
                        );
                    onChange({
                      chapter: value.chapter,
                      paragraphs: [...new Set(paragraphs)].sort(
                        (a, b) => a - b,
                      ),
                    });
                  }}
                />
                <span>
                  {t("outline.edit.paragraphIndex", {
                    number: paragraph.index,
                  })}
                </span>
              </label>
            );
          })}
        </div>
      </Field>
    </div>
  );
}

function CharacterCheckboxGroup({
  characters,
  label,
  onChange,
  selectedIds,
}: {
  characters: Character[];
  label: string;
  onChange: (selectedIds: string[]) => void;
  selectedIds: string[];
}): React.ReactElement {
  const { t } = useTranslation();
  const items = characters.map((character) => ({
    label: character.name,
    value: character.id,
  }));
  const selectedItems = items.filter((item) =>
    selectedIds.includes(item.value),
  );

  return (
    <Field className="w-full">
      <FieldLabel>{label}</FieldLabel>
      <FieldDescription>
        {t("outline.edit.characterDescription")}
      </FieldDescription>
      <Select
        itemToStringValue={(item) => item.value}
        items={items}
        multiple
        onValueChange={(nextItems) => {
          onChange(nextItems.map((item) => item.value));
        }}
        value={selectedItems}
      >
        <SelectTrigger>
          <SelectValue placeholder={t("outline.edit.placeholders.characters")}>
            {selectedItems.length > 0
              ? selectedItems.map((item) => item.label).join(", ")
              : null}
          </SelectValue>
        </SelectTrigger>
        <SelectPopup>
          {items.map((item) => (
            <SelectItem key={item.value} value={item}>
              {item.label}
            </SelectItem>
          ))}
        </SelectPopup>
      </Select>
    </Field>
  );
}

function RelationChangeEditor({
  characters,
  onChange,
  relationChanges,
}: {
  characters: Character[];
  onChange: (relationChanges: RelationChange[]) => void;
  relationChanges: RelationChange[];
}): React.ReactElement {
  const { t } = useTranslation();

  function updateRelation(index: number, patch: Partial<RelationChange>): void {
    onChange(
      relationChanges.map((relation, relationIndex) =>
        relationIndex === index ? { ...relation, ...patch } : relation,
      ),
    );
  }

  function addRelation(): void {
    onChange([
      ...relationChanges,
      { characters: characters[0] ? [characters[0].id] : [], change: "" },
    ]);
  }

  function removeRelation(index: number): void {
    onChange(
      relationChanges.filter((_, relationIndex) => relationIndex !== index),
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="font-medium text-sm">
          {t("outline.fields.relation_changes")}
        </div>
        <Button onClick={addRelation} size="sm" type="button" variant="outline">
          <PlusIcon aria-hidden />
          {t("outline.edit.addRelationChange")}
        </Button>
      </div>
      {relationChanges.length > 0 ? (
        <div className="space-y-3">
          {relationChanges.map((relation, index) => (
            <div
              className="grid gap-3 rounded-lg border p-3 lg:grid-cols-[1fr_1fr_auto]"
              key={`relation-${index}`}
            >
              <CharacterCheckboxGroup
                characters={characters}
                label={t("outline.edit.fields.relationCharacters")}
                onChange={(selectedIds) =>
                  updateRelation(index, { characters: selectedIds })
                }
                selectedIds={relation.characters}
              />
              <Field className="w-full">
                <FieldLabel>
                  {t("outline.edit.fields.relationChange")}
                </FieldLabel>
                <Input
                  onChange={(event) =>
                    updateRelation(index, { change: event.target.value })
                  }
                  placeholder={t("outline.edit.placeholders.relationChange")}
                  type="text"
                  value={relation.change}
                />
              </Field>
              <Button
                aria-label={t("outline.edit.removeRelationChange")}
                className="self-end"
                onClick={() => removeRelation(index)}
                size="icon"
                type="button"
                variant="ghost"
              >
                <XIcon aria-hidden />
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-muted-foreground text-sm">
          {t("outline.noRelationChanges")}
        </p>
      )}
    </div>
  );
}

function TokenGroup({
  empty,
  label,
  values,
}: {
  empty: string;
  label: string;
  values: string[];
}): React.ReactElement {
  return (
    <div>
      <div className="mb-2 text-muted-foreground text-xs">{label}</div>
      <div className="flex flex-wrap gap-2">
        {values.length > 0 ? (
          values.map((value) => (
            <Badge key={value} variant="secondary">
              {value}
            </Badge>
          ))
        ) : (
          <span className="text-muted-foreground text-sm">{empty}</span>
        )}
      </div>
    </div>
  );
}
