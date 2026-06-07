"use client";

import { Accordion as AccordionPrimitive } from "@base-ui/react/accordion";
import type React from "react";
import { cn } from "~/lib/utils";

export function Accordion({
  className,
  ...props
}: AccordionPrimitive.Root.Props): React.ReactElement {
  return (
    <AccordionPrimitive.Root
      className={cn("flex flex-col", className)}
      data-slot="accordion"
      {...props}
    />
  );
}

export function AccordionItem({
  className,
  ...props
}: AccordionPrimitive.Item.Props): React.ReactElement {
  return (
    <AccordionPrimitive.Item
      className={cn("border-b border-border", className)}
      data-slot="accordion-item"
      {...props}
    />
  );
}

export function AccordionTrigger({
  className,
  ...props
}: AccordionPrimitive.Trigger.Props): React.ReactElement {
  return (
    <AccordionPrimitive.Trigger
      className={cn(
        "flex min-w-0 flex-1 items-center text-left outline-none transition-colors hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background",
        className,
      )}
      data-slot="accordion-trigger"
      {...props}
    />
  );
}

export function AccordionPanel({
  className,
  ...props
}: AccordionPrimitive.Panel.Props): React.ReactElement {
  return (
    <AccordionPrimitive.Panel
      className={cn(
        "h-(--accordion-panel-height) overflow-hidden transition-[height] duration-200 data-ending-style:h-0 data-starting-style:h-0",
        className,
      )}
      data-slot="accordion-panel"
      {...props}
    />
  );
}

export { AccordionPrimitive };
