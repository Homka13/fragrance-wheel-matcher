# Cloudflare Worker: Fragrance Wheel Matcher & Automated Scraper

Хмарний безсерверний воркер на базі **Cloudflare Workers (Edge V8)**, що поєднує:
1. **Edge REST API**: Швидка віддача каталогу, топології Колеса ароматів та ольфакторний підбір за лічені мілісекунди.
2. **Cloudflare D1**: Безсерверна реляційна база даних (SQLite на Edge) для зберігання парфумів, пірамід та родин.
3. **Cloudflare Browser Rendering (@cloudflare/puppeteer)**: Безголовий Chromium у хмарі Cloudflare для обходу динамічного JS та Cloudflare-захисту сайтів.
4. **Cron Triggers**: Автоматичний фоновий збір даних та оновлення бази за розкладом щопонеділка.

---

## 🛠️ Покрокова інструкція: що треба зробити ручками

Всі ці команди виконуються в папці `cloudflare_worker/`.

### Крок 1. Авторизація у Cloudflare CLI
Якщо ви ще не заходили в акаунт Cloudflare через термінал:
```bash
cd cloudflare_worker
npx wrangler login
```
*У браузері відкриється сторінка підтвердження доступу до вашого Cloudflare акаунту. Натисніть **Allow**.*

---

### Крок 2. Створення безсерверної бази даних Cloudflare D1
Виконайте команду створення бази даних:
```bash
npx wrangler d1 create fragrance-wheel-db
```
У терміналі ви побачите вивід схожий на:
```text
[[d1_databases]]
binding = "DB"
database_name = "fragrance-wheel-db"
database_id = "xxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

---

### Крок 3. Вставка `database_id` у `wrangler.toml`
Відкрийте файл `wrangler.toml` і замініть значення `database_id`:
```toml
[[d1_databases]]
binding = "DB"
database_name = "fragrance-wheel-db"
database_id = "ВАШ_DATABASE_ID_З_КРОКУ_2"
```

---

### Крок 4. Застосування схеми таблиць до хмарної D1
Створюємо таблиці `wheel_families`, `wheel_subfamilies`, `brands`, `fragrances`:
```bash
npx wrangler d1 execute fragrance-wheel-db --remote --file=./schema.sql
```

---

### Крок 5. Початкове наповнення даними (Seed)
Завантажуємо базовий каталог парфумів та структуру родин Колеса:
```bash
npx wrangler d1 execute fragrance-wheel-db --remote --file=./seed_d1.sql
```

---

### Крок 6. Публікація воркера на Cloudflare
Розгортаємо наш Worker у глобальну мережу Cloudflare:
```bash
npx wrangler deploy
```
Після завершення ви отримаєте публічний URL, наприклад:
`https://fragrance-wheel-worker.<your-account>.workers.dev`

---

## 💻 Локальна розробка та тестування (без завантаження у хмару)

Якщо хочете протестувати все локально на комп'ютері:
```bash
# 1. Застосувати схему локально
npx wrangler d1 execute fragrance-wheel-db --local --file=./schema.sql

# 2. Залити тестові дані локально
npx wrangler d1 execute fragrance-wheel-db --local --file=./seed_d1.sql

# 3. Запустити локальний сервер
npx wrangler dev
```

---

## 📡 Доступні ендпоінти API

| Метод | Ендпоінт | Опис |
|---|---|---|
| `GET` | `/api/wheel` | Повертає 4 родини та 14 підгруп Колеса ароматів з кольорами та нотами |
| `GET` | `/api/fragrances` | Отримання каталогу парфумів (фільтри: `?query=`, `?subfamily=`, `?gender=`) |
| `POST` | `/api/match` | Розрахунок спорідненості: `{ "source_subfamily_id": "woody_pure" }` |
| `POST` | `/api/trigger-scrape` | Ручний запуск парсера з оновленням D1: `?token=fragrance_wheel_secure_token` |

---

## ⏰ Фоновий розклад парсингу (Cron Trigger)

В `wrangler.toml` налаштовано автоматичний запуск:
```toml
[triggers]
crons = ["0 3 * * 1"] # Щопонеділка о 03:00 UTC
```
Під час спрацьовування воркер підключається до Cloudflare Browser Rendering, завантажує сторінки товарів, витягує ноти, класифікує за методом Жана Карля та зберігає в D1 без будь-якого втручання людини.
