export const uiLanguages = ["zh-CN", "en"] as const;

export type UiLanguage = (typeof uiLanguages)[number];
export type SourceLanguage = "zh-CN" | "en" | "mixed" | "unknown";
export type OutputLanguage = "zh-CN" | "en";

export const defaultUiLanguage: UiLanguage = "zh-CN";

export const sourceLanguageOptions: SourceLanguage[] = [
  "zh-CN",
  "en",
  "mixed",
  "unknown",
];

export const outputLanguageOptions: OutputLanguage[] = ["zh-CN", "en"];

// UI language controls interface copy only. Source and output languages are
// future data fields for imported novels and generated scripts.
