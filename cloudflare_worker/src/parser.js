/**
 * parser.js
 * Витяг ольфакторної піраміди з опису товару та класифікація за Колесом Майкла Едвардса на базі ваг Жана Карля.
 */

const NOTE_TO_SUBFAMILY = {
  // Квіткові
  'троянда': 'floral_pure', 'жасмин': 'floral_pure', 'конвалія': 'floral_pure', 'півонія': 'floral_pure',
  'гарденія': 'floral_pure', 'тубероза': 'floral_pure', 'магнолія': 'floral_pure', 'фрезія': 'floral_pure',
  // М'які квіткові
  'ірис': 'floral_soft', 'пудрові ноти': 'floral_soft', 'фіалка': 'floral_soft', 'альдегіди': 'floral_soft',
  // Східно-квіткові
  'флердоранж': 'floral_oriental', 'османтус': 'floral_oriental', 'іланг-іланг': 'floral_oriental', 'гвоздика': 'floral_oriental',
  // М'які східні
  'ладан': 'oriental_soft', 'бензоїн': 'oriental_soft', 'амбра': 'oriental_soft', 'кардамон': 'oriental_soft',
  // Східні
  'ваніль': 'oriental_pure', 'боби тонка': 'oriental_pure', 'смоли': 'oriental_pure', 'опопонакс': 'oriental_pure', 'какао': 'oriental_pure', 'кориця': 'oriental_pure',
  // Деревно-східні
  'пачулі': 'oriental_woody', 'сандал': 'oriental_woody', 'шафран': 'oriental_woody', 'уд': 'oriental_woody',
  // Деревні
  'кедр': 'woody_pure', 'ветивер': 'woody_pure', 'гуаяк': 'woody_pure', 'деревина': 'woody_pure',
  // Мохові
  'дубовий мох': 'woody_mossy', 'мох': 'woody_mossy', 'ладанник': 'woody_mossy',
  // Сухі деревні (шкіряні)
  'шкіра': 'woody_dry', 'тютюн': 'woody_dry', 'березовий дьоготь': 'woody_dry', 'дим': 'woody_dry',
  // Цитрусові
  'лимон': 'fresh_citrus', 'бергамот': 'fresh_citrus', 'мандарин': 'fresh_citrus', 'грейпфрут': 'fresh_citrus', 'лайм': 'fresh_citrus', 'апельсин': 'fresh_citrus',
  // Водні
  'морська сіль': 'fresh_aquatic', 'калон': 'fresh_aquatic', 'морські ноти': 'fresh_aquatic', 'водорості': 'fresh_aquatic',
  // Зелені
  'гальбанум': 'fresh_green', 'м\'ята': 'fresh_green', 'зелений чай': 'fresh_green', 'трава': 'fresh_green',
  // Фруктові
  'чорна смородина': 'fresh_fruity', 'груша': 'fresh_fruity', 'персик': 'fresh_fruity', 'яблуко': 'fresh_fruity', 'малина': 'fresh_fruity', 'вишня': 'fresh_fruity', 'лічі': 'fresh_fruity',
  // Ароматичні
  'лаванда': 'fresh_aromatic', 'розмарин': 'fresh_aromatic', 'шавлія': 'fresh_aromatic', 'чебрець': 'fresh_aromatic'
};

const SUBFAMILY_TO_FAMILY = {
  floral_pure: 'floral', floral_soft: 'floral', floral_oriental: 'floral',
  oriental_soft: 'oriental', oriental_pure: 'oriental', oriental_woody: 'oriental',
  woody_pure: 'woody', woody_mossy: 'woody', woody_dry: 'woody',
  fresh_citrus: 'fresh', fresh_aquatic: 'fresh', fresh_green: 'fresh', fresh_fruity: 'fresh', fresh_aromatic: 'fresh'
};

export function extractPyramidFromText(text) {
  const pyramid = { top_notes: [], heart_notes: [], base_notes: [] };
  if (!text) return pyramid;

  const clean = text.replace(/\xa0/g, ' ');
  const topMatch = clean.match(/(?:початков[аі]\s+нот[аи]|верхні\s+ноти)\s*[:\-–]\s*([^;\.\n\r]+)/i);
  const heartMatch = clean.match(/(?:нот[аи]\s+серця|середні\s+ноти)\s*[:\-–]\s*([^;\.\n\r]+)/i);
  const baseMatch = clean.match(/(?:кінцев[аі]\s+нот[аи]|базов[іа]\s+ноти|шлейф)\s*[:\-–]\s*([^;\.\n\r]+)/i);

  const splitNotes = (str) => {
    return (str || '')
      .split(/[,;]|\s+та\s+|\s+і\s+/)
      .map(s => s.trim().replace(/\.$/, '').toLowerCase())
      .filter(s => s.length > 1);
  };

  if (topMatch) pyramid.top_notes = splitNotes(topMatch[1]);
  if (heartMatch) pyramid.heart_notes = splitNotes(heartMatch[1]);
  if (baseMatch) pyramid.base_notes = splitNotes(baseMatch[1]);

  return pyramid;
}

export function classifyPyramid(topNotes = [], heartNotes = [], baseNotes = []) {
  const scores = {};

  const processNotes = (notes, weight) => {
    notes.forEach(note => {
      const n = note.toLowerCase().trim();
      for (const [kw, sfId] of Object.entries(NOTE_TO_SUBFAMILY)) {
        if (n.includes(kw) || kw.includes(n)) {
          scores[sfId] = (scores[sfId] || 0) + weight;
        }
      }
    });
  };

  // Метод Жана Карля: Базові (1.5) > Ноти серця (1.2) > Верхні ноти (0.7)
  processNotes(baseNotes, 1.5);
  processNotes(heartNotes, 1.2);
  processNotes(topNotes, 0.7);

  let bestSubfamily = 'floral_pure';
  let maxScore = -1;

  for (const [sfId, score] of Object.entries(scores)) {
    if (score > maxScore) {
      maxScore = score;
      bestSubfamily = sfId;
    }
  }

  const familyCode = SUBFAMILY_TO_FAMILY[bestSubfamily] || 'floral';
  return {
    primary_subfamily_id: bestSubfamily,
    family_code: familyCode,
    confidence_score: maxScore > 0 ? maxScore : 0
  };
}
