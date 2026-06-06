import { mergeProps } from "@base-ui/react/merge-props";
import { useRender } from "@base-ui/react/use-render";
import { createContext, useContext, useMemo, useState } from "react";
import { cn } from "~/lib/utils";

type SidebarContextValue = {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
};

const SidebarContext = createContext<SidebarContextValue | null>(null);

export function SidebarProvider({
  children,
  className,
  defaultOpen = true,
  ...props
}: React.ComponentProps<"div"> & {
  defaultOpen?: boolean;
}): React.ReactElement {
  const [open, setOpen] = useState(defaultOpen);
  const value = useMemo(
    () => ({
      open,
      setOpen,
      toggle: () => setOpen((current) => !current),
    }),
    [open],
  );

  return (
    <SidebarContext.Provider value={value}>
      <div
        data-sidebar-open={open}
        data-slot="sidebar-provider"
        className={cn(
          "flex min-h-dvh bg-background text-foreground",
          className,
        )}
        {...props}
      >
        {children}
      </div>
    </SidebarContext.Provider>
  );
}

export function useSidebar(): SidebarContextValue {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within SidebarProvider.");
  }
  return context;
}

type SidebarVariant = "sidebar" | "inset";

export function Sidebar({
  className,
  variant = "sidebar",
  ...props
}: React.ComponentProps<"aside"> & {
  variant?: SidebarVariant;
}): React.ReactElement {
  return (
    <aside
      data-variant={variant}
      data-slot="sidebar"
      className={cn(
        "peer hidden w-64 shrink-0 flex-col gap-2 border-r border-sidebar-border bg-background p-2 text-sidebar-foreground md:flex",
        variant === "inset" && "border-r-0",
        className,
      )}
      {...props}
    />
  );
}

export function SidebarHeader({
  className,
  ...props
}: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div
      data-slot="sidebar-header"
      className={cn("flex flex-col gap-2 p-2", className)}
      {...props}
    />
  );
}

export function SidebarContent({
  className,
  ...props
}: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div
      data-slot="sidebar-content"
      className={cn("flex min-h-0 flex-1 flex-col gap-2 p-2", className)}
      {...props}
    />
  );
}

export function SidebarFooter({
  className,
  ...props
}: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div
      data-slot="sidebar-footer"
      className={cn("flex flex-col gap-1 p-2", className)}
      {...props}
    />
  );
}

export function SidebarGroup({
  className,
  ...props
}: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div
      data-slot="sidebar-group"
      className={cn("flex flex-col gap-1", className)}
      {...props}
    />
  );
}

export function SidebarGroupAction({
  className,
  ...props
}: React.ComponentProps<"button">): React.ReactElement {
  return (
    <button
      data-slot="sidebar-group-action"
      type="button"
      className={cn(
        "inline-flex items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground",
        className,
      )}
      {...props}
    />
  );
}

export function SidebarGroupContent({
  className,
  ...props
}: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div data-slot="sidebar-group-content" className={className} {...props} />
  );
}

export function SidebarGroupLabel({
  className,
  ...props
}: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div
      data-slot="sidebar-group-label"
      className={cn(
        "px-2 text-xs font-medium uppercase tracking-wide text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

export function SidebarMenu({
  className,
  ...props
}: React.ComponentProps<"ul">): React.ReactElement {
  return (
    <ul
      data-slot="sidebar-menu"
      className={cn("flex flex-col gap-1", className)}
      {...props}
    />
  );
}

export function SidebarMenuItem({
  className,
  ...props
}: React.ComponentProps<"li">): React.ReactElement {
  return (
    <li
      data-slot="sidebar-menu-item"
      className={cn("min-w-0 list-none", className)}
      {...props}
    />
  );
}

export interface SidebarMenuButtonProps extends useRender.ComponentProps<"button"> {
  active?: boolean;
}

export function SidebarMenuButton({
  active = false,
  className,
  render,
  ...props
}: SidebarMenuButtonProps): React.ReactElement {
  const defaultProps = {
    className: cn(
      "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
      "aria-[current=page]:bg-sidebar-primary aria-[current=page]:text-sidebar-primary-foreground",
      active && "bg-sidebar-primary text-sidebar-primary-foreground",
      className,
    ),
    "data-active": active ? "" : undefined,
    "data-slot": "sidebar-menu-button",
  };

  return useRender({
    defaultTagName: "button",
    props: mergeProps<"button">(defaultProps, props),
    render,
  });
}

export function SidebarInset({
  className,
  ...props
}: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div
      data-slot="sidebar-inset"
      className={cn(
        "flex min-w-0 flex-1 flex-col bg-sidebar",
        "md:peer-data-[variant=inset]:m-2 md:peer-data-[variant=inset]:ml-0 md:peer-data-[variant=inset]:overflow-hidden md:peer-data-[variant=inset]:rounded-xl md:peer-data-[variant=inset]:shadow-sm",
        className,
      )}
      {...props}
    />
  );
}

export function SidebarRail({
  className,
  ...props
}: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div
      aria-hidden="true"
      data-slot="sidebar-rail"
      className={cn("hidden md:block", className)}
      {...props}
    />
  );
}

export function SidebarSeparator({
  className,
  ...props
}: React.ComponentProps<"div">): React.ReactElement {
  return (
    <div
      aria-hidden="true"
      data-slot="sidebar-separator"
      className={cn("h-px bg-sidebar-border", className)}
      {...props}
    />
  );
}

export function SidebarTrigger({
  className,
  onClick,
  ...props
}: React.ComponentProps<"button">): React.ReactElement {
  const { toggle } = useSidebar();

  return (
    <button
      data-slot="sidebar-trigger"
      type="button"
      className={cn(
        "inline-flex items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground",
        className,
      )}
      onClick={(event) => {
        onClick?.(event);
        if (!event.defaultPrevented) toggle();
      }}
      {...props}
    />
  );
}
