"""
Seletores e script de extração DOM para páginas /delivery/ do iFood.

Atualizar aqui quando o iFood redesenhar o frontend.
Prioridade: data-testid > ARIA > estrutura relativa.
"""

import json

# ── Loja (header) ────────────────────────────────────────────
STORE_NAME = [
    '[data-testid="merchant-name"]',
    '[data-testid="restaurant-name"]',
    "header h1",
    "main h1",
    "h1",
]

STORE_LOGO = [
    '[data-testid="merchant-logo"] img',
    '[data-testid="restaurant-logo"] img',
    'header img[alt*="logo" i]',
    'header img[src*="logosgde"]',
    'header img[src*="ifood"]',
]

STORE_COVER = [
    '[data-testid="merchant-banner"] img',
    '[data-testid="restaurant-banner"] img',
    '[data-testid="header-image"] img',
    'img[src*="capa/"]',
    'header ~ div img[src*="ifood"]',
]

# ── Cardápio (iFood usa data-test-id com hífen, não data-testid) ─
MENU_ROOT = [
    ".restaurant-menu-group",
    '[data-test-id^="menu-group-"]',
    '[data-test-id="restaurant-menu-group-item"]',
    "main",
]

MENU_GROUP = ".restaurant-menu-group, [data-test-id^='menu-group-']"

MENU_GROUP_TITLE = "h2.restaurant-menu-group__title"

MENU_GROUP_ITEM = '[data-test-id="restaurant-menu-group-item"]'

# Card do produto: apenas o <a class="dish-card"> (evita duplicar wrappers)
PRODUCT_CARD = [
    'a.dish-card[data-test-id="dish-card-test-id"]',
    "a.dish-card",
    '[data-test-id="dish-card-test-id"]',
]

PRODUCT_NAME = [
    '[data-testid="menu-item-name"]',
    '[data-testid="dish-name"]',
    "h3",
    "h4",
    "strong",
]

PRODUCT_PRICE = [
    '[data-testid="menu-item-price"]',
    '[data-testid="dish-price"]',
    '[data-testid="price"]',
]

PRODUCT_IMAGE = [
    '[data-testid="menu-item-image"] img',
    "img",
]

PRODUCT_LINK = ["a[href*='/delivery/']", "a[href*='product']", "a"]

CUSTOMIZABLE_HINT = [
    '[data-testid="customizable"]',
    ':text("Personalizar")',
    ':text("Escolha")',
    ':text("Monte")',
]

# ── Modal / drawer de produto ──────────────────────────────────
PRODUCT_MODAL = [
    ".dish-garnishes",
    ".garnish-choices__list",
    '[data-test-id="form"]',
    '[role="dialog"]',
    '[data-testid="product-modal"]',
    '[data-testid="dish-modal"]',
]

MODAL_CLOSE = [
    '[data-testid="modal-close"]',
    '[data-testid="close-button"]',
    'button[aria-label*="fechar" i]',
    'button[aria-label*="close" i]',
]

MODAL_GROUP_TITLE = [
    '[data-testid="option-group-title"]',
    '[data-testid="complement-group"] h3',
    '[role="dialog"] h3',
    '[role="dialog"] h4',
]

MODAL_OPTION = [
    '[data-testid="option-item"]',
    '[data-testid="complement-option"]',
    '[role="dialog"] label',
    '[role="dialog"] li',
]

