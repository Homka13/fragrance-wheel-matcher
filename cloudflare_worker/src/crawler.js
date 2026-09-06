/**
 * crawler.js
 * Хмарний браузерний парсер Brocard для Cloudflare Workers.
 * Використовує @cloudflare/puppeteer (Browser Rendering) для обходу Cloudflare / динамічного JS
 * та здійснює фонове оновлення бази даних Cloudflare D1.
 */

import puppeteer from '@cloudflare/puppeteer';
import { extractPyramidFromText, classifyPyramid } from './parser.js';

export const DEFAULT_TARGET_URLS = [
  "https://www.brocard.ua/ua/product/parfumovana-voda-lancome-la-vie-est-belle",
  "https://www.brocard.ua/ua/product/parfumovana-voda-lancome-idole",
  "https://www.brocard.ua/ua/product/parfumovana-voda-lancome-tresor",
  "https://www.brocard.ua/ua/product/parfumovana-voda-carolina-herrera-good-girl",
  "https://www.brocard.ua/ua/product/parfumovana-voda-carolina-herrera-very-good-girl",
  "https://www.brocard.ua/ua/product/tualetna-voda-carolina-herrera-bad-boy",
  "https://www.brocard.ua/ua/product/chanel-coco-mademoiselle",
  "https://www.brocard.ua/ua/product/chanel-bleu-de-chanel",
  "https://www.brocard.ua/ua/product/tom-ford-tobacco-vanille",
  "https://www.brocard.ua/ua/product/tom-ford-oud-wood",
  "https://www.brocard.ua/ua/product/tom-ford-lost-cherry",
  "https://www.brocard.ua/ua/product/yves-saint-laurent-black-opium",
  "https://www.brocard.ua/ua/product/yves-saint-laurent-libre",
  "https://www.brocard.ua/ua/product/dior-sauvage",
  "https://www.brocard.ua/ua/product/dior-fahrenheit",
  "https://www.brocard.ua/ua/product/giorgio-armani-acqua-di-gio",
  "https://www.brocard.ua/ua/product/maison-francis-kurkdjian-baccarat-rouge-540",
  "https://www.brocard.ua/ua/product/kilian-angels-share"
];

/**
 * Обробка сирих даних картки товару, витяг піраміди та ольфакторна класифікація.
 */
export function processProductData(raw, url) {
  const pyramid = extractPyramidFromText(raw.description || '');
  const classification = classifyPyramid(pyramid.top_notes, pyramid.heart_notes, pyramid.base_notes);

  let brandName = (raw.brand || '').trim();
  let cleanName = (raw.title || '').trim();

  if (brandName && cleanName.toLowerCase().includes(brandName.toLowerCase())) {
    cleanName = cleanName.replace(new RegExp(brandName, 'gi'), '').replace(/^[\s\-–—:]+|[\s\-–—:]+$/g, '').trim();
  }
  if (!brandName) brandName = 'Unknown';
  if (!cleanName) cleanName = raw.title || 'Fragrance';

  const brandId = brandName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'brand';
  const slugId = `${brandId}_${cleanName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')}`.slice(0, 80);

  let concentration = 'Eau de Parfum';
  const tLower = (raw.title || '').toLowerCase();
  if (tLower.includes('туалетна вода') || tLower.includes('edt')) {
    concentration = 'Eau de Toilette';
  } else if (tLower.includes('парфумована вода') || tLower.includes('edp')) {
    concentration = 'Eau de Parfum';
  } else if (tLower.includes('духи') || tLower.includes('extrait')) {
    concentration = 'Extrait de Parfum';
  } else if (tLower.includes('одеколон') || tLower.includes('edc')) {
    concentration = 'Eau de Cologne';
  }

  let gender = 'unisex';
  if (tLower.includes('для жінок') || (raw.gender && raw.gender === 'female')) {
    gender = 'female';
  } else if (tLower.includes('для чоловіків') || (raw.gender && raw.gender === 'male')) {
    gender = 'male';
  }

  return {
    id: slugId,
    brand_id: brandId,
    brand_name: brandName,
    name: cleanName,
    gender: gender,
    concentration: concentration,
    primary_subfamily_id: classification.primary_subfamily_id,
    family_code: classification.family_code,
    top_notes: JSON.stringify(pyramid.top_notes),
    heart_notes: JSON.stringify(pyramid.heart_notes),
    base_notes: JSON.stringify(pyramid.base_notes),
    price_uah: raw.price ? parseFloat(raw.price) : null,
    product_sku: raw.sku || slugId,
    product_url: url,
    image_url: raw.imageUrl || null
  };
}

/**
 * Парсер картки товару через звичайний fetch (fallback у випадку відсутності browser binding).
 */
