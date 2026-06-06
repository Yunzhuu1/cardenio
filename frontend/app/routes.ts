import {
  type RouteConfig,
  index,
  layout,
  route,
} from "@react-router/dev/routes";

export default [
  layout("routes/app-shell.tsx", [
    index("routes/overview.tsx"),
    route("projects/:projectId", "routes/project-layout.tsx", [
      index("routes/project-index.tsx"),
      route("import", "routes/project-import.tsx"),
      route("analysis", "routes/analysis-layout.tsx", [
        index("routes/analysis-understanding.tsx"),
        route("characters", "routes/analysis-characters.tsx"),
        route("intent", "routes/analysis-intent.tsx"),
      ]),
      route("outline", "routes/project-outline.tsx"),
      route("script", "routes/project-script.tsx"),
      route("editor", "routes/project-editor.tsx"),
      route("report", "routes/project-report.tsx"),
      route("settings", "routes/project-settings.tsx"),
    ]),
  ]),
] satisfies RouteConfig;
