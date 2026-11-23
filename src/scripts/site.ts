interface ReaderPrefs {
  sa: boolean;
  iast: boolean;
  hi: boolean;
  en: boolean;
  theme: 'paper' | 'sepia' | 'dark';
  size: 'sm' | 'md' | 'lg';
  focus: boolean;
}

interface BookmarkItem {
  id: string; // e.g. "1.1.12"
  label: string; // e.g. "Bālakāṇḍa 1.1.12"
  path: string; // e.g. "/valmiki-ramayana/01-bala/001/#v12"
  excerpt: string;
}

const PREFS_KEY = 'vr:prefs';
const LAST_KEY = 'vr:last';
const BOOKMARKS_KEY = 'vr:bookmarks';

const KANDA_TABLE: readonly [number, string, string, string, number][] = [
  [1, '01-bala', 'बालकाण्डम्', 'Bālakāṇḍa', 77],
  [2, '02-ayodhya', 'अयोध्याकाण्डम्', 'Ayodhyākāṇḍa', 119],
  [3, '03-aranya', 'अरण्यकाण्डम्', 'Araṇyakāṇḍa', 75],
  [4, '04-kishkindha', 'किष्किन्धाकाण्डम्', 'Kiṣkindhākāṇḍa', 67],
  [5, '05-sundara', 'सुन्दरकाण्डम्', 'Sundarakāṇḍa', 68],
  [6, '06-yuddha', 'युद्धकाण्डम्', 'Yuddhakāṇḍa', 128],
  [7, '07-uttara', 'उत्तरकाण्डम्', 'Uttarakāṇḍa', 111],
];

const BASE = document.documentElement.dataset.base || '/';

function pad3(n: number): string {
  return String(n).padStart(3, '0');
}

function loadPrefs(): ReaderPrefs {
  const defaults: ReaderPrefs = {
    sa: true,
    iast: true,
    hi: true,
    en: true,
    theme: 'paper',
    size: 'md',
    focus: false,
  };
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return { ...defaults, ...parsed };
    }
  } catch {
    // ignore storage errors
  }
  return defaults;
}

function savePrefs(p: ReaderPrefs): void {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(p));
  } catch {
    // ignore storage errors
  }
}

function loadBookmarks(): BookmarkItem[] {
  try {
    const raw = localStorage.getItem(BOOKMARKS_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function saveBookmarks(list: BookmarkItem[]): void {
  try {
    localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(list));
  } catch {
    // ignore storage errors
  }
}

function updateThemeMeta(theme: ReaderPrefs['theme']): void {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (!meta) return;
  meta.setAttribute(
    'content',
    theme === 'dark' ? '#12100d' : theme === 'sepia' ? '#efe5d0' : '#faf6ee',
  );
}

function applyPrefs(p: ReaderPrefs): void {
  const r = document.documentElement;
  r.classList.remove('theme-paper', 'theme-sepia', 'theme-dark', 'size-sm', 'size-md', 'size-lg');
  r.classList.add(`theme-${p.theme || 'paper'}`, `size-${p.size || 'md'}`);
  r.classList.toggle('hide-sa', !p.sa);
  r.classList.toggle('hide-iast', !p.iast);
  r.classList.toggle('hide-hi', !p.hi);
  r.classList.toggle('hide-en', !p.en);
  r.classList.toggle('focus-mode', Boolean(p.focus));
  updateThemeMeta(p.theme);

  document.querySelectorAll<HTMLButtonElement>('[data-layer]').forEach((btn) => {
    const key = btn.dataset.layer as 'sa' | 'iast' | 'hi' | 'en' | undefined;
    if (key) btn.setAttribute('aria-pressed', String(Boolean(p[key])));
  });
  document.querySelectorAll<HTMLButtonElement>('[data-theme-set]').forEach((btn) => {
    btn.setAttribute('aria-pressed', String(btn.dataset.themeSet === p.theme));
  });
  document.querySelectorAll<HTMLButtonElement>('[data-size-set]').forEach((btn) => {
    btn.setAttribute('aria-pressed', String(btn.dataset.sizeSet === p.size));
  });
  document.querySelectorAll<HTMLButtonElement>('[data-focus-toggle]').forEach((btn) => {
    btn.setAttribute('aria-pressed', String(Boolean(p.focus)));
  });
}

let toastTimer: number | undefined;
function showToast(message: string, action?: { label: string; onClick: () => void }): void {
  const toast = document.getElementById('vr-toast');
  if (!toast) return;
  toast.innerHTML = '';

  const span = document.createElement('span');
  span.textContent = message;
  toast.appendChild(span);

  if (action) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'vr-toast-btn';
    btn.textContent = action.label;
    btn.addEventListener('click', () => {
      action.onClick();
    });
    toast.appendChild(btn);
  }

  toast.hidden = false;
  toast.classList.add('is-visible');
  if (toastTimer) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.classList.remove('is-visible');
    window.setTimeout(() => {
      toast.hidden = true;
    }, 200);
  }, 4200);
}