# Extração alinhada ao markup real: .restaurant-menu-group > h2 + ul > li > a.dish-card
EXTRACT_VISIBLE_MENU_JS = """
(merchantId) => {
  const text = (el) => (el && (el.textContent || '').trim()) || '';
  const storeNameSels = %STORE_NAME%;
  const logoSels = %STORE_LOGO%;
  const coverSels = %STORE_COVER%;

  const priceRe = /(?:R\\$\\s*|r\\$\\s*|(?:a partir de|apartir de)\\s*)([\\d.,]+)/i;
  const pratoRe = /[?&]prato=([0-9a-f-]{36})/i;

  let storeName = '';
  for (const sel of storeNameSels) {
    const el = document.querySelector(sel);
    if (el) {
      storeName = text(el);
      if (storeName.length > 2) break;
    }
  }

  let logoSrc = null;
  for (const sel of logoSels) {
    const el = document.querySelector(sel);
    if (el && el.src) { logoSrc = el.src; break; }
  }

  let coverSrc = null;
  for (const sel of coverSels) {
    const el = document.querySelector(sel);
    if (el && el.src) { coverSrc = el.src; break; }
  }

  const parseDishCard = (card) => {
    const nameEl =
      card.querySelector('h3.dish-card__description') ||
      card.querySelector('.dish-card__description') ||
      card.querySelector('h3');
    const name = text(nameEl);
    if (!name || name.length < 2) return null;

    const priceEl =
      card.querySelector('[data-test-id="dish-card-price"]') ||
      card.querySelector('.dish-card__price');
    let priceText = text(priceEl);
    if (!priceText) {
      const m = (card.innerText || '').match(priceRe);
      priceText = m ? ('R$ ' + m[1]) : '';
    }
    if (!priceText) return null;

    const detailsEl = card.querySelector('.dish-card__details, span.dish-card__details');
    const detailsText = text(detailsEl) || null;

    const isProductPhoto = (img) => {
      if (!img) return false;
      const src = img.currentSrc || img.src || '';
      if (!src || /serves_\\d|dish-info-serves|\\/static\\/images\\/icons\\//i.test(src)) {
        return false;
      }
      if (/pratos\\//i.test(src) || /static\\.ifood-static\\.com\\.br/i.test(src)) {
        return true;
      }
      return (img.className || '').includes('dish-card__image');
    };

    const pickProductImage = (cardEl, productName) => {
      const norm = (s) => (s || '').trim().toLowerCase();
      const want = norm(productName);
      const imgs = Array.from(cardEl.querySelectorAll('img'));
      if (want) {
        const byAlt = imgs.find((img) => norm(img.getAttribute('alt')) === want && isProductPhoto(img));
        if (byAlt) return byAlt.currentSrc || byAlt.src;
      }
      const byClass = cardEl.querySelector('img.dish-card__image');
      if (byClass && isProductPhoto(byClass)) return byClass.currentSrc || byClass.src;
      const inContainer = cardEl.querySelector('.dish-card__container-image img');
      if (inContainer && isProductPhoto(inContainer)) return inContainer.currentSrc || inContainer.src;
      const any = imgs.find((img) => isProductPhoto(img));
      return any ? (any.currentSrc || any.src) : null;
    };

    const imageSrc = pickProductImage(card, name);

    const href = card.getAttribute('href') || '';
    const pm = href.match(pratoRe);
    const id = pm ? pm[1] : null;

    const customizable = !!id;

    return {
      id,
      name,
      priceText,
      detailsText,
      imageSrc,
      href,
      customizable,
    };
  };

  const categories = [];
  const seenGlobal = new Set();
  let totalCards = 0;

  const groups = document.querySelectorAll(
    '.restaurant-menu-group, [data-test-id^="menu-group-"]'
  );

  groups.forEach((group, gIdx) => {
    const titleEl =
      group.querySelector('h2.restaurant-menu-group__title') ||
      group.querySelector('h2');
    const catName = text(titleEl);
    if (!catName) return;

    const groupId =
      group.getAttribute('data-test-id') ||
      group.getAttribute('id') ||
      ('cat-' + gIdx);

    const items = [];
    const itemNodes = group.querySelectorAll(
      '[data-test-id="restaurant-menu-group-item"] a.dish-card, li a.dish-card'
    );

    itemNodes.forEach((card) => {
      const parsed = parseDishCard(card);
      if (!parsed) return;
      const key = (parsed.id || parsed.name) + '|' + parsed.priceText;
      if (seenGlobal.has(key)) return;
      seenGlobal.add(key);
      items.push(parsed);
      totalCards += 1;
    });

    if (items.length) {
      categories.push({
        id: groupId,
        name: catName,
        items,
      });
    }
  });

  const selectorHits = {
    menuGroups: groups.length,
    dishCards: document.querySelectorAll('a.dish-card').length,
    menuItems: document.querySelectorAll('[data-test-id="restaurant-menu-group-item"]').length,
  };

  return {
    store: { name: storeName, logoSrc, coverSrc },
    categories,
    totalCards,
    debug: {
      pageTitle: document.title,
      pageUrl: location.href,
      storeName,
      categoryCount: categories.length,
      selectorHits,
    },
  };
}
"""

