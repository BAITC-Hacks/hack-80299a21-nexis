import type { ApiLanguage, Language } from './types';

/** Keep the existing KZ button label while using the ISO language code at the API boundary. */
export function apiLanguage(language: Language): ApiLanguage { return language === 'kz' ? 'kk' : language; }
export function storedLanguage(value: unknown): Language {
  return value === 'kk' || value === 'kz' ? 'kz' : value === 'en' ? 'en' : 'ru';
}
type Translation = readonly [string, string, string];
function translated(values: Translation, language: Language): string { return values[language === 'kz' ? 1 : language === 'en' ? 2 : 0]; }

const errors: Record<string, Translation> = {
  network_error: ['Не удалось подключиться к консультанту. Проверьте соединение.', 'Кеңесшіге қосылу мүмкін болмады. Байланысты тексеріңіз.', 'Unable to connect to the assistant. Check your connection.'],
  request_timeout: ['Ответ задерживается. Проверьте корзину перед повторным подтверждением.', 'Жауап кешігуде. Қайта растамас бұрын себетті тексеріңіз.', 'The response timed out. Check your cart before confirming again.'],
  request_error: ['Не удалось выполнить запрос. Повторите позже.', 'Сұрауды орындау мүмкін болмады. Кейінірек қайталаңыз.', 'The request could not be completed. Please try again later.'],
  validation_error: ['Проверьте запрос: количество должно быть целым, сообщение — не длиннее 4000 символов.', 'Сұрауды тексеріңіз: саны бүтін болуы, хабарлама 4000 таңбадан аспауы керек.', 'Check your request: quantity must be a whole number and messages must be at most 4,000 characters.'],
  rate_limited: ['Слишком много запросов. Повторите через {seconds} сек.', 'Сұраулар тым көп. {seconds} секундтан кейін қайталаңыз.', 'Too many requests. Try again in {seconds} seconds.'],
  session_failed: ['Не удалось открыть сессию консультанта.', 'Кеңесші сеансын ашу мүмкін болмады.', 'Unable to start an assistant session.'],
  session_expired: ['Сессия истекла. Открыта новая корзина. Повторите запрос и подтвердите товар заново.', 'Сеанс аяқталды. Жаңа себет ашылды. Сұрауды қайталап, тауарды қайта растаңыз.', 'Your session expired. A new cart is open. Repeat your request and confirm the item again.'],
  invalid_session: ['Сессия истекла. Обновите страницу и повторите запрос.', 'Сеанс аяқталды. Бетті жаңартып, сұрауды қайталаңыз.', 'Your session expired. Refresh the page and try again.'],
  invalid_quantity: ['Укажите допустимое целое количество.', 'Рұқсат етілген бүтін сан енгізіңіз.', 'Enter a valid whole-number quantity.'],
  catalog_unavailable: ['Не удалось проверить цену и остаток. Корзина не изменена.', 'Баға мен қалдықты тексеру мүмкін болмады. Себет өзгерген жоқ.', 'Price and stock could not be verified. Your cart was not changed.'],
  price_unavailable: ['Цену нужно уточнить у менеджера.', 'Бағаны менеджерден нақтылау керек.', 'Please confirm the price with a manager.'],
  insufficient_stock: ['Запрошенное количество превышает доступный остаток. Проверьте товар заново.', 'Сұралған сан қолжетімді қалдықтан артық. Тауарды қайта тексеріңіз.', 'The requested quantity exceeds available stock. Check the product again.'],
  packaging_mismatch: ['Количество не соответствует минимальной партии или кратности упаковки.', 'Саны ең аз партияға немесе қаптама еселігіне сәйкес келмейді.', 'The quantity does not meet the minimum order or package multiple.'],
  invalid_offer: ['Предложение истекло или уже использовано. Проверьте товар заново.', 'Ұсыныстың мерзімі өткен немесе қолданылған. Тауарды қайта тексеріңіз.', 'The offer expired or was already used. Check the product again.'],
  offer_mismatch: ['Товар или количество отличаются от предложения. Получите новое предложение.', 'Тауар немесе саны ұсынысқа сәйкес келмейді. Жаңа ұсыныс алыңыз.', 'The product or quantity differs from the offer. Request a new offer.'],
  cart_item_not_found: ['Товара нет в корзине. Обновите корзину.', 'Тауар себетте жоқ. Себетті жаңартыңыз.', 'The item is no longer in your cart. Refresh the cart.'],
  quantity_unchanged: ['Это количество уже установлено.', 'Бұл сан бұрыннан орнатылған.', 'This quantity is already set.'],
  confirmation_required: ['Подтвердите показанное предложение.', 'Көрсетілген ұсынысты растаңыз.', 'Please confirm the displayed offer.'],
  cart_changed: ['Корзина изменилась. Обновите её и подтвердите новое предложение.', 'Себет өзгерді. Оны жаңартып, жаңа ұсынысты растаңыз.', 'Your cart changed. Refresh it and confirm a new offer.'],
  price_changed: ['Цена изменилась. Получите новое предложение и подтвердите его.', 'Баға өзгерді. Жаңа ұсыныс алып, оны растаңыз.', 'The price changed. Request and confirm a new offer.'],
  unsupported_file: ['Поддерживаются PDF, TXT, DOCX, XLSX, XLS, JPEG, PNG и WEBP. Файл DOC сохраните как DOCX.', 'PDF, TXT, DOCX, XLSX, XLS, JPEG, PNG және WEBP қолданылады. DOC файлын DOCX ретінде сақтаңыз.', 'Supported formats: PDF, TXT, DOCX, XLSX, XLS, JPEG, PNG and WEBP. Convert DOC files to DOCX.'],
  empty_file: ['Файл пуст. Выберите файл с содержимым.', 'Файл бос. Мазмұны бар файлды таңдаңыз.', 'The file is empty. Choose a file with content.'],
  file_too_large: ['Размер файла превышает лимит. Выберите файл до 15 МБ.', 'Файл көлемі шектен асады. 15 МБ-қа дейінгі файлды таңдаңыз.', 'The file is too large. Choose a file of up to 15 MB.'],
  file_signature_mismatch: ['Содержимое файла не соответствует формату. Сохраните файл заново.', 'Файл мазмұны пішіміне сәйкес келмейді. Файлды қайта сақтаңыз.', 'The file content does not match its format. Save the file again.'],
  encrypted_document: ['Файлы с паролем не поддерживаются. Отправьте незашифрованную копию.', 'Құпиясөзбен қорғалған файлдар қолдау таппайды. Қорғалмаған көшірмесін жіберіңіз.', 'Password-protected files are unsupported. Upload an unencrypted copy.'],
  ocr_unavailable: ['Распознавание изображений недоступно. Пришлите текстовую спецификацию.', 'Суреттен мәтін тану қолжетімсіз. Мәтіндік спецификация жіберіңіз.', 'Image recognition is unavailable. Upload a text specification.'],
  ocr_timeout: ['Распознавание заняло слишком много времени. Отправьте меньший фрагмент.', 'Мәтін тану тым ұзаққа созылды. Кішірек бөлігін жіберіңіз.', 'Recognition timed out. Upload a smaller section.'],
  document_too_large: ['Документ превышает лимит обработки. Разделите его на меньшие файлы.', 'Құжат өңдеу шегінен асады. Оны кішірек файлдарға бөліңіз.', 'The document exceeds processing limits. Split it into smaller files.'],
  invalid_text_encoding: ['Сохраните текстовый файл в кодировке UTF-8.', 'Мәтіндік файлды UTF-8 кодтамасында сақтаңыз.', 'Save the text file using UTF-8 encoding.'],
  invalid_table_row: ['Проверьте разделители и кавычки в строках таблицы.', 'Кесте жолдарындағы бөлгіштер мен тырнақшаларды тексеріңіз.', 'Check the delimiters and quotation marks in the table rows.'],
  unreadable_file: ['Не удалось прочитать файл. Попробуйте сохранить его заново.', 'Файлды оқу мүмкін болмады. Оны қайта сақтап көріңіз.', 'The file could not be read. Try saving it again.'],
  no_text: ['Читаемый текст не найден. Нужны отчётливые маркировка и артикул.', 'Оқылатын мәтін табылмады. Анық таңбалау мен артикул қажет.', 'No readable text was found. Use a clear image of the markings and article number.'],
  no_product_rows: ['В файле не найдены строки спецификации.', 'Файлда спецификация жолдары табылмады.', 'No specification rows were found in the file.'],
};
const errorAliases: Record<string, string> = {
  ocr_languages_missing: 'ocr_unavailable', archive_too_large: 'document_too_large', too_many_pages: 'document_too_large',
  too_many_scans: 'document_too_large', image_too_large: 'document_too_large', text_too_large: 'document_too_large',
  table_too_large: 'document_too_large', too_many_rows: 'document_too_large',
};
export function localizedError(code: string, language: Language, params: Record<string, unknown> = {}): string {
  return translated(errors[errorAliases[code] || code] || errors.request_error, language)
    .replace(/\{(\w+)\}/g, (_, key: string) => String(params[key] ?? (key === 'seconds' ? '60' : '—')));
}

