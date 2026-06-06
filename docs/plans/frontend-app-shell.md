# Plan: 前端应用外壳 + 项目作用域路由 + API 客户端层（含 mock）

> 分支：建议 `feat/frontend-app-shell`（从 `main` 切出）。覆盖 MVP 路线图 **M0-T1 基础路由** 与 **M0-T3 工件存储/项目容器**的前端接入面（API 客户端契约 + mock）。

---

## Context（为什么这么做）

前端目前只有脚手架交付的**单一演示首页**（[frontend/app/routes.ts](../../frontend/app/routes.ts) 仅 `index("routes/home.tsx")`）。需要补齐业务导航骨架。经与产品确认了**信息架构**与**数据接入**两项关键决策：

**信息架构（IA）——两条导航轴分离：**
- 产品的数据模型是「一次改编 = 一个 **Project**，下挂有序、可编辑、可版本化的工件」（[design.md §3.1](../design/design.md)、[api.md §2.1](../design/api.md)）。
- 流程是**线性 + 确认关卡（幕/幕间）**（[api.md §2.2 状态机](../design/api.md)、[visual-style §1/§6 幕隐喻](../design/visual-style.md)）。
- 因此：**侧边栏 = 项目轨**（项目列表 + 新建 + 全部项目）；**内容区顶部 = 「幕」步骤条**（导入→理解→大纲→剧本→打磨→报告），承载进度与门控。用户**通过侧栏切换项目、通过幕步骤条切换工序**。
- 路由形态为**项目作用域** `/projects/:projectId/<stage>`——脱离项目的 `/outline` 在数据模型上不成立。

**数据接入——先写 API 契约再 mock：**
- 按 [api.md](../design/api.md) 写一层**类型化 API 客户端**（`app/lib/api/`），含真实 `fetch` 实现（`http.ts`，打 `/api/v1`，按 §1.6 错误模型）与**内存 mock 适配器**（`mock.ts`，假后端）。
- 二者实现同一 `ApiClient` 接口，经 `import.meta.env.VITE_API_MODE`（默认 `mock`）切换。**接真实后端 = 设 `VITE_API_MODE=http`，组件零改动。**
- 路由用 React Router v7 的 **`clientLoader`/`clientAction`** 调客户端（SPA `ssr:false` 下服务端 loader 不运行，必须用 client 版）。项目列表/详情由 API 驱动，**不在组件里硬编码示例项目**（seed 数据只存在于 mock「假服务端」层）。

**验收口径**：应用可启动；侧栏列出（mock 的）项目并可切换；进入项目显示幕步骤条 + 六个阶段占位页 + 项目设置占位；新建项目走 `POST /projects` mock 后跳到 `/projects/:id/import`；`VITE_API_MODE=http` 时改打真实 `/api/v1`。

**依赖**：**零新增**。数据层用 RR v7 内置 loader/action（不引入 TanStack Query/Zustand）；mock 为本地适配器（评估过 MSW，为保持零依赖改用适配器模式）。

---

## 路由结构（`routes.ts`）

```text
app-shell (布局: 侧栏=项目轨 + 顶栏)
├── index "/"                         → 概览/全部项目（list + 新建）
└── projects/:projectId (project-layout: 加载项目 + 幕步骤条 + 项目头)
    ├── index                         → 重定向到 ./import
    ├── import / analysis / outline / script / editor / report   ← 6 幕占位
    └── settings                      ← 项目设置占位（齿轮入口，不在幕内）
```

> 「设置」按 [api.md §13](../design/api.md) 是**项目作用域**（`/projects/:id/settings`），故放在项目内（项目头齿轮），不作全局菜单。UI 语言/主题在顶栏（全局）。
> 「analysis」一页覆盖 M2 作品理解 + 人物档案 + M3 意图/方向（MVP 七目录无独立 intent 路由）。

---

## 文件清单

**新增 · API 客户端层（4）**
- `frontend/app/lib/api/types.ts` — 契约类型（对齐 api.md §3/§14）
- `frontend/app/lib/api/client.ts` — `ApiClient` 接口 + 按 env 选择实现
- `frontend/app/lib/api/http.ts` — 真实 `fetch` 实现（`/api/v1`）
- `frontend/app/lib/api/mock.ts` — 内存 mock 适配器（假后端 + seed）

**新增 · 其它支撑（3）**
- `frontend/app/lib/stages.ts` — 幕步骤元数据 + 路径/状态助手
- `frontend/app/components/stage-placeholder.tsx` — 通用占位组件
- `frontend/app/vite-env.d.ts` — 声明 `VITE_API_MODE` 环境变量类型

