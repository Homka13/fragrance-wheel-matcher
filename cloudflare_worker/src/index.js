/**
 * index.js
 * Головний обробник Cloudflare Worker для Fragrance Wheel Matcher:
 * - Edge REST API (CORS, D1 SQLite, Wheel Matcher)
 * - Scheduled Cron Handler (Щотижневе фонове оновлення бази даних через @cloudflare/puppeteer)
 */

import { FAMILIES, SUBFAMILIES, SUBFAMILIES_BY_ID, matchFragrancesOnEdge } from './wheel.js';
import { crawlBrocard, saveProductsToD1 } from './crawler.js';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      ...CORS_HEADERS
    }
  });
}

function parseNotesArray(field) {
  if (!field) return [];
  if (Array.isArray(field)) return field;
  try {
    return JSON.parse(field);
  } catch (_) {
    return [];
  }
}

export default {
  /**
   * Обробка вхідних HTTP-запитів Edge API.
   */
  async fetch(request, env, ctx) {
    // Обробка OPTIONS (CORS preflight)
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, '') || '/';

    try {
      // 1. Інформація про API / Health Check
      if (path === '' || path === '/' || path === '/api') {
        return jsonResponse({
          status: 'ok',
          service: 'Fragrance Wheel Matcher Edge API',
          runtime: 'Cloudflare Workers (V8 Edge)',
          database: 'Cloudflare D1 (Edge SQLite)',
          endpoints: [
            { path: '/api/wheel', method: 'GET', description: 'Топологія Колеса Майкла Едвардса (14 підгруп)' },
            { path: '/api/fragrances', method: 'GET', description: 'Каталог парфумів з D1 (підтримує ?query=, ?subfamily=, ?family=)' },
            { path: '/api/match', method: 'POST', description: 'Ольфакторний підбір аналогів та комплементарних ароматів' },
            { path: '/api/trigger-scrape', method: 'POST', description: 'Ручний запуск парсера з оновленням D1 (потребує Bearer токен)' }
          ]
        });
      }

      // 2. Колесо ароматів (топологія та класифікація)
      if (path === '/api/wheel' && request.method === 'GET') {
        return jsonResponse({
          families: FAMILIES,
          subfamilies: SUBFAMILIES
        });
      }

      // 3. Каталог парфумів з D1
      if (path === '/api/fragrances' && request.method === 'GET') {
        if (!env.DB) {
          return jsonResponse({ error: 'Database D1 binding "DB" is not configured in wrangler.toml' }, 500);
        }

        const query = url.searchParams.get('query') || '';
        const subfamily = url.searchParams.get('subfamily') || '';
        const family = url.searchParams.get('family') || '';
        const gender = url.searchParams.get('gender') || '';
        const limit = Math.min(parseInt(url.searchParams.get('limit') || '200', 10), 500);

        let sql = `SELECT * FROM fragrances WHERE 1=1`;
        const params = [];

        if (subfamily) {
          sql += ` AND primary_subfamily_id = ?`;
          params.push(subfamily);
        }
        if (family) {
          sql += ` AND family_code = ?`;
          params.push(family);
        }
        if (gender) {
          sql += ` AND gender = ?`;
          params.push(gender);
        }
        if (query) {
          sql += ` AND (name LIKE ? OR brand_name LIKE ? OR product_sku LIKE ?)`;
          const term = `%${query}%`;
          params.push(term, term, term);
        }

        sql += ` ORDER BY brand_name ASC, name ASC LIMIT ?`;
        params.push(limit);

        const stmt = env.DB.prepare(sql).bind(...params);
        const { results } = await stmt.all();

        const formatted = (results || []).map(f => ({
          ...f,
          top_notes: parseNotesArray(f.top_notes),
          heart_notes: parseNotesArray(f.heart_notes),
          base_notes: parseNotesArray(f.base_notes)
        }));

        return jsonResponse({
          count: formatted.length,
          fragrances: formatted
        });
      }

      // 4. Ольфакторний підбір ароматів (Exact, Adjacent, Complementary)
      if (path === '/api/match' && request.method === 'POST') {
        if (!env.DB) {
          return jsonResponse({ error: 'Database D1 binding "DB" is not configured' }, 500);
        }

        const body = await request.json().catch(() => ({}));
        const sourceSubfamilyId = body.source_subfamily_id || null;
        const referenceFragranceId = body.reference_fragrance_id || null;

        if (!sourceSubfamilyId && !referenceFragranceId) {
          return jsonResponse({
            error: 'Необхідно вказати "source_subfamily_id" або "reference_fragrance_id"'
          }, 400);
        }

        // Завантажуємо всі доступні парфуми для швидкого метчингу в оперативній пам'яті Edge V8
        const { results: allFragrances } = await env.DB.prepare(
          'SELECT * FROM fragrances'
        ).all();

        const matchResults = matchFragrancesOnEdge(
          allFragrances || [],
          sourceSubfamilyId,
          referenceFragranceId
        );

        return jsonResponse({
          source_subfamily_id: sourceSubfamilyId,
          reference_fragrance_id: referenceFragranceId,
          matches: matchResults
        });
      }

      // 5. Ручний запуск фонового скрапера з оновленням D1 (захищений ендпоінт)
      if ((path === '/api/trigger-scrape' || path === '/api/scrape') && (request.method === 'POST' || request.method === 'GET')) {
        const authHeader = request.headers.get('Authorization') || '';
        const queryToken = url.searchParams.get('token') || '';
        const expectedSecret = env.ADMIN_SECRET || 'fragrance_wheel_secure_token';

        const isAuthorized = authHeader === `Bearer ${expectedSecret}` || queryToken === expectedSecret;
        if (!isAuthorized) {
          return jsonResponse({
            error: 'Unauthorized: Надайте правильний Admin Secret у заголовку Authorization або в ?token='
          }, 401);
        }

        if (!env.DB) {
          return jsonResponse({ error: 'Database D1 binding "DB" is not configured' }, 500);
        }

        const maxProducts = parseInt(url.searchParams.get('max') || env.CRAWL_MAX_PRODUCTS || '15', 10);
        
        console.log(`[Scrape Trigger] Початок збору даних (макс ${maxProducts} товарів)...`);
        const scraped = await crawlBrocard(env, maxProducts);
        const savedCount = await saveProductsToD1(env.DB, scraped);

        return jsonResponse({
          success: true,
          message: `Успішно зібрано та синхронізовано з D1 ${savedCount} парфумів`,
          count: savedCount,
          products: scraped.map(p => ({
            id: p.id,
            name: p.name,
            brand: p.brand_name,
            subfamily: p.primary_subfamily_id,
            url: p.product_url
          }))
        });
      }

      // 404 для інших шляхів
      return jsonResponse({ error: 'Not Found', path }, 404);

    } catch (err) {
      console.error('Unhandled Worker Error:', err);
      return jsonResponse({
        error: 'Internal Server Error',
        message: err.message
      }, 500);
    }
  },

  /**
   * Фонове виконання за розкладом (Cron Trigger).
   * Автоматично запускається Cloudflare щопонеділка о 03:00 UTC.
   */
  async scheduled(event, env, ctx) {
    console.log(`[Scheduled Cron] Запуск регулярного парсингу каталогу: ${new Date().toISOString()}`);

    ctx.waitUntil((async () => {
      try {
        if (!env.DB) {
          console.error('[Scheduled Cron] D1 DB binding відсутній. Перевірте wrangler.toml');
          return;
        }

        const maxProducts = parseInt(env.CRAWL_MAX_PRODUCTS || '15', 10);
        const scraped = await crawlBrocard(env, maxProducts);
        const savedCount = await saveProductsToD1(env.DB, scraped);

        console.log(`[Scheduled Cron] Завершено успішно. Оновлено ${savedCount} записів у D1.`);
      } catch (cronErr) {
        console.error('[Scheduled Cron] Помилка виконання фонового завдання:', cronErr);
      }
    })());
  }
};
