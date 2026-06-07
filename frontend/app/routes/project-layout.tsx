import { Outlet } from "react-router";
import type { Route } from "./+types/project-layout";
import { ScrollArea } from "~/components/ui/scroll-area";
import { api } from "~/lib/api/client";

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const project = await api.projects.get(params.projectId);
  return { project };
}

export function meta({ data }: Route.MetaArgs) {
  const title = data?.project?.title;
  return [{ title: title ? `${title} · Cardenio 入戏` : "Cardenio 入戏" }];
}

export default function ProjectLayout({}: Route.ComponentProps): React.ReactElement {
  return (
    <ScrollArea className="mx-auto h-full w-full max-w-6xl" scrollFade>
      <div className="px-5 py-8 sm:px-8">
        <Outlet />
      </div>
    </ScrollArea>
  );
}
