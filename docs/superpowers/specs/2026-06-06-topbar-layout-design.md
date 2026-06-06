# Topbar Layout Design

## Goal

Adjust the app shell so the topbar owns global page context and sidebar visibility, while the sidebar footer owns secondary global preferences.

## Scope

- Add a topbar button that toggles the sidebar.
- Hide the sidebar completely when collapsed on desktop.
- Reuse the same sidebar toggle state for mobile.
- Move language and theme controls from the topbar to the sidebar footer.
- Move page titles into the topbar, immediately to the right of the sidebar toggle.
- Remove page-level description text from existing page headers.

This change does not add dependencies, change runtime commands, or change backend behavior.

## Architecture

The existing `SidebarProvider` in `frontend/app/components/ui/sidebar.tsx` remains the source of truth for sidebar visibility. `AppShell` renders the topbar controls and route outlet. `AppSidebar` renders navigation plus footer actions. Route-level layouts provide the active page title through a small outlet context instead of duplicating topbar markup in every page.

## Component Responsibilities

- `frontend/app/components/ui/sidebar.tsx`: expose the existing sidebar open state in DOM classes so the sidebar can be fully hidden when closed.
- `frontend/app/routes/app-shell.tsx`: render the sidebar toggle button and current page title in the topbar.
- `frontend/app/components/app-sidebar.tsx`: move language and theme controls into the footer below the new-project action.
- `frontend/app/routes/overview.tsx`: provide the overview title to the shell and remove the local description copy.
- `frontend/app/routes/project-layout.tsx`: provide the project title to the shell and keep project settings/stage navigation in the project layout.

## Interaction Details

The topbar toggle button uses an icon-only control with an accessible label. When the sidebar is open, the button label communicates that it collapses the sidebar; when closed, it communicates that it expands the sidebar. Desktop collapse removes the sidebar from layout instead of shrinking it to a rail. Mobile keeps the same state path so the topbar control has one behavior across viewport sizes.

## Verification

Run:

```bash
pnpm --dir frontend format:check
pnpm --dir frontend lint
pnpm --dir frontend build
```

Manual verification should confirm that the sidebar can be hidden and shown, topbar titles update on overview and project pages, language/theme controls remain available in the sidebar footer, and page header descriptions are removed.
