import { LayoutGridIcon, PlusIcon } from "lucide-react";
import { NavLink } from "react-router";
import { useTranslation } from "react-i18next";
import type { ProjectSummary } from "~/lib/api/types";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "~/components/ui/sidebar";

export function AppSidebar({
  projects,
}: {
  projects: ProjectSummary[];
}): React.ReactElement {
  const { t } = useTranslation();
  const [brandLatin, brandCjk] = t("app.name").split(" ");

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-baseline gap-2 text-sidebar-foreground">
          <span className="[font-family:var(--font-brand-latin)] text-[1.75rem] font-light italic leading-none">
            {brandLatin}
          </span>
          {brandCjk && (
            <span className="[font-family:var(--font-brand-cjk)] text-base font-normal leading-none">
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
      </SidebarContent>
    </Sidebar>
  );
}
