import { redirect } from "react-router";
import type { Route } from "./+types/project-index";

export function clientLoader({ params }: Route.ClientLoaderArgs) {
  return redirect(`/projects/${params.projectId}/import`);
}
