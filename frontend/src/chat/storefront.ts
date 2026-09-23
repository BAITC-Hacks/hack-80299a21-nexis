import type { Language } from './types';

// The surrounding storefront is illustrative; its stock and price labels never authorize API cart writes.
const ru = {
  pageTitle: 'ekt.kz — ИИ-консультант', city: 'Астана', account: 'Личный кабинет', business: 'Для бизнеса', buyers: 'Покупателям',
  request: 'Оставить заявку', contacts: 'Контакты ekt.kz', catalog: 'Каталог', search: 'Поиск по каталогу', compare: 'Сравнить', favorites: 'Избранное',
  home: 'Главная', catalogTitle: 'Каталог электротехнической продукции', category: 'Электротехническая продукция',
  heroTitle: 'Энергия решений', heroAccent: 'для вашего проекта', heroCopy: 'Кабель, автоматика, освещение и оборудование с подбором под вашу задачу.',
  searchQuestion: 'Что вы ищете?', find: 'Найти', brands: 'Проверенные бренды', warehouses: 'Склады по Казахстану',
  power: 'Надёжное', powerAccent: 'электроснабжение', quick: 'Быстрый доступ', popular: 'Популярные категории', all: 'Весь каталог',
  cables: 'Кабель и провод', automation: 'Автоматика', lighting: 'Освещение', switchgear: 'Щитовое оборудование',
  cableCount: '1 240 товаров', automationCount: '860 товаров', lightingCount: '532 товара', switchgearCount: '294 товара',
  popularCatalog: 'Популярное в каталоге', frequent: 'Часто выбирают', demo: 'Демонстрационная витрина',
  illustrativeStock: 'Пример наличия', pricePrefix: 'от', meter: 'м', footer: 'Электротехническая продукция для проектов любого масштаба',
  illustrative: 'Цены, остатки и количество товаров на фоне — иллюстративные', sections: 'Разделы магазина', selection: 'Подборка товаров',
};
const kz: typeof ru = {
  pageTitle: 'ekt.kz — ЖИ кеңесшісі', city: 'Астана', account: 'Жеке кабинет', business: 'Бизнеске', buyers: 'Сатып алушыларға',
  request: 'Өтінім қалдыру', contacts: 'ekt.kz байланыстары', catalog: 'Каталог', search: 'Каталогтан іздеу', compare: 'Салыстыру', favorites: 'Таңдаулылар',
  home: 'Басты бет', catalogTitle: 'Электротехникалық өнімдер каталогы', category: 'Электротехникалық өнімдер',
  heroTitle: 'Шешімдер қуаты', heroAccent: 'сіздің жобаңыз үшін', heroCopy: 'Міндетіңізге сай кабель, автоматика, жарықтандыру және жабдық таңдау.',
  searchQuestion: 'Не іздеп жүрсіз?', find: 'Іздеу', brands: 'Сенімді брендтер', warehouses: 'Қазақстан бойынша қоймалар',
  power: 'Сенімді', powerAccent: 'электрмен жабдықтау', quick: 'Жылдам қол жеткізу', popular: 'Танымал санаттар', all: 'Барлық каталог',
  cables: 'Кабель және сым', automation: 'Автоматика', lighting: 'Жарықтандыру', switchgear: 'Қалқан жабдықтары',
  cableCount: '1 240 тауар', automationCount: '860 тауар', lightingCount: '532 тауар', switchgearCount: '294 тауар',
  popularCatalog: 'Каталогта танымал', frequent: 'Жиі таңдалады', demo: 'Демонстрациялық сөре',
  illustrativeStock: 'Қалдық мысалы', pricePrefix: 'бастап', meter: 'м', footer: 'Кез келген ауқымдағы жобаларға арналған электротехникалық өнімдер',
  illustrative: 'Фондағы бағалар, қалдықтар мен тауар саны — мысалдар', sections: 'Дүкен бөлімдері', selection: 'Тауарлар топтамасы',
};
const en: typeof ru = {
  pageTitle: 'ekt.kz — AI assistant', city: 'Astana', account: 'My account', business: 'For businesses', buyers: 'For buyers',
  request: 'Send a request', contacts: 'ekt.kz contacts', catalog: 'Catalog', search: 'Search the catalog', compare: 'Compare', favorites: 'Favorites',
  home: 'Home', catalogTitle: 'Electrical product catalog', category: 'Electrical products',
  heroTitle: 'Powering solutions', heroAccent: 'for your project', heroCopy: 'Cables, circuit protection, lighting and equipment selected for your needs.',
  searchQuestion: 'What are you looking for?', find: 'Search', brands: 'Trusted brands', warehouses: 'Warehouses across Kazakhstan',
  power: 'Reliable', powerAccent: 'power supply', quick: 'Quick access', popular: 'Popular categories', all: 'Full catalog',
  cables: 'Cables and wires', automation: 'Circuit protection', lighting: 'Lighting', switchgear: 'Switchgear',
  cableCount: '1,240 products', automationCount: '860 products', lightingCount: '532 products', switchgearCount: '294 products',
  popularCatalog: 'Popular in the catalog', frequent: 'Frequently selected', demo: 'Illustrative storefront',
  illustrativeStock: 'Sample stock', pricePrefix: 'from', meter: 'm', footer: 'Electrical products for projects of any scale',
  illustrative: 'Background prices, stock and product counts are illustrative', sections: 'Store sections', selection: 'Product selection',
};
export const storefrontCopy = { ru, kz, en };
export function applyStorefrontLanguage(language: Language) {
  const labels = storefrontCopy[language];
  document.title = labels.pageTitle;
  document.querySelectorAll<HTMLElement>('[data-store-copy]').forEach((element) => {
    const key = element.dataset.storeCopy as keyof typeof labels;
    if (key in labels) element.textContent = labels[key];
  });
  document.querySelectorAll<HTMLElement>('[data-store-label]').forEach((element) => {
    const key = element.dataset.storeLabel as keyof typeof labels;
    if (key in labels) element.setAttribute('aria-label', labels[key]);
  });
}