**新增 · 路由（11）**
- `frontend/app/routes/app-shell.tsx`（布局，含 `clientLoader` 列项目）
- `frontend/app/routes/overview.tsx`（index，`clientLoader` + `clientAction` 新建）
- `frontend/app/routes/project-layout.tsx`（项目布局，`clientLoader` 取项目 + 幕步骤条）
- `frontend/app/routes/project-index.tsx`（index → 重定向到 import）
- `frontend/app/routes/project-{import,analysis,outline,script,editor,report,settings}.tsx`（7 个占位）

**修改（3）+ 删除（1）**
- 改 `frontend/app/routes.ts`、`frontend/app/root.tsx`（加 `HydrateFallback`）、两个 `i18n/locales/*/common.json`
- 删 `frontend/app/routes/home.tsx`（由 overview 取代；同时删 `home.*` i18n 键）

> [trust-chips.tsx](../../frontend/app/components/trust-chips.tsx) 暂不被任何路由引用，**保留**（它是 M6 编辑器真正的信任标记 UI），`trust.*` 键一并保留以便其编译。

---

## 实现细节（含完整代码，按文件照抄）

### A. API 客户端层

#### `frontend/app/lib/api/types.ts`
```ts
// 对齐 docs/design/api.md §3（项目管理）与 §14（通用对象）。字段命名为最终契约。
export type ProjectId = string; // "prj_*"

export type UiLanguage = "zh-CN" | "en";
export type SourceLanguage = "zh-CN" | "en" | "mixed" | "unknown";
export type OutputLanguage = "zh-CN" | "en";

export type AdaptationDirection =
  | "faithful" | "cinematic" | "short_drama" | "tv" | "film" | "stage";

// §2.2 状态机 + API-1 创建后的 "empty"
export type ProjectState =
  | "empty" | "imported" | "understood" | "profiled" | "intent_set"
  | "outlined" | "generated" | "editing" | "report" | "exported";

export type GateState = "empty" | "draft" | "confirmed";

export type ProjectGates = {
  understanding: GateState;
  characters: GateState;
  outline: GateState;
};

export type ProjectMeta = {
  ui_language: UiLanguage;
  source_language: SourceLanguage;
  output_language: OutputLanguage;
  adaptation_direction: AdaptationDirection | null;
  style_fingerprint: string | null;
};

// 列表项（API-2 列表：id/title/state/updated_at）
export type ProjectSummary = {
  id: ProjectId;
  title: string;
  state: ProjectState;
  updated_at: string; // ISO-8601 UTC
};

// 详情（API-2 详情：含 state 与各工件 gates）
export type Project = ProjectSummary & {
  meta: ProjectMeta;
  gates: ProjectGates;
};

// API-1 创建项目请求体
export type CreateProjectInput = {
  title: string;
  ui_language: UiLanguage;
  source_language: SourceLanguage;
  output_language: OutputLanguage;
  adaptation_direction: AdaptationDirection | null;
};

// API-2 PATCH 改 meta
export type PatchProjectInput = Partial<
  Pick<CreateProjectInput, "title" | "source_language" | "output_language" | "adaptation_direction">
>;

// §1.5 游标分页
export type Paginated<T> = { items: T[]; next_cursor: string | null };

// §1.6 统一错误模型
export type ApiErrorBody = {
  code: string;
  message: string;
  retryable: boolean;
  details?: Record<string, unknown>;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;
  readonly details?: Record<string, unknown>;
  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.retryable = body.retryable;
    this.details = body.details;
  }
}
```

#### `frontend/app/lib/api/client.ts`
```ts
import type {
  CreateProjectInput, Paginated, PatchProjectInput, Project, ProjectId, ProjectSummary,
} from "./types";
import { mockClient } from "./mock";
import { httpClient } from "./http";

export type ProjectsApi = {
  list(params?: { limit?: number; cursor?: string }): Promise<Paginated<ProjectSummary>>;
  get(id: ProjectId): Promise<Project>;
  create(input: CreateProjectInput): Promise<Project>;
  patch(id: ProjectId, input: PatchProjectInput): Promise<Project>;
  remove(id: ProjectId): Promise<void>;
};

// 后续里程碑在此扩展：source / understanding / characters / outline / screenplay / report。
export type ApiClient = {
  projects: ProjectsApi;
};

const mode = import.meta.env.VITE_API_MODE ?? "mock";

export const api: ApiClient = mode === "http" ? httpClient : mockClient;
```

