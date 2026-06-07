import { PlusIcon, XIcon } from "lucide-react";
import type * as React from "react";
import { useState } from "react";
import { Badge } from "~/components/ui/badge";
import { Button } from "~/components/ui/button";
import { Field, FieldDescription, FieldLabel } from "~/components/ui/field";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "~/components/ui/input-group";

export type StringListEditorProps = {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  description?: string;
  inputType?: React.HTMLInputTypeAttribute;
  reserveValueSpace?: boolean;
};

export function StringListEditor({
  label,
  values,
  onChange,
  placeholder,
  description,
  inputType = "text",
  reserveValueSpace = true,
}: StringListEditorProps): React.ReactElement {
  const [draft, setDraft] = useState("");

  function addValue(): void {
    const value = draft.trim();
    if (!value || values.includes(value)) {
      setDraft("");
      return;
    }
    onChange([...values, value]);
    setDraft("");
  }

  function removeValue(value: string): void {
    onChange(values.filter((item) => item !== value));
  }

  return (
    <Field className="w-full">
      <FieldLabel>{label}</FieldLabel>
      {description ? <FieldDescription>{description}</FieldDescription> : null}
      <InputGroup>
        <InputGroupInput
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addValue();
            }
          }}
          placeholder={placeholder}
          type={inputType}
          value={draft}
        />
        <InputGroupAddon align="inline-end">
          <Button
            aria-label={label}
            disabled={!draft.trim()}
            onClick={addValue}
            size="icon-xs"
            variant="ghost"
          >
            <PlusIcon aria-hidden />
          </Button>
        </InputGroupAddon>
      </InputGroup>
      {reserveValueSpace || values.length > 0 ? (
        <div className="flex min-h-6 flex-wrap gap-1.5">
          {values.map((value) => (
            <Badge key={value} size="lg" variant="secondary">
              <span className="max-w-64 truncate">{value}</span>
              <button
                aria-label={`${label}: ${value}`}
                className="rounded-sm outline-none hover:text-destructive focus-visible:ring-2 focus-visible:ring-ring"
                onClick={() => removeValue(value)}
                type="button"
              >
                <XIcon aria-hidden className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      ) : null}
    </Field>
  );
}
