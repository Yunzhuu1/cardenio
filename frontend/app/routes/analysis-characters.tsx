import {
  CheckCircleIcon,
  MoreHorizontalIcon,
  PlusIcon,
  RefreshCwIcon,
  Trash2Icon,
  UserPenIcon,
  UsersIcon,
  XIcon,
} from "lucide-react";
import type * as React from "react";
import { useMemo, useState } from "react";
import { Link, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/analysis-characters";
import { StringListEditor } from "~/components/string-list-editor";
import {
  Alert,
  AlertAction,
  AlertDescription,
  AlertTitle,
} from "~/components/ui/alert";
import {
  AlertDialog,
  AlertDialogClose,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogPopup,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "~/components/ui/alert-dialog";
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
import {
  Dialog,
  DialogClose,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPanel,
  DialogPopup,
  DialogTitle,
  DialogTrigger,
} from "~/components/ui/dialog";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { Field, FieldLabel } from "~/components/ui/field";
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
import { toastManager } from "~/components/ui/toast";
import { api } from "~/lib/api/client";
import {
  ApiError,
  type Character,
  type CharacterRelation,
  type CharacterRole,
  type ProjectId,
} from "~/lib/api/types";
import { analysisStepPath } from "~/lib/stages";

const roleOrder: CharacterRole[] = ["protagonist", "supporting", "mentioned"];

type CharacterFormState = {
  id: string | null;
  name: string;
  role: CharacterRole;
  voice: string;
  desire: string;
  fear: string;
  arc: string;
  relations: CharacterRelation[];
  hard_rules: string[];
};

async function getOrNull<T>(request: Promise<T>): Promise<T | null> {
  try {
    return await request;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

function emptyCharacterForm(): CharacterFormState {
  return {
    arc: "",
    desire: "",
    fear: "",
    hard_rules: [],
    id: null,
    name: "",
    relations: [],
    role: "supporting",
    voice: "",
  };
}

function characterToForm(character: Character): CharacterFormState {
  return {
    ...character,
    arc: character.arc ?? "",
  };
}

function formToCharacter(form: CharacterFormState, id: string): Character {
  return {
    arc: form.arc.trim() || null,
    desire: form.desire.trim(),
    fear: form.fear.trim(),
    hard_rules: form.hard_rules,
    id,
    name: form.name.trim(),
    relations: form.relations
      .filter((relation) => relation.to && relation.type.trim())
      .map((relation) => ({
        change: relation.change?.trim() || null,
        to: relation.to,
        type: relation.type.trim(),
      })),
    role: form.role,
    voice: form.voice.trim(),
  };
}

function makeCharacterId(name: string, existingIds: string[]): string {
  const base =
    name
      .normalize("NFKD")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || "character";

  if (!existingIds.includes(base)) return base;

  let suffix = 2;
  while (existingIds.includes(`${base}-${suffix}`)) suffix += 1;
  return `${base}-${suffix}`;
}

function roleBadgeVariant(
  role: CharacterRole,
): "default" | "secondary" | "info" {
  if (role === "protagonist") return "default";
  if (role === "supporting") return "info";
  return "secondary";
}

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const projectId = params.projectId as ProjectId;
  const [characters, understanding] = await Promise.all([
    getOrNull(api.characters.get(projectId)),
    getOrNull(api.understanding.get(projectId)),
  ]);
  return { characters, understanding, projectId };
}

export default function AnalysisCharacters({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const revalidator = useRevalidator();
  const { characters, understanding, projectId } = loaderData;
  const [working, setWorking] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<CharacterFormState>(emptyCharacterForm);
  const [deleteTarget, setDeleteTarget] = useState<Character | null>(null);
  const locked = understanding?.state !== "confirmed";
  const status = characters?.state ?? "empty";
  const characterList = useMemo(
    () => characters?.data.characters ?? [],
    [characters],
  );
  const editingCharacterId = form.id;
  const groupedCharacters = useMemo(
    () =>
      roleOrder.map((role) => ({
        characters: characterList.filter(
          (character) => character.role === role,
        ),
        role,
      })),
    [characterList],
  );

  async function refresh(): Promise<void> {
    await revalidator.revalidate();
  }

  function openCreateDialog(): void {
    setForm(emptyCharacterForm());
    setDialogOpen(true);
  }

  function openEditDialog(character: Character): void {
    setForm(characterToForm(character));
    setDialogOpen(true);
  }

  async function generateCharacters(): Promise<void> {
    try {
      setWorking(true);
      await api.characters.generate(projectId);
      toastManager.add({
        title: t("analysis.characters.generateSuccess"),
        type: "success",
      });
      await refresh();
    } catch (error) {
      toastManager.add({
        description:
          error instanceof ApiError && error.code === "state_gate_blocked"
            ? t("analysis.characters.gateBlocked")
            : getErrorMessage(error),
        title: t("analysis.characters.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function saveCharacter(): Promise<void> {
    const name = form.name.trim();
    if (
      !name ||
      !form.voice.trim() ||
      !form.desire.trim() ||
      !form.fear.trim()
    ) {
      return;
    }

    const existingIds = characterList.map((character) => character.id);
    const id = editingCharacterId ?? makeCharacterId(name, existingIds);
    const character = formToCharacter(form, id);

    try {
      setWorking(true);
      if (editingCharacterId) {
        await api.characters.update(projectId, editingCharacterId, character);
        toastManager.add({
          title: t("analysis.characters.editSuccess"),
          type: "success",
        });
      } else {
        await api.characters.add(projectId, character);
        toastManager.add({
          title: t("analysis.characters.addSuccess"),
          type: "success",
        });
      }
      setDialogOpen(false);
      await refresh();
    } catch (error) {
      toastManager.add({
        description:
          error instanceof ApiError && error.status === 409
            ? t("analysis.characters.idConflict")
            : getErrorMessage(error),
        title: t("analysis.characters.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function deleteCharacter(): Promise<void> {
    if (!deleteTarget) return;

    try {
      setWorking(true);
      await api.characters.remove(projectId, deleteTarget.id);
      toastManager.add({
        title: t("analysis.characters.deleteSuccess"),
        type: "success",
      });
      setDeleteTarget(null);
      await refresh();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("analysis.characters.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  async function confirmCharacters(): Promise<void> {
    try {
      setWorking(true);
      await api.characters.confirm(projectId);
      toastManager.add({
        title: t("analysis.characters.confirmSuccess"),
        type: "success",
      });
      await refresh();
    } catch (error) {
      toastManager.add({
        description: getErrorMessage(error),
        title: t("analysis.characters.actionError"),
        type: "error",
      });
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="space-y-4">
      {locked ? (
        <Alert variant="warning">
          <AlertTitle>{t("analysis.characters.lockedTitle")}</AlertTitle>
          <AlertDescription>
            {t("analysis.characters.lockedDescription")}
          </AlertDescription>
          <AlertAction>
            <Button
              render={
                <Link to={analysisStepPath(projectId, "understanding")} />
              }
              size="sm"
              variant="outline"
            >
              {t("analysis.backToUnderstanding")}
            </Button>
          </AlertAction>
        </Alert>
      ) : characters ? (
        <div className="space-y-4">
          {status !== "confirmed" ? (
            <Alert variant="info">
              <AlertTitle>
                {t("analysis.characters.needsReconfirmTitle")}
              </AlertTitle>
              <AlertDescription>
                {t("analysis.characters.needsReconfirmDescription")}
              </AlertDescription>
            </Alert>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>{t("analysis.characters.cardTitle")}</CardTitle>
              <CardDescription>
                {t("analysis.characters.cardDescription")}
              </CardDescription>
              <CardAction className="flex flex-wrap justify-end gap-2">
                <AlertDialog>
                  <AlertDialogTrigger render={<Button variant="outline" />}>
                    <RefreshCwIcon aria-hidden />
                    {t("analysis.characters.regenerate")}
                  </AlertDialogTrigger>
                  <AlertDialogPopup>
                    <AlertDialogHeader>
                      <AlertDialogTitle>
                        {t("analysis.characters.regenerateTitle")}
                      </AlertDialogTitle>
                      <AlertDialogDescription>
                        {t("analysis.characters.regenerateDescription")}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogClose
                        render={<Button type="button" variant="ghost" />}
                      >
                        {t("analysis.characters.cancel")}
                      </AlertDialogClose>
                      <AlertDialogClose
                        render={
                          <Button
                            loading={working}
                            onClick={generateCharacters}
                            type="button"
                          />
                        }
                      >
                        {t("analysis.characters.regenerateConfirm")}
                      </AlertDialogClose>
                    </AlertDialogFooter>
                  </AlertDialogPopup>
                </AlertDialog>
                <Dialog onOpenChange={setDialogOpen} open={dialogOpen}>
                  <DialogTrigger render={<Button onClick={openCreateDialog} />}>
                    <PlusIcon aria-hidden />
                    {t("analysis.characters.addCharacter")}
                  </DialogTrigger>
                  <CharacterDialog
                    characters={characterList}
                    form={form}
                    onFormChange={setForm}
                    onSave={saveCharacter}
                    projectWorking={working}
                  />
                </Dialog>
                {status !== "confirmed" ? (
                  <Button loading={working} onClick={confirmCharacters}>
                    <CheckCircleIcon aria-hidden />
                    {t("analysis.characters.confirm")}
                  </Button>
                ) : null}
                {status === "confirmed" ? (
                  <Button
                    render={<Link to={analysisStepPath(projectId, "intent")} />}
                    variant="secondary"
                  >
                    {t("analysis.characters.confirmCta")}
                  </Button>
                ) : null}
              </CardAction>
            </CardHeader>
          </Card>

          {groupedCharacters.map((group) => (
            <section className="space-y-3" key={group.role}>
              <h3 className="font-medium text-base">
                {t(`analysis.characters.roles.${group.role}`)}
              </h3>
              {group.characters.length > 0 ? (
                <div className="grid gap-3 xl:grid-cols-2">
                  {group.characters.map((character) => (
                    <CharacterCard
                      character={character}
                      characters={characterList}
                      key={character.id}
                      onDelete={setDeleteTarget}
                      onEdit={openEditDialog}
                    />
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">
                  {t("analysis.characters.noCharacters")}
                </p>
              )}
            </section>
          ))}
        </div>
      ) : (
        <Empty className="rounded-lg border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <UsersIcon aria-hidden className="size-4" />
            </EmptyMedia>
            <EmptyTitle>{t("analysis.characters.emptyTitle")}</EmptyTitle>
            <EmptyDescription>
              {t("analysis.characters.emptyDescription")}
            </EmptyDescription>
          </EmptyHeader>
          <Button loading={working} onClick={generateCharacters}>
            <UsersIcon aria-hidden />
            {t("analysis.characters.generate")}
          </Button>
        </Empty>
      )}

      <AlertDialog
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        open={Boolean(deleteTarget)}
      >
        <AlertDialogPopup>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("analysis.characters.deleteTitle")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t("analysis.characters.deleteDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogClose render={<Button type="button" variant="ghost" />}>
              {t("analysis.characters.cancel")}
            </AlertDialogClose>
            <AlertDialogClose
              render={
                <Button
                  loading={working}
                  onClick={deleteCharacter}
                  type="button"
                  variant="destructive"
                />
              }
            >
              {t("analysis.characters.deleteConfirm")}
            </AlertDialogClose>
          </AlertDialogFooter>
        </AlertDialogPopup>
      </AlertDialog>
    </section>
  );
}

function CharacterCard({
  character,
  characters,
  onDelete,
  onEdit,
}: {
  character: Character;
  characters: Character[];
  onDelete: (character: Character) => void;
  onEdit: (character: Character) => void;
}): React.ReactElement {
  const { t } = useTranslation();
  const relationName = (id: string) =>
    characters.find((item) => item.id === id)?.name ?? id;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex min-w-0 items-center gap-2">
          <span className="truncate">{character.name}</span>
          <Badge size="sm" variant={roleBadgeVariant(character.role)}>
            {t(`analysis.characters.roles.${character.role}`)}
          </Badge>
        </CardTitle>
        <CardDescription>{character.id}</CardDescription>
        <CardAction>
          <Menu>
            <MenuTrigger
              aria-label={t("analysis.characters.menuLabel")}
              render={<Button size="icon-sm" variant="ghost" />}
            >
              <MoreHorizontalIcon aria-hidden />
            </MenuTrigger>
            <MenuPopup align="end">
              <MenuItem onClick={() => onEdit(character)}>
                <UserPenIcon aria-hidden />
                {t("analysis.characters.editCharacter")}
              </MenuItem>
              <MenuItem
                onClick={() => onDelete(character)}
                variant="destructive"
              >
                <Trash2Icon aria-hidden />
                {t("analysis.characters.deleteCharacter")}
              </MenuItem>
            </MenuPopup>
          </Menu>
        </CardAction>
      </CardHeader>
      <CardPanel className="space-y-3">
        <dl className="grid gap-2 text-sm">
          <CharacterDetail
            label={t("analysis.characters.fields.voice")}
            value={character.voice}
          />
          <CharacterDetail
            label={t("analysis.characters.fields.desire")}
            value={character.desire}
          />
          <CharacterDetail
            label={t("analysis.characters.fields.fear")}
            value={character.fear}
          />
          {character.arc ? (
            <CharacterDetail
              label={t("analysis.characters.fields.arc")}
              value={character.arc}
            />
          ) : null}
        </dl>

        <Separator />

        <div className="space-y-2">
          <div className="font-medium text-sm">
            {t("analysis.characters.fields.hard_rules")}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {character.hard_rules.length > 0 ? (
              character.hard_rules.map((rule) => (
                <Badge key={rule} variant="secondary">
                  {rule}
                </Badge>
              ))
            ) : (
              <span className="text-muted-foreground text-sm">-</span>
            )}
          </div>
        </div>

        <div className="space-y-2">
          <div className="font-medium text-sm">
            {t("analysis.characters.fields.relations")}
          </div>
          {character.relations.length > 0 ? (
            <ul className="space-y-1 text-sm">
              {character.relations.map((relation, index) => (
                <li key={`${relation.to}-${relation.type}-${index}`}>
                  {"-> "}
                  {relationName(relation.to)}
                  {relation.type ? ` (${relation.type})` : ""}
                  {relation.change ? `: ${relation.change}` : ""}
                </li>
              ))}
            </ul>
          ) : (
            <span className="text-muted-foreground text-sm">
              {t("analysis.characters.relations.empty")}
            </span>
          )}
        </div>
      </CardPanel>
    </Card>
  );
}

function CharacterDetail({
  label,
  value,
}: {
  label: string;
  value: string;
}): React.ReactElement {
  return (
    <div className="grid gap-1 sm:grid-cols-[7rem_1fr]">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function CharacterDialog({
  characters,
  form,
  onFormChange,
  onSave,
  projectWorking,
}: {
  characters: Character[];
  form: CharacterFormState;
  onFormChange: React.Dispatch<React.SetStateAction<CharacterFormState>>;
  onSave: () => Promise<void>;
  projectWorking: boolean;
}): React.ReactElement {
  const { t } = useTranslation();
  const isEditing = Boolean(form.id);
  const canSave = Boolean(
    form.name.trim() &&
    form.voice.trim() &&
    form.desire.trim() &&
    form.fear.trim(),
  );

  function updateField(
    key: keyof Pick<
      CharacterFormState,
      "name" | "voice" | "desire" | "fear" | "arc"
    >,
    value: string,
  ): void {
    onFormChange((current) => ({ ...current, [key]: value }));
  }

  return (
    <DialogPopup className="max-w-3xl">
      <DialogHeader>
        <DialogTitle>
          {isEditing
            ? t("analysis.characters.editCharacter")
            : t("analysis.characters.addCharacter")}
        </DialogTitle>
        <DialogDescription>
          {t("analysis.characters.cardDescription")}
        </DialogDescription>
      </DialogHeader>
      <DialogPanel className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <Field className="w-full">
            <FieldLabel>{t("analysis.characters.fields.name")}</FieldLabel>
            <Input
              onChange={(event) => updateField("name", event.target.value)}
              placeholder={t("analysis.characters.placeholders.name")}
              value={form.name}
            />
          </Field>
          <RoleSelect
            onChange={(role) =>
              onFormChange((current) => ({ ...current, role }))
            }
            value={form.role}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Field className="w-full">
            <FieldLabel>{t("analysis.characters.fields.voice")}</FieldLabel>
            <Input
              onChange={(event) => updateField("voice", event.target.value)}
              placeholder={t("analysis.characters.placeholders.voice")}
              value={form.voice}
            />
          </Field>
          <Field className="w-full">
            <FieldLabel>{t("analysis.characters.fields.desire")}</FieldLabel>
            <Input
              onChange={(event) => updateField("desire", event.target.value)}
              placeholder={t("analysis.characters.placeholders.desire")}
              value={form.desire}
            />
          </Field>
          <Field className="w-full">
            <FieldLabel>{t("analysis.characters.fields.fear")}</FieldLabel>
            <Input
              onChange={(event) => updateField("fear", event.target.value)}
              placeholder={t("analysis.characters.placeholders.fear")}
              value={form.fear}
            />
          </Field>
          <Field className="w-full">
            <FieldLabel>{t("analysis.characters.fields.arc")}</FieldLabel>
            <Input
              onChange={(event) => updateField("arc", event.target.value)}
              placeholder={t("analysis.characters.placeholders.arc")}
              value={form.arc}
            />
          </Field>
        </div>

        <StringListEditor
          label={t("analysis.characters.fields.hard_rules")}
          onChange={(hardRules) =>
            onFormChange((current) => ({
              ...current,
              hard_rules: hardRules,
            }))
          }
          placeholder={t("analysis.characters.placeholders.hard_rules")}
          values={form.hard_rules}
        />

        <RelationEditor
          characterId={form.id}
          characters={characters}
          onChange={(relations) =>
            onFormChange((current) => ({ ...current, relations }))
          }
          relations={form.relations}
        />
      </DialogPanel>
      <DialogFooter>
        <DialogClose render={<Button type="button" variant="ghost" />}>
          {t("analysis.characters.cancel")}
        </DialogClose>
        <Button disabled={!canSave} loading={projectWorking} onClick={onSave}>
          {isEditing
            ? t("analysis.characters.saveCharacter")
            : t("analysis.characters.createCharacter")}
        </Button>
      </DialogFooter>
    </DialogPopup>
  );
}

function RoleSelect({
  onChange,
  value,
}: {
  onChange: (role: CharacterRole) => void;
  value: CharacterRole;
}): React.ReactElement {
  const { t } = useTranslation();
  const items = roleOrder.map((role) => ({
    label: t(`analysis.characters.roles.${role}`),
    value: role,
  }));
  const selectedItem = items.find((item) => item.value === value) ?? items[0];

  return (
    <Field className="w-full">
      <FieldLabel>{t("analysis.characters.fields.role")}</FieldLabel>
      <Select
        itemToStringValue={(item) => item.value}
        items={items}
        onValueChange={(nextValue) => {
          if (nextValue) onChange(nextValue.value);
        }}
        value={selectedItem}
      >
        <SelectTrigger>
          <SelectValue
            placeholder={t("analysis.characters.placeholders.role")}
          />
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

function RelationEditor({
  characterId,
  characters,
  onChange,
  relations,
}: {
  characterId: string | null;
  characters: Character[];
  onChange: (relations: CharacterRelation[]) => void;
  relations: CharacterRelation[];
}): React.ReactElement {
  const { t } = useTranslation();
  const candidates = characters.filter(
    (character) => character.id !== characterId,
  );

  function updateRelation(
    index: number,
    patch: Partial<CharacterRelation>,
  ): void {
    onChange(
      relations.map((relation, relationIndex) =>
        relationIndex === index ? { ...relation, ...patch } : relation,
      ),
    );
  }

  function removeRelation(index: number): void {
    onChange(relations.filter((_, relationIndex) => relationIndex !== index));
  }

  function addRelation(): void {
    const firstCandidate = candidates[0];
    if (!firstCandidate) return;
    onChange([...relations, { change: null, to: firstCandidate.id, type: "" }]);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="font-medium text-sm">
          {t("analysis.characters.fields.relations")}
        </div>
        <Button
          disabled={candidates.length === 0}
          onClick={addRelation}
          size="sm"
          variant="outline"
        >
          <PlusIcon aria-hidden />
          {t("analysis.characters.relations.add")}
        </Button>
      </div>
      {candidates.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          {t("analysis.characters.relations.unavailable")}
        </p>
      ) : null}
      {relations.length > 0 ? (
        <div className="space-y-2">
          {relations.map((relation, index) => (
            <div
              className="grid gap-2 rounded-lg border p-3 md:grid-cols-[1.2fr_1fr_1.4fr_auto]"
              key={`${relation.to}-${index}`}
            >
              <Field className="w-full">
                <FieldLabel>
                  {t("analysis.characters.fields.relationTo")}
                </FieldLabel>
                <Select
                  itemToStringValue={(item) => item.value}
                  items={candidates.map((candidate) => ({
                    label: candidate.name,
                    value: candidate.id,
                  }))}
                  onValueChange={(to) => {
                    if (to) updateRelation(index, { to: to.value });
                  }}
                  value={
                    candidates
                      .map((candidate) => ({
                        label: candidate.name,
                        value: candidate.id,
                      }))
                      .find((item) => item.value === relation.to) ?? null
                  }
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={t(
                        "analysis.characters.placeholders.relationTo",
                      )}
                    />
                  </SelectTrigger>
                  <SelectPopup>
                    {candidates.map((candidate) => (
                      <SelectItem
                        key={candidate.id}
                        value={{
                          label: candidate.name,
                          value: candidate.id,
                        }}
                      >
                        {candidate.name}
                      </SelectItem>
                    ))}
                  </SelectPopup>
                </Select>
              </Field>
              <Field className="w-full">
                <FieldLabel>
                  {t("analysis.characters.fields.relationType")}
                </FieldLabel>
                <Input
                  onChange={(event) =>
                    updateRelation(index, { type: event.target.value })
                  }
                  placeholder={t(
                    "analysis.characters.placeholders.relationType",
                  )}
                  value={relation.type}
                />
              </Field>
              <Field className="w-full">
                <FieldLabel>
                  {t("analysis.characters.fields.relationChange")}
                </FieldLabel>
                <Input
                  onChange={(event) =>
                    updateRelation(index, { change: event.target.value })
                  }
                  placeholder={t(
                    "analysis.characters.placeholders.relationChange",
                  )}
                  value={relation.change ?? ""}
                />
              </Field>
              <Button
                aria-label={t("analysis.characters.relations.remove")}
                className="self-end"
                onClick={() => removeRelation(index)}
                size="icon"
                variant="ghost"
              >
                <XIcon aria-hidden />
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-muted-foreground text-sm">
          {t("analysis.characters.relations.empty")}
        </p>
      )}
    </div>
  );
}
