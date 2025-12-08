/**
 * i18n - Internationalization System
 * Gère les traductions FR, EN, DE, ES, ZH
 * Utilise localStorage pour persister la langue
 */

class I18n {
  constructor() {
    this.translations = {};
    this.currentLanguage = localStorage.getItem('crbot_language') || 'en';
    this.supportedLanguages = ['fr', 'en', 'de', 'es', 'zh'];
  }

  /**
   * Charger les traductions depuis le fichier JSON
   */
  async loadTranslations() {
    try {
      const response = await fetch('/i18n/translations.json');
      this.translations = await response.json();
      console.log(`✅ i18n: Translations loaded. Current language: ${this.currentLanguage}`);
    } catch (error) {
      console.error('❌ i18n: Failed to load translations', error);
      this.translations = { en: {}, fr: {} };
    }
  }

  /**
   * Obtenir une traduction
   * Utilisation: i18n.t('dashboard.portfolio_value')
   */
  t(key, lang = null) {
    const language = lang || this.currentLanguage;
    const keys = key.split('.');
    let value = this.translations[language];

    for (const k of keys) {
      if (value && typeof value === 'object') {
        value = value[k];
      } else {
        // Fallback to English if key not found
        value = this.translations['en'];
        for (const k2 of keys) {
          if (value && typeof value === 'object') {
            value = value[k2];
          }
        }
        return value || key;
      }
    }

    return value || key;
  }

  /**
   * Définir la langue courante
   */
  setLanguage(lang) {
    if (this.supportedLanguages.includes(lang)) {
      this.currentLanguage = lang;
      localStorage.setItem('crbot_language', lang);
      console.log(`✅ i18n: Language changed to ${lang}`);
      // Émettre un événement pour notifier les pages
      window.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: lang } }));
      return true;
    }
    return false;
  }

  /**
   * Obtenir la langue courante
   */
  getLanguage() {
    return this.currentLanguage;
  }

  /**
   * Obtenir toutes les langues supportées
   */
  getSupportedLanguages() {
    return this.supportedLanguages;
  }

  /**
   * Traduire tout le DOM
   */
  translateDOM() {
    // Traduire tous les éléments avec data-i18n
    document.querySelectorAll('[data-i18n]').forEach(element => {
      const key = element.getAttribute('data-i18n');
      const translated = this.t(key);
      
      // Déterminer si c'est un attribut ou du contenu
      if (element.getAttribute('data-i18n-attr')) {
        const attr = element.getAttribute('data-i18n-attr');
        element.setAttribute(attr, translated);
      } else {
        element.textContent = translated;
      }
    });

    // Traduire les attributs placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
      const key = element.getAttribute('data-i18n-placeholder');
      element.placeholder = this.t(key);
    });

    // Traduire les attributs title
    document.querySelectorAll('[data-i18n-title]').forEach(element => {
      const key = element.getAttribute('data-i18n-title');
      element.title = this.t(key);
    });
  }

  /**
   * Format un nombre selon la langue
   */
  formatNumber(num, decimals = 2) {
    const options = {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    };
    return new Intl.NumberFormat(this.currentLanguage === 'fr' ? 'fr-FR' : 'en-US', options).format(num);
  }

  /**
   * Format une devise selon la langue
   */
  formatCurrency(num, currency = 'USD') {
    const options = {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    };
    return new Intl.NumberFormat(this.currentLanguage === 'fr' ? 'fr-FR' : 'en-US', options).format(num);
  }

  /**
   * Format une date selon la langue
   */
  formatDate(date, format = 'short') {
    if (typeof date === 'string') {
      date = new Date(date);
    }
    
    const options = format === 'short' 
      ? { year: 'numeric', month: '2-digit', day: '2-digit' }
      : { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    
    return new Intl.DateTimeFormat(this.currentLanguage === 'fr' ? 'fr-FR' : 'en-US', options).format(date);
  }
}

// Instance globale
const i18n = new I18n();

// Initialiser au chargement
document.addEventListener('DOMContentLoaded', async () => {
  await i18n.loadTranslations();
  i18n.translateDOM();
});

// Écouter les changements de langue
window.addEventListener('languageChanged', () => {
  i18n.translateDOM();
});
