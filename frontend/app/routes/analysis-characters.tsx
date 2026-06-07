import cytoscape, {
  type Core as CytoscapeCore,
  type ElementDefinition,
} from "cytoscape";
import {
  CheckCircleIcon,
  PlusIcon,
  RefreshCwIcon,
  UsersIcon,
  XIcon,
} from "lucide-react";
import type * as React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useOutletContext, useRevalidator } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/analysis-characters";
import type { AnalysisLayoutContext } from "./analysis-layout";
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
import { Button } from "~/components/ui/button";
import {
  Drawer,
  DrawerClose,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerPanel,
  DrawerPopup,
  DrawerTitle,
  DrawerTrigger,
} from "~/components/ui/drawer";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "~/components/ui/empty";
import { Field, FieldLabel } from "~/components/ui/field";
import { Input } from "~/components/ui/input";
import {
  Select,
  SelectItem,
  SelectPopup,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
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

const roleColors: Record<CharacterRole, string> = {
  mentioned: "#8f8f8f",
  protagonist: "#d9a700",
  supporting: "#4f8f8a",
};

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
  const { setActions } = useOutletContext<AnalysisLayoutContext>();
  const { characters, understanding, projectId } = loaderData;
  const [working, setWorking] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [form, setForm] = useState<CharacterFormState>(emptyCharacterForm);
  const [deleteTarget, setDeleteTarget] = useState<Character | null>(null);
  const locked = understanding?.state !== "confirmed";
  const status = characters?.state ?? "empty";
  const characterList = useMemo(
    () => characters?.data.characters ?? [],
    [characters],
  );
  const editingCharacterId = form.id;

  const refresh = useCallback(async (): Promise<void> => {
    await revalidator.revalidate();
  }, [revalidator]);

  const openCreateDrawer = useCallback((): void => {
    setForm(emptyCharacterForm());
    setDrawerOpen(true);
  }, []);

  const openEditDrawer = useCallback((character: Character): void => {
    setForm(characterToForm(character));
    setDrawerOpen(true);
  }, []);

  const requestDeleteEditingCharacter = useCallback((): void => {
    if (!editingCharacterId) return;
    const target = characterList.find(
      (character) => character.id === editingCharacterId,
    );
    if (!target) return;
    setDeleteTarget(target);
    setDrawerOpen(false);
  }, [characterList, editingCharacterId]);

  const generateCharacters = useCallback(async (): Promise<void> => {
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
  }, [projectId, refresh, t]);

  const saveCharacter = useCallback(async (): Promise<void> => {
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
      setDrawerOpen(false);
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
  }, [characterList, editingCharacterId, form, projectId, refresh, t]);

  const deleteCharacter = useCallback(async (): Promise<void> => {
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
  }, [deleteTarget, projectId, refresh, t]);

  const confirmCharacters = useCallback(async (): Promise<void> => {
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
  }, [projectId, refresh, t]);

  useEffect(() => {
    if (locked || !characters) {
      setActions(null);
      return;
    }

    setActions(
      <>
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
        <Drawer onOpenChange={setDrawerOpen} open={drawerOpen} position="right">
          <DrawerTrigger render={<Button onClick={openCreateDrawer} />}>
            <PlusIcon aria-hidden />
            {t("analysis.characters.addCharacter")}
          </DrawerTrigger>
          <CharacterDrawer
            characters={characterList}
            form={form}
            onFormChange={setForm}
            onRequestDelete={requestDeleteEditingCharacter}
            onSave={saveCharacter}
            projectWorking={working}
          />
        </Drawer>
        {status !== "confirmed" ? (
          <Button loading={working} onClick={confirmCharacters}>
            <CheckCircleIcon aria-hidden />
            {t("analysis.characters.confirm")}
          </Button>
        ) : (
          <Button
            render={<Link to={analysisStepPath(projectId, "intent")} />}
            variant="secondary"
          >
            {t("analysis.characters.confirmCta")}
          </Button>
        )}
      </>,
    );

    return () => setActions(null);
  }, [
    characterList,
    characters,
    confirmCharacters,
    drawerOpen,
    form,
    generateCharacters,
    locked,
    openCreateDrawer,
    projectId,
    requestDeleteEditingCharacter,
    saveCharacter,
    setActions,
    status,
    t,
    working,
  ]);

  return (
    <section className="h-full space-y-4">
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
        <div className="h-full min-h-0">
          <CharacterGraph
            characters={characterList}
            onNodeClick={openEditDrawer}
          />
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

function CharacterGraph({
  characters,
  onNodeClick,
}: {
  characters: Character[];
  onNodeClick: (character: Character) => void;
}): React.ReactElement {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<CytoscapeCore | null>(null);
  const charactersRef = useRef(characters);
  const onNodeClickRef = useRef(onNodeClick);
  const elements = useMemo(
    () => buildCharacterGraphElements(characters),
    [characters],
  );

  useEffect(() => {
    charactersRef.current = characters;
    onNodeClickRef.current = onNodeClick;
  }, [characters, onNodeClick]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const graph = cytoscape({
      container,
      elements,
      layout: {
        animate: true,
        animationDuration: 500,
        fit: true,
        name: "cose",
        nodeRepulsion: 5200,
        padding: 48,
      },
      maxZoom: 2.4,
      minZoom: 0.45,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            "border-color": "#ffffff",
            "border-opacity": 0.92,
            "border-width": 2,
            color: "#1f2933",
            content: "data(label)",
            "font-family":
              "IBM Plex Sans, IBM Plex Sans SC, Noto Sans SC, sans-serif",
            "font-size": 12,
            "font-weight": 600,
            height: "mapData(weight, 1, 4, 36, 58)",
            label: "data(label)",
            "overlay-opacity": 0,
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.78,
            "text-background-padding": "3px",
            "text-margin-y": -10,
            "text-outline-width": 0,
            "text-valign": "top",
            width: "mapData(weight, 1, 4, 36, 58)",
          },
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "font-family":
              "IBM Plex Sans, IBM Plex Sans SC, Noto Sans SC, sans-serif",
            "font-size": 10,
            label: "data(label)",
            "line-color": "#b9b2a3",
            opacity: 0.74,
            "target-arrow-color": "#b9b2a3",
            "target-arrow-shape": "triangle",
            "text-background-color": "#faf9f7",
            "text-background-opacity": 0.84,
            "text-background-padding": "2px",
            "text-rotation": "autorotate",
            width: 1.25,
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#d9a700",
            "border-width": 4,
          },
        },
        {
          selector: "edge:selected",
          style: {
            "line-color": "#d9a700",
            "target-arrow-color": "#d9a700",
            width: 2,
          },
        },
      ],
      wheelSensitivity: 0.18,
    });

    graph.on("tap", "node", (event) => {
      const id = event.target.id();
      const character = charactersRef.current.find((item) => item.id === id);
      if (character) onNodeClickRef.current(character);
    });

    graphRef.current = graph;

    return () => {
      graph.destroy();
      graphRef.current = null;
    };
  }, [elements]);

  useEffect(() => {
    const graph = graphRef.current;
    if (!graph) return;

    graph.json({ elements });
    graph
      .layout({
        animate: true,
        animationDuration: 450,
        fit: true,
        name: "cose",
        nodeRepulsion: 5200,
        padding: 48,
      })
      .run();
  }, [elements]);

  return (
    <section
      aria-label={t("analysis.characters.graphLabel")}
      className="h-full"
    >
      <div
        className="h-full min-h-[30rem] overflow-hidden rounded-lg border bg-background"
        ref={containerRef}
      />
    </section>
  );
}