#### `frontend/app/lib/api/http.ts`
```ts
import type { ApiClient } from "./client";
import { ApiError, type ApiErrorBody } from "./types";

const BASE_URL = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      // §1.3 UI 语言走 Accept-Language；§1.2 鉴权 token 待选型（开放问题 A1）后补
      "Accept-Language":
        typeof document !== "undefined" ? document.documentElement.lang || "zh-CN" : "zh-CN",
      ...init?.headers,
    },
  });

  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const body = (payload?.error ?? {
      code: "unknown",
      message: response.statusText,
      retryable: false,
    }) as ApiErrorBody;
    throw new ApiError(response.status, body);
  }

  return payload as T;
}

export const httpClient: ApiClient = {
  projects: {
    list: (params) => {
      const search = new URLSearchParams();
      if (params?.limit) search.set("limit", String(params.limit));
      if (params?.cursor) search.set("cursor", params.cursor);
      const qs = search.toString();
      return request(`/projects${qs ? `?${qs}` : ""}`);
    },
    get: (id) => request(`/projects/${id}`),
    create: (input) =>
      request(`/projects`, { method: "POST", body: JSON.stringify(input) }),
    patch: (id, input) =>
      request(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
    remove: (id) =>
      request<void>(`/projects/${id}`, { method: "DELETE" }).then(() => undefined),
  },
};
```

#### `frontend/app/lib/api/mock.ts`
```ts
import type { ApiClient } from "./client";
import {
  ApiError, type CreateProjectInput, type Paginated, type PatchProjectInput,
  type Project, type ProjectId, type ProjectSummary,
} from "./types";

const LATENCY_MS = 300;
const delay = (): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, LATENCY_MS));

// 模拟「服务端状态」。这是假后端的数据，不是 UI 层硬编码示例——
// 接真实后端时整层被 http.ts 取代（VITE_API_MODE=http），组件零改动。
// 注意：内存存储，刷新页面即重置（mock 限制，可接受）。
const store = new Map<ProjectId, Project>();
let seeded = false;

function ensureSeed(): void {
  if (seeded) return;
  seeded = true;
  // 想测试空状态时，把下面数组清空即可。
  const seeds: Project[] = [
    {
      id: "prj_demo_outlined",
      title: "旧书店的信",
      state: "outlined",
      updated_at: "2026-06-05T09:00:00Z",
      meta: {
        ui_language: "zh-CN", source_language: "zh-CN", output_language: "zh-CN",
        adaptation_direction: "short_drama", style_fingerprint: "克制、冷硬、意象密集",
      },
      gates: { understanding: "confirmed", characters: "confirmed", outline: "draft" },
    },
    {
      id: "prj_demo_imported",
      title: "山中来信",
      state: "imported",
      updated_at: "2026-06-04T14:30:00Z",
      meta: {
        ui_language: "zh-CN", source_language: "zh-CN", output_language: "zh-CN",
        adaptation_direction: null, style_fingerprint: null,
      },
      gates: { understanding: "empty", characters: "empty", outline: "empty" },
    },
  ];
  for (const project of seeds) store.set(project.id, project);
}

let counter = 0;
function nextId(): ProjectId {
  counter += 1;
  return `prj_${Date.now().toString(36)}${counter}`;
}

export const mockClient: ApiClient = {
  projects: {
    async list() {
      ensureSeed();
      await delay();
      const items: ProjectSummary[] = [...store.values()]
        .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))
        .map(({ id, title, state, updated_at }) => ({ id, title, state, updated_at }));
      return { items, next_cursor: null } satisfies Paginated<ProjectSummary>;
    },
    async get(id) {
      ensureSeed();
      await delay();
      const project = store.get(id);
      if (!project) {
        throw new ApiError(404, { code: "not_found", message: "项目不存在", retryable: false });
      }
      return project;
    },
    async create(input: CreateProjectInput) {
      ensureSeed();
      await delay();
      const id = nextId();
      const project: Project = {
        id,
        title: input.title,
        state: "empty",
        updated_at: new Date().toISOString(),
        meta: {
          ui_language: input.ui_language,
          source_language: input.source_language,
          output_language: input.output_language,
          adaptation_direction: input.adaptation_direction,
          style_fingerprint: null,
        },
        gates: { understanding: "empty", characters: "empty", outline: "empty" },
      };
      store.set(id, project);
      return project;
    },
    async patch(id, input: PatchProjectInput) {
      ensureSeed();
      await delay();
      const project = store.get(id);
      if (!project) {
        throw new ApiError(404, { code: "not_found", message: "项目不存在", retryable: false });
      }
      const updated: Project = {
        ...project,
        title: input.title ?? project.title,
        meta: {
          ...project.meta,
          source_language: input.source_language ?? project.meta.source_language,
          output_language: input.output_language ?? project.meta.output_language,
          adaptation_direction:
            input.adaptation_direction ?? project.meta.adaptation_direction,
        },
        updated_at: new Date().toISOString(),
      };
      store.set(id, updated);
      return updated;
    },
    async remove(id) {
      ensureSeed();
      await delay();
      store.delete(id);
    },
  },
};
```

#### `frontend/app/vite-env.d.ts`
```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_MODE?: "mock" | "http";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

### B. 幕步骤元数据 `frontend/app/lib/stages.ts`
```ts
import {
  BookOpenIcon, ClapperboardIcon, Columns2Icon, FileInputIcon,
  ListTreeIcon, ScrollTextIcon, type LucideIcon,
} from "lucide-react";
import type { ProjectState } from "./api/types";