function hydrateDisplayPopover(): void {
  const pop = document.getElementById('display-pop');
  if (!pop || pop.childElementCount > 0) return;
  pop.innerHTML = `
    <div class="space-y-4 text-sm">
      <div>
        <p class="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">Paper &amp; Theme</p>
        <div class="grid grid-cols-3 gap-1.5" role="group" aria-label="Theme">
          <button type="button" data-theme-set="paper" aria-pressed="true" class="swatch-btn flex items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs">
            <span class="inline-block h-3 w-3 rounded-full border border-black/20" style="background:#faf6ee"></span>
            <span>Paper</span>
          </button>
          <button type="button" data-theme-set="sepia" aria-pressed="false" class="swatch-btn flex items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs">
            <span class="inline-block h-3 w-3 rounded-full border border-black/20" style="background:#efe5d0"></span>
            <span>Sepia</span>
          </button>
          <button type="button" data-theme-set="dark" aria-pressed="false" class="swatch-btn flex items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs">
            <span class="inline-block h-3 w-3 rounded-full border border-white/25" style="background:#12100d"></span>
            <span>Night</span>
          </button>
        </div>
      </div>
      <div>
        <p class="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">Text Size</p>
        <div class="grid grid-cols-3 gap-1.5" role="group" aria-label="Font size">
          <button type="button" data-size-set="sm" aria-pressed="false" class="swatch-btn rounded-md py-1.5 text-xs">A-</button>
          <button type="button" data-size-set="md" aria-pressed="true" class="swatch-btn rounded-md py-1.5 text-sm">A</button>
          <button type="button" data-size-set="lg" aria-pressed="false" class="swatch-btn rounded-md py-1.5 text-base">A+</button>
        </div>
      </div>
      <div class="flex items-center justify-between border-t border-[var(--border)] pt-3">
        <span class="text-xs font-medium text-[var(--ink)]">Focus Mode</span>
        <button type="button" data-focus-toggle aria-pressed="false" class="swatch-btn rounded-md px-2.5 py-1 text-xs">
          Toggle (f)
        </button>
      </div>
      <p class="m-0 border-t border-[var(--border)] pt-2.5 text-[11px] leading-relaxed text-[var(--muted)]">
        Keys: <kbd class="rounded border border-[var(--border)] px-1 font-mono">&larr;</kbd> <kbd class="rounded border border-[var(--border)] px-1 font-mono">&rarr;</kbd> sargas &middot;
        <kbd class="rounded border border-[var(--border)] px-1 font-mono">g</kbd> jump &middot;
        <kbd class="rounded border border-[var(--border)] px-1 font-mono">/</kbd> search &middot;
        Click any shloka number to copy or bookmark.
      </p>
    </div>
  `;
}

function initControls(prefs: ReaderPrefs): void {
  hydrateDisplayPopover();
  applyPrefs(prefs);

  document.querySelectorAll<HTMLButtonElement>('[data-layer]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const key = btn.dataset.layer as 'sa' | 'iast' | 'hi' | 'en' | undefined;
      if (!key) return;
      prefs[key] = !prefs[key];
      savePrefs(prefs);
      applyPrefs(prefs);
    });
  });

  document.querySelectorAll<HTMLButtonElement>('[data-theme-set]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const val = btn.dataset.themeSet as ReaderPrefs['theme'] | undefined;
      if (!val) return;
      prefs.theme = val;
      savePrefs(prefs);
      applyPrefs(prefs);
    });
  });

  document.querySelectorAll<HTMLButtonElement>('[data-size-set]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const val = btn.dataset.sizeSet as ReaderPrefs['size'] | undefined;
      if (!val) return;
      prefs.size = val;
      savePrefs(prefs);
      applyPrefs(prefs);
    });
  });

  document.querySelectorAll<HTMLButtonElement>('[data-focus-toggle]').forEach((btn) => {
    btn.addEventListener('click', () => {
      prefs.focus = !prefs.focus;
      savePrefs(prefs);
      applyPrefs(prefs);
    });
  });

  document.getElementById('exit-focus-btn')?.addEventListener('click', () => {
    prefs.focus = false;
    savePrefs(prefs);
    applyPrefs(prefs);
  });
}