async function scrapeProductViaFetch(url) {
  try {
    const res = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'uk-UA,uk;q=0.9,en;q=0.8'
      }
    });
    if (!res.ok) return null;
    const html = await res.text();

    const titleMatch = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i) || html.match(/<title>([\s\S]*?)<\/title>/i);
    const title = titleMatch ? titleMatch[1].replace(/<[^>]+>/g, '').trim() : '';

    const ogImgMatch = html.match(/<meta\s+property=["']og:image["']\s+content=["']([^"']+)["']/i);
    const img = ogImgMatch ? ogImgMatch[1] : null;

    const brandMatch = html.match(/class=["'][^"']*brand[^"']*["'][^>]*>([\s\S]*?)<\//i);
    const brand = brandMatch ? brandMatch[1].replace(/<[^>]+>/g, '').trim() : '';

    const cleanHtml = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
                          .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '');
    const cleanText = cleanHtml.replace(/<[^>]+>/g, ' ');

    return processProductData({
      title,
      brand,
      description: cleanText,
      price: null,
      sku: null,
      imageUrl: img
    }, url);
  } catch (e) {
    console.error(`Fetch fallback error for ${url}:`, e.message);
    return null;
  }
}

/**
 * Головна функція збору даних каталогу.
 */
export async function crawlBrocard(env, maxItems = 10) {
  const results = [];
  const targetUrls = [...DEFAULT_TARGET_URLS].slice(0, maxItems);

  if (env.MYBROWSER) {
    let browser = null;
    try {
      browser = await puppeteer.launch(env.MYBROWSER);
      const page = await browser.newPage();
      await page.setUserAgent(
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
      );
      await page.setViewport({ width: 1280, height: 800 });

      for (const url of targetUrls) {
        try {
          await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 25000 });
          await new Promise(r => setTimeout(r, 1200));

          const raw = await page.evaluate(() => {
            const getTxt = (sel) => {
              const el = document.querySelector(sel);
              return el ? el.textContent.trim() : '';
            };
            const title = getTxt('h1') || getTxt('.product-title') || document.title;
            const brand = getTxt('.brand') || getTxt('.product-brand') || getTxt('.vendor') || '';
            const desc = getTxt('.product-info__description') || getTxt('.description') || getTxt('.details') || document.body.innerText;
            
            const priceText = getTxt('.price-current') || getTxt('.price') || getTxt('.special-price') || '';
            const priceNum = priceText.replace(/[^\d]/g, '');

            const skuText = getTxt('.sku') || getTxt('.product-code') || '';
            
            let img = '';
            const imgEl = document.querySelector('.product-gallery img, .product-image img, meta[property="og:image"]');
            if (imgEl) {
              img = imgEl.tagName === 'META' ? imgEl.content : (imgEl.src || imgEl.getAttribute('data-src') || '');
            }

            return {
              title,
              brand,
              description: desc,
              price: priceNum ? parseFloat(priceNum) : null,
              sku: skuText || null,
              imageUrl: img
            };
          });

          if (raw && raw.title) {
            results.push(processProductData(raw, url));
          }
        } catch (pageErr) {
          console.warn(`Browser scrap failed for ${url}, trying fallback:`, pageErr.message);
          const fallbackItem = await scrapeProductViaFetch(url);
          if (fallbackItem) results.push(fallbackItem);
        }
      }
    } catch (browserErr) {
      console.error('Puppeteer launch error:', browserErr);
    } finally {
      if (browser) {
        try { await browser.close(); } catch (_) {}
      }
    }
  } else {
    // Якщо MYBROWSER не налаштований (локальне тестування тощо)
    for (const url of targetUrls) {
      const item = await scrapeProductViaFetch(url);
      if (item) results.push(item);
    }
  }

  return results;
}

/**
 * Запис та оновлення зібраних парфумів у базі даних Cloudflare D1.
 */
export async function saveProductsToD1(db, products) {
  if (!db || !products || products.length === 0) return 0;

  const brandStatements = [];
  const fragranceStatements = [];
  const uniqueBrands = new Map();

  for (const p of products) {
    if (!uniqueBrands.has(p.brand_id)) {
      uniqueBrands.set(p.brand_id, p.brand_name);
    }
  }

  for (const [brandId, brandName] of uniqueBrands.entries()) {
    brandStatements.push(
      db.prepare(`
        INSERT OR IGNORE INTO brands (id, name, country)
        VALUES (?, ?, 'Global')
      `).bind(brandId, brandName)
    );
  }

  for (const p of products) {
    fragranceStatements.push(
      db.prepare(`
        INSERT INTO fragrances (
          id, brand_id, brand_name, name, gender, concentration,
          primary_subfamily_id, family_code,
          top_notes, heart_notes, base_notes,
          price_uah, product_sku, product_url, image_url,
          updated_at
        ) VALUES (
          ?, ?, ?, ?, ?, ?,
          ?, ?,
          ?, ?, ?,
          ?, ?, ?, ?,
          CURRENT_TIMESTAMP
        )
        ON CONFLICT(id) DO UPDATE SET
          brand_name = excluded.brand_name,
          name = excluded.name,
          gender = excluded.gender,
          concentration = excluded.concentration,
          primary_subfamily_id = excluded.primary_subfamily_id,
          family_code = excluded.family_code,
          top_notes = excluded.top_notes,
          heart_notes = excluded.heart_notes,
          base_notes = excluded.base_notes,
          price_uah = excluded.price_uah,
          product_sku = excluded.product_sku,
          product_url = excluded.product_url,
          image_url = excluded.image_url,
          updated_at = CURRENT_TIMESTAMP
      `).bind(
        p.id, p.brand_id, p.brand_name, p.name, p.gender, p.concentration,
        p.primary_subfamily_id, p.family_code,
        p.top_notes, p.heart_notes, p.base_notes,
        p.price_uah, p.product_sku, p.product_url, p.image_url
      )
    );
  }

  if (brandStatements.length > 0) {
    await db.batch(brandStatements);
  }
  if (fragranceStatements.length > 0) {
    await db.batch(fragranceStatements);
  }

  return products.length;
}
