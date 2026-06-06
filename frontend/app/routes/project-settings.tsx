import { SettingsIcon } from "lucide-react";
import { StagePlaceholder } from "~/components/stage-placeholder";

export default function ProjectSettings(): React.ReactElement {
  return <StagePlaceholder icon={SettingsIcon} stageKey="settings" />;
}
