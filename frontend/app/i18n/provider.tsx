import { useEffect } from "react";
import { I18nextProvider, useTranslation } from "react-i18next";
import { i18next } from "~/i18n/config";

function DocumentLanguageSync(): null {
  const { i18n } = useTranslation();

  useEffect(() => {
    document.documentElement.lang = i18n.resolvedLanguage || "zh-CN";
  }, [i18n.resolvedLanguage]);

  return null;
}

export function I18nProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <I18nextProvider i18n={i18next}>
      <DocumentLanguageSync />
      {children}
    </I18nextProvider>
  );
}