function initScrollHeaderFallback(): void {
  if (typeof CSS !== 'undefined' && CSS.supports && CSS.supports('container-type', 'scroll-state')) {
    return;
  }
  const bar = document.querySelector<HTMLElement>('.top-bar');
  if (!bar) return;
  let lastY = window.scrollY;
  window.addEventListener(
    'scroll',
    () => {
      const maxY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
      const y = Math.max(0, Math.min(window.scrollY, maxY));
      if (Math.abs(y - lastY) < 4) return;
      bar.classList.toggle('is-hidden', y > lastY && y > bar.offsetHeight + 16);
      lastY = y;
    },
    { passive: true },
  );
}

function initJumpDialog(): void {
  const dlg = document.getElementById('jump-dialog') as HTMLDialogElement | null;
  if (!dlg) return;

  if (dlg.childElementCount === 0) {
    dlg.innerHTML = `
      <form id="jump-form" class="p-5 sm:p-6">
        <div class="flex items-center justify-between gap-2 border-b border-[var(--border)] pb-3">
          <h2 id="jump-title" class="text-lg font-semibold">Jump to Passage</h2>
          <button
            type="button"
            id="jump-close"
            class="cursor-pointer rounded px-2 py-0.5 text-sm text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--ink)]"
            aria-label="Close"
          >
            &times;
          </button>
        </div>
        <div class="mt-4 space-y-4">
          <div>
            <label for="jump-kanda" class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">Kāṇḍa</label>
            <select
              id="jump-kanda"
              class="mt-1.5 w-full rounded-md border border-[var(--border-strong)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)]"
            ></select>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="jump-sarga" class="flex items-baseline justify-between text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                <span>Sarga</span>
                <span id="jump-range-hint" class="font-normal normal-case">1 – 77</span>
              </label>
              <input
                id="jump-sarga"
                type="number"
                min="1"
                max="128"
                value="1"
                required
                class="mt-1.5 w-full rounded-md border border-[var(--border-strong)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
              />
            </div>
            <div>
              <label for="jump-verse" class="block text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">Shloka (optional)</label>
              <input
                id="jump-verse"
                type="number"
                min="1"
                placeholder="e.g. 12"
                class="mt-1.5 w-full rounded-md border border-[var(--border-strong)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--ink)]"
              />
            </div>
          </div>
        </div>
        <div class="mt-5 flex items-center justify-between gap-3 border-t border-[var(--border)] pt-4">
          <span class="text-xs text-[var(--muted)]">Shortcut: <kbd class="rounded border border-[var(--border)] px-1 font-mono">g</kbd></span>
          <button
            type="submit"
            class="cursor-pointer rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-[var(--accent-ink)] hover:opacity-90"
          >
            Go to Sarga &rarr;
          </button>
        </div>
      </form>
    `;
  }

  const kandaSelect = document.getElementById('jump-kanda') as HTMLSelectElement | null;
  const sargaInput = document.getElementById('jump-sarga') as HTMLInputElement | null;
  const verseInput = document.getElementById('jump-verse') as HTMLInputElement | null;
  const rangeHint = document.getElementById('jump-range-hint');
  const form = document.getElementById('jump-form') as HTMLFormElement | null;

  if (!kandaSelect || !sargaInput || !verseInput || !form) return;

  if (kandaSelect.options.length === 0) {
    for (const [num, slug, sa, iast, count] of KANDA_TABLE) {
      const opt = document.createElement('option');
      opt.value = slug;
      opt.textContent = `${num}. ${iast} (${sa}) · ${count} sargas`;
      kandaSelect.appendChild(opt);
    }
  }

  const readerRoot = document.getElementById('reader-root');
  const currentSlug = readerRoot?.dataset.slug;
  const currentSarga = readerRoot?.dataset.sarga;

  function syncRange(): number {
    const entry = KANDA_TABLE.find((k) => k[1] === kandaSelect!.value) ?? KANDA_TABLE[0];
    const maxS = entry[4];
    sargaInput!.max = String(maxS);
    if (rangeHint) rangeHint.textContent = `1 – ${maxS}`;
    const cur = Number(sargaInput!.value);
    if (cur > maxS) sargaInput!.value = String(maxS);
    return maxS;
  }

  kandaSelect.addEventListener('change', syncRange);

  function openJump(): void {
    if (currentSlug) kandaSelect!.value = currentSlug;
    if (currentSarga) sargaInput!.value = currentSarga;
    else if (!sargaInput!.value) sargaInput!.value = '1';
    verseInput!.value = '';
    syncRange();
    if (typeof dlg!.showModal === 'function') {
      dlg!.showModal();
    } else {
      dlg!.setAttribute('open', '');
    }
    sargaInput!.focus();
    sargaInput!.select();
  }

  document.querySelectorAll('[data-open-jump]').forEach((el) => {
    el.addEventListener('click', openJump);
  });

  document.getElementById('jump-close')?.addEventListener('click', () => {
    dlg.close();
  });

  dlg.addEventListener('click', (e) => {
    if (e.target === dlg) dlg.close();
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const maxS = syncRange();
    const sarga = Math.max(1, Math.min(maxS, Number(sargaInput.value) || 1));
    const verse = Number(verseInput.value);
    const hash = verse > 0 ? `#v${verse}` : '';
    window.location.href = `${BASE}${kandaSelect.value}/${pad3(sarga)}/${hash}`;
  });
}