DOM_DIAGNOSTIC_SCRIPT = """
(merchantId) => {
  const priceRe = /(?:R\\$\\s*|a partir de\\s*)([\\d.,]+)/gi;
  const body = document.body ? document.body.innerText : '';
  const prices = body.match(priceRe) || [];
  const groups = document.querySelectorAll(
    '.restaurant-menu-group, [data-test-id^="menu-group-"]'
  );
  const categoryNames = [];
  groups.forEach((g) => {
    const h = g.querySelector('h2.restaurant-menu-group__title, h2');
    if (h && h.textContent) categoryNames.push(h.textContent.trim());
  });
  return {
    pageTitle: document.title,
    pageUrl: location.href,
    priceMatches: prices.length,
    menuGroupCount: groups.length,
    categoryNames: categoryNames.slice(0, 20),
    dishCardCount: document.querySelectorAll('a.dish-card').length,
    menuItemCount: document.querySelectorAll('[data-test-id="restaurant-menu-group-item"]').length,
    merchantId,
  };
}
"""

EXTRACT_VISIBLE_MENU_SCRIPT = (
    EXTRACT_VISIBLE_MENU_JS.replace("%STORE_NAME%", json.dumps(STORE_NAME))
    .replace("%STORE_LOGO%", json.dumps(STORE_LOGO))
    .replace("%STORE_COVER%", json.dumps(STORE_COVER))
)

EXTRACT_MODAL_GROUPS_JS = """
() => {
  const priceRe = /(?:\\+\\s*)?R\\$\\s*([\\d.,]+)/i;
  const root =
    document.querySelector('.dish-garnishes') ||
    document.querySelector('section.dish-garnishes') ||
    document.querySelector('[role="dialog"]') ||
    document.body;
  if (!root) return [];

  const groups = [];
  const sections = root.querySelectorAll(
    'section.garnish-choices__list, .garnish-choices__list'
  );

  const parseLabel = (label) => {
    const desc = label.querySelector('.garnish-choices__option-desc');
    if (!desc) return null;
    const priceEl = label.querySelector('.garnish-choices__option-price');
    let name = (desc.textContent || '').trim();
    let priceText = priceEl ? (priceEl.textContent || '').trim() : '';
    if (!priceText) {
      const m = name.match(priceRe);
      if (m) {
        priceText = 'R$ ' + m[1];
        name = name.replace(/\\+\\s*R\\$\\s*[\\d.,]+.*$/i, '').trim();
      }
    }
    priceText = (priceText || '').replace(/^\\+\\s*/, '').trim();
    if (!priceText) priceText = 'R$ 0';
    if (!name || name.length < 1) return null;
    return {
      id: label.getAttribute('for') || '',
      name,
      priceText,
    };
  };

  sections.forEach((sec) => {
    const titleEl = sec.querySelector('.garnish-choices__title, p.garnish-choices__title');
    let groupName = 'Adicionais';
    if (titleEl) {
      const clone = titleEl.cloneNode(true);
      clone.querySelectorAll('.garnish-choices__title-desc').forEach((el) => el.remove());
      groupName = (clone.textContent || '').trim() || groupName;
    }

    const options = [];
    sec.querySelectorAll('label.garnish-choices__label').forEach((label) => {
      const opt = parseLabel(label);
      if (!opt) return;
      if (options.some((o) => o.name === opt.name)) return;
      options.push(opt);
    });

    if (options.length) {
      groups.push({ name: groupName, options });
    }
  });

  if (groups.length === 0) {
    const labels = root.querySelectorAll('label.garnish-choices__label');
    const options = [];
    labels.forEach((label) => {
      const opt = parseLabel(label);
      if (!opt) return;
      if (options.some((o) => o.name === opt.name)) return;
      options.push(opt);
    });
    if (options.length) {
      groups.push({ name: 'Adicionais', options });
    }
  }

  return groups;
}
"""
