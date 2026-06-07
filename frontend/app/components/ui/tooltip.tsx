"use client";

import { Tooltip as TooltipPrimitive } from "@base-ui/react/tooltip";
import type React from "react";
import { cn } from "~/lib/utils";

export const Tooltip: typeof TooltipPrimitive.Root = TooltipPrimitive.Root;

export const TooltipProvider: typeof TooltipPrimitive.Provider =
  TooltipPrimitive.Provider;

export const TooltipCreateHandle: typeof TooltipPrimitive.createHandle =
  TooltipPrimitive.createHandle;

export function TooltipTrigger(
  props: TooltipPrimitive.Trigger.Props,
): React.ReactElement {
  return <TooltipPrimitive.Trigger data-slot="tooltip-trigger" {...props} />;
}

export function TooltipPopup({
  children,
  className,
  side = "top",
  sideOffset = 6,
  align = "center",
  alignOffset,
  portalProps,
  ...props
}: TooltipPrimitive.Popup.Props & {
  side?: TooltipPrimitive.Positioner.Props["side"];
  sideOffset?: TooltipPrimitive.Positioner.Props["sideOffset"];
  align?: TooltipPrimitive.Positioner.Props["align"];
  alignOffset?: TooltipPrimitive.Positioner.Props["alignOffset"];
  portalProps?: TooltipPrimitive.Portal.Props;
}): React.ReactElement {
  return (
    <TooltipPrimitive.Portal {...portalProps}>
      <TooltipPrimitive.Positioner
        align={align}
        alignOffset={alignOffset}
        className="z-50"
        data-slot="tooltip-positioner"
        side={side}
        sideOffset={sideOffset}
      >
        <TooltipPrimitive.Popup
          className={cn(
            "max-w-64 rounded-md bg-popover px-2.5 py-1.5 text-popover-foreground text-xs shadow-lg/10 outline-none transition-[opacity,scale] duration-150 data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0",
            className,
          )}
          data-slot="tooltip-popup"
          {...props}
        >
          {children}
        </TooltipPrimitive.Popup>
      </TooltipPrimitive.Positioner>
    </TooltipPrimitive.Portal>
  );
}

export { TooltipPrimitive };
