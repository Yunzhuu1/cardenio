import {
  BookOpenIcon,
  ClapperboardIcon,
  Columns2Icon,
  FileInputIcon,
  ListTreeIcon,
  ScrollTextIcon,
  type LucideIcon,
} from "lucide-react";
import type { ProjectState } from "./api/types";

export type Stage = { key: string; segment: string; icon: LucideIcon };

export const stages: Stage[] = [
  { key: "import", segment: "import", icon: FileInputIcon },
  { key: "analysis", segment: "analysis", icon: BookOpenIcon },
  { key: "outline", segment: "outline", icon: ListTreeIcon },
  { key: "script", segment: "script", icon: ClapperboardIcon },
  { key: "editor", segment: "editor", icon: Columns2Icon },
  { key: "report", segment: "report", icon: ScrollTextIcon },
];

export function stagePath(projectId: string, segment: string): string {
  return `/projects/${projectId}/${segment}`;
}

export type AnalysisStep = "understanding" | "characters" | "intent";

export function analysisStepPath(
  projectId: string,
  step: AnalysisStep,
): string {
  const base = stagePath(projectId, "analysis");
  if (step === "understanding") return base;
  return `${base}/${step}`;
}

const stateOrder: ProjectState[] = [
  "empty",
  "imported",
  "understood",
  "profiled",
  "intent_set",
  "outlined",
  "generated",
  "editing",
  "report",
  "exported",
];

const stageDoneAt: Record<string, ProjectState> = {
  import: "imported",
  analysis: "intent_set",
  outline: "outlined",
  script: "generated",
  editor: "editing",
  report: "report",
};

export function isStageDone(
  stageKey: string,
  projectState: ProjectState,
): boolean {
  return (
    stateOrder.indexOf(projectState) >=
    stateOrder.indexOf(stageDoneAt[stageKey])
  );
}