export type Stage = { key: string; segment: string; icon: LucideIcon };

// 六幕，顺序即 api.md §2.2 状态机推进顺序。
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

const stateOrder: ProjectState[] = [
  "empty", "imported", "understood", "profiled", "intent_set",
  "outlined", "generated", "editing", "report", "exported",
];

// 每个幕「完成」所对应、达到即视为已过的项目状态。
const stageDoneAt: Record<string, ProjectState> = {
  import: "imported",
  analysis: "intent_set", // analysis 覆盖 understood→profiled→intent_set
  outline: "outlined",
  script: "generated",
  editor: "editing",
  report: "report",
};

export function isStageDone(stageKey: string, projectState: ProjectState): boolean {
  return stateOrder.indexOf(projectState) >= stateOrder.indexOf(stageDoneAt[stageKey]);
}
```
> 8 个 lucide 图标名均存在于 `lucide-react@^1.17`。

### C. 占位组件 `frontend/app/components/stage-placeholder.tsx`
```tsx
import type { LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { stages } from "~/lib/stages";

export function StagePlaceholder({
  stageKey,
  icon,
}: {
  stageKey: string;
  icon?: LucideIcon;
}): React.ReactElement {
  const { t } = useTranslation();
  const Icon = icon ?? stages.find((stage) => stage.key === stageKey)?.icon;

  return (
    <section className="flex min-h-[40dvh] flex-col items-start justify-center gap-4">
      <span className="inline-flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
        {t(`pages.${stageKey}.milestone`)} · {t("placeholder.badge")}
      </span>
      <div className="flex items-center gap-3">
        {Icon && (
          <span className="flex size-10 items-center justify-center rounded-lg border border-border bg-card text-primary">
            <Icon aria-hidden className="size-5" />
          </span>
        )}
        <h2 className="text-xl font-semibold tracking-normal text-foreground">
          {t(`pages.${stageKey}.title`)}
        </h2>
      </div>
      <p className="max-w-2xl text-base leading-7 text-muted-foreground">
        {t(`pages.${stageKey}.description`)}
      </p>
      <p className="text-sm text-muted-foreground">{t("placeholder.note")}</p>
    </section>
  );
}
```

### D. 路由

#### `frontend/app/routes.ts`（改）
```ts
import {
  type RouteConfig, index, layout, route,
} from "@react-router/dev/routes";

export default [
  layout("routes/app-shell.tsx", [
    index("routes/overview.tsx"),
    route("projects/:projectId", "routes/project-layout.tsx", [
      index("routes/project-index.tsx"),
      route("import", "routes/project-import.tsx"),
      route("analysis", "routes/project-analysis.tsx"),
      route("outline", "routes/project-outline.tsx"),
      route("script", "routes/project-script.tsx"),
      route("editor", "routes/project-editor.tsx"),
      route("report", "routes/project-report.tsx"),
      route("settings", "routes/project-settings.tsx"),
    ]),
  ]),
] satisfies RouteConfig;
```

#### `frontend/app/routes/app-shell.tsx`（布局，侧栏=项目轨）
```tsx
import { LayoutGridIcon, PlusIcon } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/app-shell";
import { LanguageSwitcher } from "~/components/language-switcher";
import { ThemeToggle } from "~/components/theme-toggle";
import { api } from "~/lib/api/client";
import { cn } from "~/lib/utils";

const linkBase =
  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors";
const linkActive = "bg-sidebar-accent text-sidebar-foreground";
const linkIdle =
  "text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground";

export async function clientLoader() {
  const { items } = await api.projects.list();
  return { projects: items };
}

export default function AppShell({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const { projects } = loaderData;

  return (
    <div className="flex min-h-dvh bg-background text-foreground">
      <aside className="hidden w-64 shrink-0 flex-col gap-2 border-r border-sidebar-border bg-sidebar px-3 py-4 md:flex">
        <div className="px-2 pb-2 text-sm font-semibold text-sidebar-foreground">
          {t("app.name")}
        </div>

        <NavLink
          to="/"
          end
          className={({ isActive }) => cn(linkBase, isActive ? linkActive : linkIdle)}
        >
          <LayoutGridIcon aria-hidden className="size-4" />
          {t("nav.allProjects")}
        </NavLink>

        <div className="mt-3 px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {t("nav.projectsHeading")}
        </div>

        <nav aria-label={t("nav.label")} className="flex flex-col gap-1">
          {projects.length === 0 ? (
            <p className="px-3 py-2 text-sm text-muted-foreground">
              {t("nav.noProjects")}
            </p>
          ) : (
            projects.map((project) => (
              <NavLink
                key={project.id}
                to={`/projects/${project.id}`}
                className={({ isActive }) =>
                  cn(linkBase, isActive ? linkActive : linkIdle)
                }
              >
                <span className="truncate">{project.title}</span>
              </NavLink>
            ))
          )}
        </nav>

        <NavLink to="/" end className={cn(linkBase, "mt-2 text-primary")}>
          <PlusIcon aria-hidden className="size-4" />
          {t("nav.newProject")}
        </NavLink>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border px-5 py-3 sm:px-8">
          <NavLink to="/" className="text-sm font-semibold text-foreground md:hidden">
            {t("app.name")}
          </NavLink>
          <div className="hidden md:block" aria-hidden />
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <ThemeToggle />
          </div>
        </header>
        <main className="min-w-0 flex-1 px-5 py-8 sm:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```
> 侧栏在 `<md` 隐藏；移动端经顶栏左上角「Cardenio 入戏」链接回到 `/` 概览换项目（响应式抽屉留作后续）。「新建项目」链接到概览（创建表单在那里）。

#### `frontend/app/routes/overview.tsx`（index：列表 + 新建）
```tsx
import { PlusIcon } from "lucide-react";
import { Form, Link, redirect, useNavigation } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/overview";
import { Button } from "~/components/ui/button";
import { api } from "~/lib/api/client";
import { stagePath } from "~/lib/stages";
import type { UiLanguage } from "~/lib/api/types";

export function meta() {
  return [
    { title: "Cardenio 入戏" },
    { name: "description", content: "AI-assisted novel-to-script adaptation." },
  ];
}

export async function clientLoader() {
  const { items } = await api.projects.list();
  return { projects: items };
}

export async function clientAction({ request }: Route.ClientActionArgs) {
  const form = await request.formData();
  const title = String(form.get("title") || "Untitled");
  const language = String(form.get("language") || "zh-CN") as UiLanguage;
  const project = await api.projects.create({
    title,
    ui_language: language,
    source_language: language,
    output_language: language,
    adaptation_direction: null,
  });
  return redirect(stagePath(project.id, "import"));
}

export default function Overview({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t, i18n } = useTranslation();
  const { projects } = loaderData;
  const navigation = useNavigation();
  const creating = navigation.state !== "idle";

  return (
    <div className="mx-auto w-full max-w-5xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-normal text-foreground">
            {t("overview.title")}
          </h1>
          <p className="mt-2 max-w-2xl text-base leading-7 text-muted-foreground">
            {t("overview.description")}
          </p>
        </div>
        <Form method="post">
          <input type="hidden" name="title" value={t("overview.newProjectTitle")} />
          <input type="hidden" name="language" value={i18n.resolvedLanguage || "zh-CN"} />
          <Button type="submit" loading={creating}>
            <PlusIcon aria-hidden />
            {t("overview.newProject")}
          </Button>
        </Form>
      </div>

      {projects.length === 0 ? (
        <div className="mt-10 rounded-lg border border-dashed border-border p-10 text-center text-muted-foreground">
          {t("overview.empty")}
        </div>
      ) : (
        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="flex flex-col gap-2 rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/40"
            >
              <div className="font-medium text-foreground">{project.title}</div>
              <div className="text-sm text-muted-foreground">
                {t(`state.${project.state}`)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
```

#### `frontend/app/routes/project-layout.tsx`（项目布局：幕步骤条 + 项目头）
```tsx
import { CheckIcon, SettingsIcon } from "lucide-react";
import { NavLink, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import type { Route } from "./+types/project-layout";
import { api } from "~/lib/api/client";
import { cn } from "~/lib/utils";
import { isStageDone, stagePath, stages } from "~/lib/stages";

export async function clientLoader({ params }: Route.ClientLoaderArgs) {
  const project = await api.projects.get(params.projectId);
  return { project };
}

export function meta({ data }: Route.MetaArgs) {
  const title = data?.project?.title;
  return [{ title: title ? `${title} · Cardenio 入戏` : "Cardenio 入戏" }];
}

export default function ProjectLayout({
  loaderData,
}: Route.ComponentProps): React.ReactElement {
  const { t } = useTranslation();
  const { project } = loaderData;

  return (
    <div className="mx-auto w-full max-w-6xl">
      <div className="mb-6 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal text-foreground">
            {project.title}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t(`state.${project.state}`)}
          </p>
        </div>
        <NavLink
          to={stagePath(project.id, "settings")}
          aria-label={t("nav.projectSettings")}
          className={({ isActive }) =>
            cn(
              "flex size-9 items-center justify-center rounded-md border border-border",
              isActive ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent",
            )
          }
        >
          <SettingsIcon aria-hidden className="size-4" />
        </NavLink>
      </div>

      <nav
        aria-label={t("nav.stages")}
        className="mb-8 flex gap-2 overflow-x-auto border-b border-border pb-3"
      >
        {stages.map((stage, index) => {
          const done = isStageDone(stage.key, project.state);
          return (
            <NavLink
              key={stage.key}
              to={stagePath(project.id, stage.segment)}
              className={({ isActive }) =>
                cn(
                  "flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground",
                )
              }
            >
              <span
                className={cn(
                  "flex size-5 items-center justify-center rounded-full border text-xs",
                  done
                    ? "border-success bg-success text-success-foreground"
                    : "border-current",
                )}
              >
                {done ? <CheckIcon aria-hidden className="size-3" /> : index + 1}
              </span>
              {t(`steps.${stage.key}`)}
            </NavLink>
          );
        })}
      </nav>

      <Outlet />
    </div>
  );
}
```
> 幕的「已完成」状态由 `isStageDone(project.state)` 派生（success 勾），「当前」由 `NavLink` 的 `isActive`（primary 实底）表达。**本期不做硬门控**（占位页可自由跳转）；门控（`409 state_gate_blocked`）随各业务里程碑落地。

#### `frontend/app/routes/project-index.tsx`（index → 重定向到 import）
```ts
import { redirect } from "react-router";
import type { Route } from "./+types/project-index";

export function clientLoader({ params }: Route.ClientLoaderArgs) {
  return redirect(`/projects/${params.projectId}/import`);
}
```

#### 七个占位路由（统一模式）
以 `project-import.tsx` 为模板，其余按表替换 `stageKey` 与默认导出函数名：
```tsx
import { StagePlaceholder } from "~/components/stage-placeholder";

export default function ProjectImport(): React.ReactElement {
  return <StagePlaceholder stageKey="import" />;
}
```
- `project-analysis.tsx` → `"analysis"` / `ProjectAnalysis`
- `project-outline.tsx` → `"outline"` / `ProjectOutline`
- `project-script.tsx` → `"script"` / `ProjectScript`
- `project-editor.tsx` → `"editor"` / `ProjectEditor`
- `project-report.tsx` → `"report"` / `ProjectReport`
- `project-settings.tsx` → 传图标（不在 stages 内）：
```tsx
import { SettingsIcon } from "lucide-react";
import { StagePlaceholder } from "~/components/stage-placeholder";

export default function ProjectSettings(): React.ReactElement {
  return <StagePlaceholder stageKey="settings" icon={SettingsIcon} />;
}
```
> 占位路由不导出 `meta`，文档标题由 `project-layout` 的 `meta`（项目名）提供。

### E. `frontend/app/root.tsx`（加 `HydrateFallback`）

SPA 模式下根路由首屏运行 `clientLoader` 期间需要 `HydrateFallback`，否则白屏/告警。在文件追加（复用现有 [Spinner](../../frontend/app/components/ui/spinner.tsx)）：
```tsx
import { Spinner } from "~/components/ui/spinner";

export function HydrateFallback(): React.ReactElement {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-background">
      <Spinner className="size-6 text-muted-foreground" />
    </div>
  );
}
```
> `Layout`/`App`/`ErrorBoundary` 不变；`ErrorBoundary` 已处理 404（项目不存在时 `api.projects.get` 抛 `ApiError(404)`，RR 交给它渲染）。

### F. i18n（两个 JSON 全量替换）

**`frontend/app/i18n/locales/zh-CN/common.json`**（删除 `home.*`；新增 `overview`/`nav`/`steps`/`state`/`placeholder`/`pages`；保留 `app`/`trust`/`language`）：
```json
{
  "app": { "name": "Cardenio 入戏" },
  "overview": {
    "title": "改编项目",
    "description": "选择一个项目继续，或新建一个。每个项目从导入原文开始，逐幕推进到改编报告。",
    "newProject": "新建项目",
    "newProjectTitle": "未命名改编",
    "empty": "还没有项目。点击「新建项目」开始你的第一次改编。"
  },
  "nav": {
    "label": "项目导航",
    "allProjects": "全部项目",
    "projectsHeading": "项目",
    "noProjects": "暂无项目",
    "newProject": "新建项目",
    "stages": "改编步骤",
    "projectSettings": "项目设置"
  },
  "steps": {
    "import": "导入", "analysis": "理解与档案", "outline": "分场大纲",
    "script": "剧本", "editor": "打磨", "report": "报告"
  },
  "state": {
    "empty": "空项目", "imported": "已导入原文", "understood": "已生成作品理解",
    "profiled": "已生成人物档案", "intent_set": "已设定改编意图", "outlined": "已生成分场大纲",
    "generated": "已生成剧本初稿", "editing": "打磨中", "report": "已生成改编报告", "exported": "已导出"
  },
  "placeholder": {
    "badge": "占位页",
    "note": "此功能尚在规划中，当前为路由骨架占位。"
  },
  "pages": {
    "import": { "milestone": "M1", "title": "导入与预处理", "description": "粘贴或上传 TXT/DOCX 小说，按章节切分，校验不少于 3 章后进入下一步。" },
    "analysis": { "milestone": "M2 · M3", "title": "改编前理解与人物档案", "description": "生成可编辑的作品理解、人物档案、作者意图与改编方向；先理解，再改编。" },
    "outline": { "milestone": "M4", "title": "分场大纲", "description": "生成每场绑定 source_ref 的分场大纲，可增删、调序与逐字段编辑。" },
    "script": { "milestone": "M5", "title": "剧本生成", "description": "把大纲翻译为 YAML 剧本：心理外化、对白剧本化、加戏强标注与台词级溯源。" },
    "editor": { "milestone": "M6", "title": "打磨工作台", "description": "左原文右剧本双栏对照、选中局部重生成、所见即所得与留白标记。" },
    "report": { "milestone": "M7", "title": "改编取舍报告", "description": "汇总保留/删除/合并/新增/外化，与剧本标记一致，每条可定位到原文。" },
    "settings": { "milestone": "M8", "title": "项目设置", "description": "数据隐私与不用于训练承诺、镜头建议默认开关、存储区域等项目级设置。" }
  },
  "trust": { "source": "source_ref: ch3.p18", "inferred": "AI 新增", "todo": "TODO 待确认" },
  "language": { "label": "界面语言", "zh-CN": "中文", "en": "English" }
}
```

**`frontend/app/i18n/locales/en/common.json`**（同结构、键完全一致）：
```json
{
  "app": { "name": "Cardenio" },
  "overview": {
    "title": "Adaptation projects",
    "description": "Pick a project to continue, or start a new one. Each project begins with imported source text and advances act by act to the adaptation report.",
    "newProject": "New project",
    "newProjectTitle": "Untitled adaptation",
    "empty": "No projects yet. Click \"New project\" to start your first adaptation."
  },
  "nav": {
    "label": "Project navigation",
    "allProjects": "All projects",
    "projectsHeading": "Projects",
    "noProjects": "No projects yet",
    "newProject": "New project",
    "stages": "Adaptation stages",
    "projectSettings": "Project settings"
  },
  "steps": {
    "import": "Import", "analysis": "Understanding", "outline": "Outline",
    "script": "Screenplay", "editor": "Editing", "report": "Report"
  },
  "state": {
    "empty": "Empty", "imported": "Source imported", "understood": "Understanding generated",
    "profiled": "Profiles generated", "intent_set": "Intent set", "outlined": "Outline generated",
    "generated": "Draft generated", "editing": "Editing", "report": "Report generated", "exported": "Exported"
  },
  "placeholder": {
    "badge": "Placeholder",
    "note": "This feature is still planned; the page is a routing-scaffold placeholder."
  },
  "pages": {
    "import": { "milestone": "M1", "title": "Import & Preprocessing", "description": "Paste or upload TXT/DOCX novels, split by chapter, and validate at least 3 chapters before continuing." },
    "analysis": { "milestone": "M2 · M3", "title": "Understanding & Character Profiles", "description": "Generate editable story understanding, character profiles, author intent, and adaptation direction—understand first, then adapt." },
    "outline": { "milestone": "M4", "title": "Scene Outline", "description": "Generate a per-scene outline with source_ref bindings; add, remove, reorder, and edit fields." },
    "script": { "milestone": "M5", "title": "Screenplay Generation", "description": "Translate the outline into a YAML screenplay: externalization, dialogue scripting, added-content flags, and line-level sourcing." },
    "editor": { "milestone": "M6", "title": "Editing Workbench", "description": "Side-by-side source vs. screenplay, scoped regeneration, WYSIWYG editing, and TODO markers." },
    "report": { "milestone": "M7", "title": "Adaptation Report", "description": "Summarize kept/cut/merged/added/externalized changes, consistent with screenplay flags, each traceable to the source." },
    "settings": { "milestone": "M8", "title": "Project Settings", "description": "Privacy and no-training commitment, shot-hint defaults, storage region, and other project-level settings." }
  },
  "trust": { "source": "source_ref: ch3.p18", "inferred": "AI inferred", "todo": "TODO review" },
  "language": { "label": "UI language", "zh-CN": "中文", "en": "English" }
}
```
> 两个 locale 的键集合必须完全一致（缺键回退到 key 字符串，视为缺陷）。

---

## 关键技术约束（避免踩坑）

- **必须用 `clientLoader`/`clientAction`，不是 `loader`/`action`**：[react-router.config.ts](../../frontend/react-router.config.ts) 为 `ssr:false`，服务端 loader 运行时不触发。
- **根路由必须导出 `HydrateFallback`**（§E）：首屏 `clientLoader` 期间的占位，缺它会告警/白屏。
- **组件用 `Route.ComponentProps` 取 `loaderData`**（已是 [home.tsx](../../frontend/app/routes/home.tsx) 现有模式的延伸）；`meta` 用 `Route.MetaArgs` 的 `data`。
- **`Button` 提交**：传 `type="submit"`（[button.tsx](../../frontend/app/components/ui/button.tsx) 默认 `type="button"`，显式 `submit` 经 `mergeProps` 覆盖生效），`loading` 显示 Spinner。
- **`VITE_API_MODE`** 默认 `mock`，无需建 `.env`；接后端时 `VITE_API_MODE=http pnpm dev`（http.ts 打相对 `/api/v1`，跨域/代理在后端就绪时于 [vite.config.ts](../../frontend/vite.config.ts) 加 `server.proxy`，本期不做）。
- **鉴权**：http.ts 暂不带 `Authorization`（api.md §1.2 / 开放问题 A1 待选型），接入时在 `request()` 注入。

---

## 提交策略（Conventional Commits，ASCII，逐步可构建）

每步后 `lint` + `build` 通过（pre-commit 根 `lint`、pre-push 根 `build`，见 [lefthook.yml](../../lefthook.yml)）：

1. `feat(frontend): add typed api client with mock and http adapters` — `lib/api/*` + `vite-env.d.ts`（独立可编译，暂未被引用）。
2. `feat(frontend): add stage metadata and stage placeholder` — `lib/stages.ts` + `components/stage-placeholder.tsx` + i18n 增 `steps`/`state`/`placeholder`/`pages` 键。
3. `feat(frontend): add app shell and project-scoped routes` — `app-shell`/`overview`/`project-layout`/`project-index`/7 占位 + 改 `routes.ts` + `root.tsx` 加 `HydrateFallback` + i18n 增 `overview`/`nav`、删 `home.*`、删 `routes/home.tsx`。

> 提交时间落在 AGENTS.md 开发窗口内。

---

## 验证方式（端到端）

1. `pnpm install`（无新依赖）。
2. `pnpm dev`（默认 mock）：
   - 概览 `/`：显示 mock 的两个项目卡（「旧书店的信/已生成分场大纲」「山中来信/已导入原文」）+「新建项目」按钮；空状态可通过清空 mock seed 验证。
   - 点项目 → `/projects/:id/import`：顶部显示项目名 + 状态；幕步骤条六项，已完成幕显示 success 勾，当前幕 primary 实底；点各幕 URL 与高亮正确切换；齿轮进 `/projects/:id/settings`。
   - 侧栏：项目高亮随当前项目；跨幕切换时项目保持高亮；「全部项目」回到 `/`。
   - 新建项目：点击 → mock `create` → 跳到新项目 `/projects/prj_xxx/import`，侧栏出现新项目（按钮 loading 态可见）。
   - 顶栏语言/主题切换在所有路由可用，无闪烁；中英文案随之切换；亮/暗双主题下 sidebar/success/primary 配色正确。
   - 深链接 `/projects/prj_demo_outlined/outline` 直接可达；访问不存在项目 `/projects/prj_x/import` → 404（ErrorBoundary）。
   - 窄视口（`<md`）：侧栏隐藏，顶栏左上「Cardenio 入戏」回到概览；幕步骤条横向可滚动。
3. `VITE_API_MODE=http pnpm dev`：网络面板应出现对 `/api/v1/projects` 的真实请求（无后端则失败 → 验证已切到 http 适配器即可，证明切换生效）。
4. `pnpm typecheck`（`react-router typegen && tsc`）、`pnpm lint`、`pnpm format:check`、`pnpm build` 全过。
5. Hooks：测试提交触发 pre-commit `lint`、`git push` 触发 pre-push `build`，均通过。

---

## 关键复用与依据

- IA 两轴分离：[design.md §3.1 Project/工件](../design/design.md)、[api.md §2.1/§2.2](../design/api.md)、[visual-style §1/§6 幕隐喻](../design/visual-style.md)。
- API 契约逐字段对齐 [api.md §3 项目管理 / §14 通用对象 / §1.6 错误模型](../design/api.md)；设置项目作用域见 §13。
- 复用现有：`cn`（[utils.ts](../../frontend/app/lib/utils.ts)）、`Button`/`Spinner`、`LanguageSwitcher`/`ThemeToggle`、设计令牌（`sidebar-*`/`primary`/`success`，[app.css](../../frontend/app/app.css)）；路由 API `index/layout/route`、导航 `NavLink/Link/Outlet/Form/redirect/useNavigation`。

## 不在本 PR 范围

- 真实业务逻辑（导入解析、各阶段生成、状态机硬门控、SSE Job 流）——占位页保持纯表现层；`ApiClient` 仅含 `projects`，其余资源随各里程碑扩展。
- 移动端抽屉式侧栏、`vite` `/api` 代理、鉴权 token 注入、mock 持久化（刷新重置）。
- README 技术栈更新（脚手架计划遗留项，无新依赖，单列后续 PR）。
