/**
 * wheel.js
 * Топологія Колеса Ароматів Майкла Едвардса (14 підгруп) та ольфакторний метчинг для Cloudflare Workers.
 */

export const FAMILIES = {
  floral: {
    code: 'floral',
    name_uk: 'Квіткові',
    name_en: 'Floral',
    color_hex: '#E879F9',
    profile: 'Романтичні, пудрові, елегантні, класичні'
  },
  oriental: {
    code: 'oriental',
    name_uk: 'Східні (Бурштинові)',
    name_en: 'Oriental / Amber',
    color_hex: '#F59E0B',
    profile: 'Чуттєві, теплі, насичені, пряні, огортаючі'
  },
  woody: {
    code: 'woody',
    name_uk: 'Деревні',
    name_en: 'Woody',
    color_hex: '#10B981',
    profile: 'Землянисті, строгі, глибокі, шляхетні, сухі'
  },
  fresh: {
    code: 'fresh',
    name_uk: 'Свіжі',
    name_en: 'Fresh',
    color_hex: '#06B6D4',
    profile: 'Енергійні, чисті, яскраві, бадьорі, іскристі'
  }
};

export const SUBFAMILIES = [
  { id: 'floral_pure', ring_index: 0, family_code: 'floral', name_uk: 'Квіткові', name_en: 'Floral', color_hex: '#F472B6', key_ingredients: ['троянда', 'жасмин', 'конвалія', 'півонія', 'гарденія', 'тубероза'] },
  { id: 'floral_soft', ring_index: 1, family_code: 'floral', name_uk: 'М\'які квіткові', name_en: 'Soft Floral', color_hex: '#EC4899', key_ingredients: ['ірис', 'пудрові ноти', 'фіалка', 'альдегіди', 'мускус'] },
  { id: 'floral_oriental', ring_index: 2, family_code: 'floral', name_uk: 'Східно-квіткові', name_en: 'Floral Oriental', color_hex: '#D946EF', key_ingredients: ['флердоранж', 'османтус', 'гвоздика', 'солодка спеція', 'іланг-іланг'] },
  { id: 'oriental_soft', ring_index: 3, family_code: 'oriental', name_uk: 'М\'які східні', name_en: 'Soft Oriental', color_hex: '#FB923C', key_ingredients: ['ладан', 'бензоїн', 'м\'яка амбра', 'кардамон', 'мускатний горіх'] },
  { id: 'oriental_pure', ring_index: 4, family_code: 'oriental', name_uk: 'Східні', name_en: 'Oriental', color_hex: '#F59E0B', key_ingredients: ['ваніль', 'смоли', 'боби тонка', 'амбра', 'опопонакс'] },
  { id: 'oriental_woody', ring_index: 5, family_code: 'oriental', name_uk: 'Деревно-східні', name_en: 'Woody Oriental', color_hex: '#D97706', key_ingredients: ['пачулі', 'сандал', 'темний шоколад', 'амброве дерево', 'шафран'] },
  { id: 'woody_pure', ring_index: 6, family_code: 'woody', name_uk: 'Деревні', name_en: 'Woods', color_hex: '#059669', key_ingredients: ['кедр', 'ветивер', 'дерево уд', 'сандалове дерево', 'гуаяк'] },
  { id: 'woody_mossy', ring_index: 7, family_code: 'woody', name_uk: 'Мохові деревні (Шипрові)', name_en: 'Mossy Woods / Chypre', color_hex: '#10B981', key_ingredients: ['дубовий мох', 'бергамот', 'ладанник', 'земляні ноти', 'листи пачулі'] },
  { id: 'woody_dry', ring_index: 8, family_code: 'woody', name_uk: 'Сухі деревні (Шкіряні)', name_en: 'Dry Woods / Leather', color_hex: '#34D399', key_ingredients: ['шкіра', 'тютюн', 'березовий дьоготь', 'суха деревина', 'дим'] },
  { id: 'fresh_citrus', ring_index: 9, family_code: 'fresh', name_uk: 'Цитрусові', name_en: 'Citrus', color_hex: '#06B6D4', key_ingredients: ['лимон', 'бергамот', 'мандарин', 'грейпфрут', 'лайм', 'вербена'] },
  { id: 'fresh_aquatic', ring_index: 10, family_code: 'fresh', name_uk: 'Водні (Акватичні)', name_en: 'Water / Aquatic', color_hex: '#0EA5E9', key_ingredients: ['морська сіль', 'калон', 'водорості', 'морський бриз', 'латаття'] },
  { id: 'fresh_green', ring_index: 11, family_code: 'fresh', name_uk: 'Зелені', name_en: 'Green', color_hex: '#38BDF8', key_ingredients: ['скошена трава', 'гальбанум', 'листя фіалки', 'м\'ята', 'зелений чай'] },
  { id: 'fresh_fruity', ring_index: 12, family_code: 'fresh', name_uk: 'Фруктові', name_en: 'Fruity', color_hex: '#818CF8', key_ingredients: ['чорна смородина', 'персик', 'яблуко', 'груша', 'малина', 'лічі'] },
  { id: 'fresh_aromatic', ring_index: 13, family_code: 'fresh', name_uk: 'Ароматичні (Фужерні)', name_en: 'Aromatic / Fougère', color_hex: '#A78BFA', key_ingredients: ['лаванда', 'розмарин', 'шавлія', 'базилік', 'чебрець'] }
];

