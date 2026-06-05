import { MoonIcon, SunIcon } from "lucide-react";
import { Button } from "~/components/ui/button";
import { useTheme } from "~/theme/provider";

export function ThemeToggle(): React.ReactElement {
  const { resolvedTheme, toggleTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <Button
      aria-label={isDark ? "切换到亮色主题" : "切换到暗色主题"}
      onClick={toggleTheme}
      size="icon"
      variant="outline"
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
    </Button>
  );
}
