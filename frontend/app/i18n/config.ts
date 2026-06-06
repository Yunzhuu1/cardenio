import i18next from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import enCommon from "~/i18n/locales/en/common.json";
import zhCNCommon from "~/i18n/locales/zh-CN/common.json";
import { defaultUiLanguage, uiLanguages } from "~/i18n/languages";

const resources = {
  "zh-CN": {
    common: zhCNCommon,
  },
  en: {
    common: enCommon,
  },
};

if (!i18next.isInitialized) {
  const chain = i18next.use(initReactI18next);

  if (typeof window !== "undefined") {
    chain.use(LanguageDetector);
  }

  void chain.init({
    defaultNS: "common",
    detection: {
      caches: ["localStorage"],
      lookupLocalStorage: "cardenio-ui-language",
      order: ["localStorage", "navigator"],
    },
    fallbackLng: defaultUiLanguage,
    interpolation: {
      escapeValue: false,
    },
    lng: typeof window === "undefined" ? defaultUiLanguage : undefined,
    ns: ["common"],
    resources,
    supportedLngs: [...uiLanguages],
  });
}

export { i18next };
