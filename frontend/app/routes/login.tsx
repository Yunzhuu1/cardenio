import { LogInIcon, PenLineIcon } from "lucide-react";
import type * as React from "react";
import { useState } from "react";
import { redirect, useNavigate, useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";
import { Alert, AlertDescription, AlertTitle } from "~/components/ui/alert";
import { Button } from "~/components/ui/button";
import { Field, FieldLabel } from "~/components/ui/field";
import { Input } from "~/components/ui/input";
import { api } from "~/lib/api/client";
import { ApiError } from "~/lib/api/types";
import { cn } from "~/lib/utils";

type AuthMode = "login" | "register";

export async function clientLoader() {
  if (!api.auth.getStoredToken()) return null;

  try {
    await api.auth.me();
    throw redirect("/");
  } catch (error) {
    if (error instanceof Response) throw error;
    api.auth.setStoredToken(null);
    return null;
  }
}

export default function Login(): React.ReactElement {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isRegister = mode === "register";

  async function submit(
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setError(null);
    setWorking(true);
    try {
      if (isRegister) {
        await api.auth.register({
          display_name: displayName.trim() || null,
          email,
          password,
        });
      } else {
        await api.auth.login({ email, password });
      }
      navigate(searchParams.get("redirectTo") || "/", { replace: true });
    } catch (submitError) {
      setError(authErrorMessage(submitError, t("auth.errorFallback")));
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="grid min-h-dvh place-items-center bg-background px-5 py-8">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-2 text-center">
          <div className="app-heading text-2xl">{t("app.name")}</div>
          <p className="text-muted-foreground text-sm">{t("auth.subtitle")}</p>
        </div>

        <div className="grid grid-cols-2 gap-1 rounded-lg bg-muted p-1">
          <AuthModeButton
            active={mode === "login"}
            icon={LogInIcon}
            label={t("auth.loginTab")}
            onClick={() => setMode("login")}
          />
          <AuthModeButton
            active={mode === "register"}
            icon={PenLineIcon}
            label={t("auth.registerTab")}
            onClick={() => setMode("register")}
          />
        </div>

        {error ? (
          <Alert variant="error">
            <AlertTitle>{t("auth.errorTitle")}</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <form className="space-y-4" onSubmit={submit}>
          {isRegister ? (
            <Field>
              <FieldLabel htmlFor="display-name">
                {t("auth.displayName")}
              </FieldLabel>
              <Input
                autoComplete="name"
                id="display-name"
                onChange={(event) => setDisplayName(event.target.value)}
                type="text"
                value={displayName}
              />
            </Field>
          ) : null}

          <Field>
            <FieldLabel htmlFor="email">{t("auth.email")}</FieldLabel>
            <Input
              autoComplete="email"
              id="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </Field>

          <Field>
            <FieldLabel htmlFor="password">{t("auth.password")}</FieldLabel>
            <Input
              autoComplete={isRegister ? "new-password" : "current-password"}
              id="password"
              minLength={isRegister ? 8 : undefined}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </Field>

          <Button className="w-full" loading={working} type="submit">
            {isRegister ? t("auth.registerSubmit") : t("auth.loginSubmit")}
          </Button>
        </form>
      </div>
    </main>
  );
}

function AuthModeButton({
  active,
  icon: Icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: React.ComponentType<{ "aria-hidden"?: boolean; className?: string }>;
  label: string;
  onClick: () => void;
}): React.ReactElement {
  return (
    <button
      className={cn(
        "inline-flex h-8 items-center justify-center gap-2 rounded-md px-3 text-sm transition-colors",
        active
          ? "bg-background text-foreground shadow-xs"
          : "text-muted-foreground hover:text-foreground",
      )}
      onClick={onClick}
      type="button"
    >
      <Icon aria-hidden className="size-4" />
      {label}
    </button>
  );
}

function authErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}
