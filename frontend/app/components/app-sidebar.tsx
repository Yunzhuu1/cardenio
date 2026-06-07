import { LayoutGridIcon, LogOutIcon, PlusIcon } from "lucide-react";
import { NavLink, useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { LanguageSwitcher } from "~/components/language-switcher";
import { ThemeToggle } from "~/components/theme-toggle";
import { api } from "~/lib/api/client";
import type { AuthUser, ProjectSummary } from "~/lib/api/types";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "~/components/ui/sidebar";

export function AppSidebar({
  projects,
  user,
}: {
  projects: ProjectSummary[];
  user: AuthUser;
}): React.ReactElement {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [brandLatin, brandCjk] = t("app.name").split(" ");

  async function logout(): Promise<void> {
    await api.auth.logout().catch(() => undefined);
    navigate("/login", { replace: true });
  }

  return (
    <Sidebar variant="inset">
      <SidebarHeader>
        <div className="flex items-baseline gap-2 p-2 text-sidebar-foreground">
          <span className="[font-family:var(--font-brand-latin)] text-[1.75rem] font-light italic leading-none">
            {brandLatin}
          </span>
          {brandCjk && (
            <span className="relative -top-0.25 [font-family:var(--font-brand-cjk)] text-base font-normal leading-none">
              {brandCjk}
            </span>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton render={<NavLink end to="/" />}>
              <LayoutGridIcon aria-hidden="true" />
              {t("nav.allProjects")}
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        <SidebarGroup className="mt-3">
          <SidebarGroupLabel>{t("nav.projectsHeading")}</SidebarGroupLabel>
          <SidebarGroupContent>
            <nav aria-label={t("nav.label")}>
              {projects.length === 0 ? (
                <p className="px-3 py-2 text-sm text-muted-foreground">
                  {t("nav.noProjects")}
                </p>
              ) : (
                <SidebarMenu>
                  {projects.map((project) => (
                    <SidebarMenuItem key={project.id}>
                      <SidebarMenuButton
                        render={<NavLink to={`/projects/${project.id}`} />}
                      >
                        <span className="truncate">{project.title}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              )}
            </nav>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              className="text-primary"
              render={<NavLink end to="/" />}
            >
              <PlusIcon aria-hidden="true" />
              {t("nav.newProject")}
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        <SidebarSeparator />

        <div className="grid gap-1 px-2 text-sm">
          <div className="truncate font-medium">
            {user.display_name ?? user.email}
          </div>
          <div className="truncate text-muted-foreground text-xs">
            {user.email}
          </div>
        </div>

        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={logout} type="button">
              <LogOutIcon aria-hidden="true" />
              {t("auth.logout")}
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        <SidebarSeparator />

        <div className="flex flex-wrap items-center gap-2 px-2 pt-1">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