function buildCharacterGraphElements(
  characters: Character[],
): ElementDefinition[] {
  const ids = new Set(characters.map((character) => character.id));
  const relationCounts = new Map<string, number>();

  for (const character of characters) {
    relationCounts.set(
      character.id,
      character.relations.filter((relation) => ids.has(relation.to)).length,
    );
    for (const relation of character.relations) {
      if (!ids.has(relation.to)) continue;
      relationCounts.set(
        relation.to,
        (relationCounts.get(relation.to) ?? 0) + 1,
      );
    }
  }

  const nodes: ElementDefinition[] = characters.map((character) => ({
    data: {
      color: roleColors[character.role],
      id: character.id,
      label: character.name,
      role: character.role,
      weight: Math.min((relationCounts.get(character.id) ?? 0) + 1, 4),
    },
    group: "nodes",
  }));

  const edges: ElementDefinition[] = characters.flatMap((character) =>
    character.relations
      .filter((relation) => ids.has(relation.to))
      .map((relation, index) => ({
        data: {
          id: `${character.id}-${relation.to}-${index}`,
          label: relation.type,
          source: character.id,
          target: relation.to,
        },
        group: "edges",
      })),
  );

  return [...nodes, ...edges];
}

function CharacterDrawer({
  characters,
  form,
  onFormChange,
  onRequestDelete,
  onSave,
  projectWorking,
}: {
  characters: Character[];
  form: CharacterFormState;
  onFormChange: React.Dispatch<React.SetStateAction<CharacterFormState>>;
  onRequestDelete: () => void;
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
    <DrawerPopup showCloseButton variant="inset">
      <DrawerHeader>
        <DrawerTitle>
          {isEditing
            ? t("analysis.characters.editCharacter")
            : t("analysis.characters.addCharacter")}
        </DrawerTitle>
        <DrawerDescription>
          {t("analysis.characters.cardDescription")}
        </DrawerDescription>
      </DrawerHeader>
      <DrawerPanel className="space-y-4">
        <div className="grid gap-4">
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
      </DrawerPanel>
      <DrawerFooter>
        {isEditing ? (
          <Button
            className="me-auto"
            onClick={onRequestDelete}
            type="button"
            variant="destructive"
          >
            {t("analysis.characters.deleteCharacter")}
          </Button>
        ) : null}
        <DrawerClose render={<Button type="button" variant="ghost" />}>
          {t("analysis.characters.cancel")}
        </DrawerClose>
        <Button disabled={!canSave} loading={projectWorking} onClick={onSave}>
          {isEditing
            ? t("analysis.characters.saveCharacter")
            : t("analysis.characters.createCharacter")}
        </Button>
      </DrawerFooter>
    </DrawerPopup>
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