function initReaderFeatures(): void {
  const root = document.getElementById('reader-root');
  if (!root) return;

  const slug = root.dataset.slug || '';
  const kandaNum = root.dataset.kanda || '';
  const kandaName = root.dataset.kandaName || '';
  const sargaNum = root.dataset.sarga || '';
  const sargaTitle = root.dataset.title || '';
  const path = root.dataset.path || window.location.pathname;

  // Persist last read position
  try {
    localStorage.setItem(
      LAST_KEY,
      JSON.stringify({ slug, sarga: Number(sargaNum), title: sargaTitle, path }),
    );
  } catch {
    // ignore
  }

  // Auto-open collapsible Dutt prose archive if linked directly to #en-N
  if (window.location.hash.startsWith('#en-')) {
    const enEl = document.getElementById('en');
    if (enEl && enEl.tagName === 'DETAILS') {
      (enEl as HTMLDetailsElement).open = true;
      const target = document.getElementById(window.location.hash.slice(1));
      target?.scrollIntoView();
    }
  }

  // Mark already-bookmarked verses
  function syncBookmarkMarkers(): void {
    const savedIds = new Set(loadBookmarks().map((b) => b.id));
    document.querySelectorAll<HTMLElement>('#verses > article.v').forEach((art) => {
      const vn = art.id.slice(1);
      const id = `${kandaNum}.${sargaNum}.${vn}`;
      art.classList.toggle('is-bookmarked', savedIds.has(id));
    });
  }
  syncBookmarkMarkers();

  // Delegated click handler on shloka number anchor (.vn)
  const versesEl = document.getElementById('verses');
  versesEl?.addEventListener('click', (e) => {
    const target = e.target as HTMLElement | null;
    const link = target?.closest<HTMLAnchorElement>('a.vn');
    if (!link) return;

    const art = link.closest<HTMLElement>('article.v');
    if (!art) return;
    const vn = art.id.slice(1);
    const refId = `${kandaNum}.${sargaNum}.${vn}`;
    const fullUrl = `${window.location.origin}${window.location.pathname}#v${vn}`;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(fullUrl).catch(() => {});
    }

    const saText = (art.querySelector('.sa')?.textContent || '').trim().slice(0, 72);
    const exists = () => loadBookmarks().some((b) => b.id === refId);

    const toggleBookmark = () => {
      const list = loadBookmarks();
      const idx = list.findIndex((b) => b.id === refId);
      if (idx >= 0) {
        list.splice(idx, 1);
        saveBookmarks(list);
        syncBookmarkMarkers();
        showToast(`Removed bookmark · ${refId}`);
      } else {
        list.unshift({
          id: refId,
          label: `${kandaName} ${refId}`,
          path: `${path}#v${vn}`,
          excerpt: saText,
        });
        saveBookmarks(list.slice(0, 40));
        syncBookmarkMarkers();
        showToast(`Bookmarked · ${refId}`);
      }
    };

    showToast(`Link copied · ${refId}`, {
      label: exists() ? '★ Remove bookmark' : '☆ Bookmark',
      onClick: toggleBookmark,
    });
  });
}