const specLabels: Record<string, Translation> = {
  OBYEM: ['Тип изделия', 'Өнім түрі', 'Product type'],
  KOLICHESTVO_POLYUSOV: ['Число полюсов', 'Полюстер саны', 'Number of poles'],
  NOMINALNYY_TOK: ['Номинальный ток', 'Номиналды ток', 'Rated current'],
  NOMINALNOE_NAPRYAZHENIE: ['Напряжение', 'Кернеу', 'Voltage'],
  NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST: ['Отключающая способность', 'Ажырату қабілеті', 'Breaking capacity'],
  TIP_USTANOVKI: ['Монтаж', 'Орнату', 'Mounting'], TORGOVAYA_MARKA: ['Марка', 'Бренд', 'Brand'],
  SECHENIE: ['Сечение', 'Қима', 'Cross section'], KOLICHESTVO_ZHIL: ['Число жил', 'Талсым саны', 'Number of conductors'],
  KHARAKTERISTIKA_SRABATYVANIYA: ['Характеристика срабатывания', 'Іске қосылу сипаттамасы', 'Trip characteristic'],
  NOMINALNYY_OTKLYUCHAYUSHCHIY_DIFFERENTSIALNYY_TOK: ['Дифференциальный ток', 'Дифференциалды ток', 'Residual current'],
};
export function specificationLabel(key: string | undefined, original: string, language: Language): string {
  return key && specLabels[key] ? translated(specLabels[key], language) : original;
}
export function productFallback(language: Language): string { return translated(['Товар ekt.kz', 'ekt.kz тауары', 'ekt.kz product'], language); }
export function unitFallback(language: Language): string { return translated(['шт.', 'дана', 'pcs'], language); }