export const SUBFAMILIES_BY_ID = {};
SUBFAMILIES.forEach(sf => { SUBFAMILIES_BY_ID[sf.id] = sf; });

export function calculateRingDistance(idxA, idxB) {
  const diff = Math.abs(idxA - idxB);
  return Math.min(diff, 14 - diff);
}

export function classifyRelationship(distance) {
  if (distance === 0) return 'exact';
  if (distance <= 3) return 'adjacent';
  if (distance >= 5) return 'complementary';
  return 'moderate';
}

export function matchFragrancesOnEdge(allFragrances, sourceSubfamilyId, referenceFragranceId = null) {
  let sourceNotes = [];
  if (referenceFragranceId) {
    const ref = allFragrances.find(f => f.id === referenceFragranceId);
    if (ref) {
      sourceSubfamilyId = ref.primary_subfamily_id;
      const parseNotes = (arr) => Array.isArray(arr) ? arr : (typeof arr === 'string' ? JSON.parse(arr || '[]') : []);
      sourceNotes = [...parseNotes(ref.top_notes), ...parseNotes(ref.heart_notes), ...parseNotes(ref.base_notes)];
    }
  }

  const srcSf = SUBFAMILIES_BY_ID[sourceSubfamilyId];
  if (!srcSf) return { exact: [], adjacent: [], complementary: [] };

  const buckets = { exact: [], adjacent: [], complementary: [] };

  allFragrances.forEach(f => {
    if (referenceFragranceId && f.id === referenceFragranceId) return;
    const tgtSf = SUBFAMILIES_BY_ID[f.primary_subfamily_id];
    if (!tgtSf) return;

    const dist = calculateRingDistance(srcSf.ring_index, tgtSf.ring_index);
    const rel = classifyRelationship(dist);

    const parseNotes = (arr) => Array.isArray(arr) ? arr : (typeof arr === 'string' ? JSON.parse(arr || '[]') : []);
    const targetNotes = [...parseNotes(f.top_notes), ...parseNotes(f.heart_notes), ...parseNotes(f.base_notes)];

    let noteSim = 0;
    if (sourceNotes.length && targetNotes.length) {
      const sA = new Set(sourceNotes.map(n => n.toLowerCase().trim()));
      const sB = new Set(targetNotes.map(n => n.toLowerCase().trim()));
      let inter = 0;
      sA.forEach(n => { if (sB.has(n)) inter++; });
      noteSim = inter / Math.max(1, (sA.size + sB.size - inter));
    }

    let score = 0.5;
    if (rel === 'exact') {
      score = 0.65 + (0.35 * noteSim);
    } else if (rel === 'adjacent') {
      const bonus = (dist === 1) ? 0.20 : (dist === 2 ? 0.12 : 0.05);
      score = 0.55 + bonus + (0.25 * noteSim);
    } else if (rel === 'complementary') {
      const contrast = (dist === 7) ? 1.0 : 0.88;
      score = 0.50 + (0.30 * contrast) + (0.20 * (1 - noteSim));
    }

    const item = {
      fragrance: {
        ...f,
        top_notes: parseNotes(f.top_notes),
        heart_notes: parseNotes(f.heart_notes),
        base_notes: parseNotes(f.base_notes)
      },
      relation: rel,
      ring_distance: dist,
      score: Math.round(score * 10000) / 10000,
      target_subfamily: tgtSf
    };

    if (buckets[rel]) {
      buckets[rel].push(item);
    }
  });

  for (const k in buckets) {
    buckets[k].sort((a, b) => b.score - a.score);
    buckets[k] = buckets[k].slice(0, 8);
  }

  return buckets;
}