function initHomeFeatures(): void {
  // Continue reading card
  const box = document.getElementById('continue-box');
  const link = document.getElementById('continue-link');
  if (box && link) {
    try {
      const raw = localStorage.getItem(LAST_KEY);
      if (raw) {
        const last = JSON.parse(raw);
        if (last && last.path && last.title) {
          link.setAttribute('href', last.path);
          link.textContent = last.title;
          box.classList.remove('hidden');
        }
      }
    } catch {
      // ignore
    }
  }

  // Saved bookmarks list on Home
  const bmSection = document.getElementById('bookmarks-section');
  const bmList = document.getElementById('bookmarks-list');
  if (!bmSection || !bmList) return;

  function renderBookmarks(): void {
    const items = loadBookmarks();
    bmList!.innerHTML = '';
    if (items.length === 0) {
      bmSection!.classList.add('hidden');
      return;
    }
    bmSection!.classList.remove('hidden');
    for (const item of items) {
      const li = document.createElement('li');
      li.className = 'flex items-baseline justify-between gap-3 py-2.5';

      const a = document.createElement('a');
      a.href = item.path;
      a.className = 'group min-w-0 flex-1 no-underline';
      const title = document.createElement('span');
      title.className = 'font-semibold text-[var(--accent)] group-hover:underline';
      title.textContent = item.label;
      a.appendChild(title);
      if (item.excerpt) {
        const ex = document.createElement('span');
        ex.className = 'deva ml-2.5 text-sm text-[var(--muted)]';
        ex.textContent = item.excerpt + (item.excerpt.length >= 72 ? '…' : '');
        a.appendChild(ex);
      }

      const rm = document.createElement('button');
      rm.type = 'button';
      rm.className = 'cursor-pointer text-xs text-[var(--muted)] hover:text-[var(--accent)]';
      rm.textContent = 'Remove';
      rm.setAttribute('aria-label', `Remove bookmark ${item.label}`);
      rm.addEventListener('click', () => {
        const next = loadBookmarks().filter((b) => b.id !== item.id);
        saveBookmarks(next);
        renderBookmarks();
      });

      li.appendChild(a);
      li.appendChild(rm);
      bmList!.appendChild(li);
    }
  }
  renderBookmarks();
}

function initKeyboardShortcuts(prefs: ReaderPrefs): void {
  document.addEventListener('keydown', (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const el = document.activeElement as HTMLElement | null;
    if (
      el &&
      (el.tagName === 'INPUT' ||
        el.tagName === 'TEXTAREA' ||
        el.tagName === 'SELECT' ||
        el.isContentEditable)
    ) {
      return;
    }

    const dlg = document.getElementById('jump-dialog') as HTMLDialogElement | null;
    if (dlg?.open) return;

    if (e.key === '/') {
      e.preventDefault();
      const q = document.getElementById('search-q') as HTMLInputElement | null;
      if (q) q.focus();
      else window.location.href = `${BASE}search/`;
    } else if (e.key === 'g' || e.key === 'G') {
      const btn = document.querySelector<HTMLButtonElement>('[data-open-jump]');
      if (btn) {
        e.preventDefault();
        btn.click();
      }
    } else if (e.key === 'f' || e.key === 'F') {
      if (document.getElementById('reader-root')) {
        e.preventDefault();
        prefs.focus = !prefs.focus;
        savePrefs(prefs);
        applyPrefs(prefs);
      }
    } else if (e.key === 'Escape' && prefs.focus) {
      prefs.focus = false;
      savePrefs(prefs);
      applyPrefs(prefs);
    } else if (e.key === 'ArrowLeft') {
      const prev = document.querySelector<HTMLAnchorElement>('[data-nav-prev]');
      if (prev?.href) window.location.href = prev.href;
    } else if (e.key === 'ArrowRight') {
      const next = document.querySelector<HTMLAnchorElement>('[data-nav-next]');
      if (next?.href) window.location.href = next.href;
    }
  });
}

function initServiceWorker(): void {
  if (import.meta.env.PROD && 'serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register(`${BASE}sw.js`, { scope: BASE }).catch(() => {});
    });
  }
}

const prefs = loadPrefs();
initControls(prefs);
initScrollHeaderFallback();
initJumpDialog();
initReaderFeatures();
initHomeFeatures();
initKeyboardShortcuts(prefs);
initServiceWorker();
