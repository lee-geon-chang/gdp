import useBopStore from '../store/bopStore';
import translations from './translations';

export default function useTranslation() {
  const lang = useBopStore(state => state.selectedLanguage) || 'ko';

  const t = (key, params) => {
    let str = translations[lang]?.[key] || translations.ko[key] || key;
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        str = str.replace(`{${k}}`, v);
      });
    }
    return str;
  };

  return { t, lang };
}
