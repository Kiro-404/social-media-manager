/* Social Media Manager dashboard — plain JS, no build step.
 * All dynamic text goes through textContent (see el()), so LLM-generated
 * content can never be interpreted as HTML. */
"use strict";

const PLATFORMS = { youtube: "يوتيوب", instagram: "إنستغرام", facebook: "فيسبوك", tiktok: "تيك توك", twitter: "X / تويتر" };
const STATUS = { queued: "في الانتظار", publishing: "جاري النشر", published: "تم النشر", failed: "فشل", cancelled: "ملغي" };

let SERVER_TZ = "Africa/Cairo";
const view = document.getElementById("view");
/** Replace the page body; accepts nested arrays of nodes (DOM replaceChildren would stringify them). */
function show(...nodes) { view.replaceChildren(...nodes.flat(Infinity).filter(Boolean)); }

// ---------- helpers ----------
function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else if (k === "value") node.value = v;
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

let toastTimer;
function toast(msg, isError = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "show" + (isError ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.className = ""), isError ? 6000 : 2500);
}

class AuthError extends Error { constructor() { super("login required"); } }

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && !path.startsWith("/auth/")) throw new AuthError();
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch (_) { /* non-JSON error body */ }
    throw new Error(detail);
  }
  return res.json();
}

/** Run an async action behind a button: disables it, toasts failures. */
async function act(button, fn, okMsg) {
  button.disabled = true;
  try {
    await fn();
    if (okMsg) toast(okMsg);
  } catch (e) {
    toast(e.message, true);
  } finally {
    button.disabled = false;
  }
}

function fmtTime(iso) {
  return new Date(iso).toLocaleString("ar-EG", { timeZone: SERVER_TZ, dateStyle: "medium", timeStyle: "short" });
}

function chip(status) { return el("span", { class: `chip ${status}` }, STATUS[status] || status); }
function platChip(p) { return el("span", { class: "chip plat" }, PLATFORMS[p] || p); }
function empty(msg) { return el("div", { class: "empty" }, msg); }

function field(label, input) { return el("label", {}, label, input); }

/** Default value for <input type=datetime-local>: one hour from now, in the server's timezone. */
function defaultWhen() {
  const d = new Date(Date.now() + 3600_000);
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone: SERVER_TZ, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).formatToParts(d).map((p) => [p.type, p.value])
  );
  return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}`;
}

// ---------- views ----------
async function renderOverview() {
  const [stats, posts] = await Promise.all([api("/stats"), api("/schedule?status=queued")]);
  const tile = (n, l, cls = "") => el("div", { class: `stat ${cls}` }, el("div", { class: "n" }, n), el("div", { class: "l" }, l));
  show(
    el("h2", {}, "نظرة عامة"),
    el("div", { class: "grid" },
      tile(stats.niches, "مجالات"), tile(stats.accounts, "حسابات مفعّلة"), tile(stats.trends, "ترندات"),
      tile(stats.ideas, "أفكار"), tile(stats.pieces, "محتوى جاهز"),
      tile(stats.queued, "في الانتظار"), tile(stats.published, "تم نشرها", "ok"),
      tile(stats.failed, "فشلت", stats.failed ? "bad" : "")
    ),
    el("h2", {}, "المنشورات القادمة"),
    posts.length ? el("div", {}, posts.slice(0, 5).map(postCard)) : empty("مفيش منشورات مجدولة")
  );
}

function postCard(p) {
  return el("div", { class: "card" },
    el("div", { class: "row between" },
      el("div", {}, el("h3", {}, p.idea_title || `محتوى #${p.content_piece_id}`), el("div", { class: "muted" }, fmtTime(p.scheduled_for))),
      el("div", { class: "row" }, platChip(p.platform), chip(p.status))
    )
  );
}

// -- Setup: niches + accounts
async function renderSetup() {
  const [niches, accounts] = await Promise.all([api("/niches"), api("/accounts")]);

  const nicheForm = el("form", { class: "stack" },
    field("اسم المجال", el("input", { name: "name", required: true, placeholder: "لياقة منزلية" })),
    field("وصف المجال", el("textarea", { name: "description", placeholder: "تمارين سريعة في البيت بدون أدوات" })),
    field("الجمهور المستهدف", el("input", { name: "target_audience" })),
    field("أسلوب الكلام", el("input", { name: "tone_of_voice", placeholder: "حماسي وودود" })),
    field("اللغة", el("select", { name: "language" }, el("option", { value: "ar" }, "عربي"), el("option", { value: "en" }, "English"))),
    el("button", { class: "btn primary", type: "submit" }, "إضافة المجال")
  );
  nicheForm.addEventListener("submit", (e) => {
    e.preventDefault();
    act(e.submitter, async () => {
      await api("/niches", { method: "POST", body: Object.fromEntries(new FormData(nicheForm)) });
      await renderSetup();
    }, "تمت إضافة المجال");
  });

  const accForm = el("form", { class: "stack" },
    field("المنصة", el("select", { name: "platform" }, Object.entries(PLATFORMS).map(([k, v]) => el("option", { value: k }, v)))),
    field("اسم العرض", el("input", { name: "display_name", placeholder: "قناتي" })),
    el("button", { class: "btn primary", type: "submit" }, "إضافة الحساب")
  );
  accForm.addEventListener("submit", (e) => {
    e.preventDefault();
    act(e.submitter, async () => {
      await api("/accounts", { method: "POST", body: Object.fromEntries(new FormData(accForm)) });
      await renderSetup();
    }, "تمت إضافة الحساب");
  });

  const active = accounts.filter((a) => a.is_active);
  show(
    el("h2", {}, "المجالات"),
    niches.length ? niches.map((n) => el("div", { class: "card" }, el("h3", {}, n.name), el("div", { class: "muted" }, [n.description, n.tone_of_voice].filter(Boolean).join(" — ")))) : empty("ضيف مجالك الأول عشان الأفكار تتولّد على أساسه"),
    el("div", { class: "card" }, nicheForm),
    el("h2", {}, "الحسابات"),
    el("p", { class: "muted" }, "ده بيسجّل الحساب في التطبيق بس. مفاتيح كل منصة بتتحط في ملف .env (شوف README)."),
    active.length ? active.map((a) => el("div", { class: "card row between" },
      el("div", { class: "row" }, platChip(a.platform), el("strong", {}, a.display_name || "—")),
      el("button", { class: "btn danger", onclick: (e) => act(e.currentTarget, async () => { await api(`/accounts/${a.id}`, { method: "DELETE" }); await renderSetup(); }, "تم التعطيل") }, "تعطيل")
    )) : empty("مفيش حسابات"),
    el("div", { class: "card" }, accForm)
  );
}

// -- Trends
async function renderTrends() {
  const trends = await api("/trends?limit=100");
  const btn = el("button", { class: "btn primary" }, "جمع ترندات جديدة الآن");
  btn.addEventListener("click", () => act(btn, async () => { await api("/trends/collect", { method: "POST" }); await renderTrends(); }, "تم تحديث الترندات"));
  show(
    el("div", { class: "row between" }, el("h2", {}, "الترندات"), btn),
    trends.length
      ? el("div", { class: "table-wrap" }, el("table", {},
          el("thead", {}, el("tr", {}, ["الكلمة", "المصدر", "الدرجة", "الوقت"].map((h) => el("th", {}, h)))),
          el("tbody", {}, trends.map((t) => el("tr", {}, el("td", {}, t.keyword), el("td", {}, t.source), el("td", {}, Math.round(t.score)), el("td", {}, fmtTime(t.fetched_at)))))))
      : empty("لسه مفيش ترندات — دوس على الزرار")
  );
}

// -- Ideas
async function renderIdeas() {
  const [niches, trends, ideas, pieces] = await Promise.all([api("/niches"), api("/trends?limit=30"), api("/content/ideas"), api("/content/pieces")]);
  const piecesByIdea = {};
  pieces.forEach((p) => (piecesByIdea[p.idea_id] = (piecesByIdea[p.idea_id] || 0) + 1));

  const nicheSel = el("select", { name: "niche_id" }, niches.map((n) => el("option", { value: n.id }, n.name)));
  const trendSel = el("select", { name: "trend_signal_id" },
    el("option", { value: "" }, "أحدث ترند (تلقائي)"),
    trends.map((t) => el("option", { value: t.id }, `${t.keyword} — ${t.source}`)));
  const genBtn = el("button", { class: "btn primary", type: "submit" }, "ولّد فكرة");
  const genForm = el("form", { class: "stack" }, field("المجال", nicheSel), field("الترند", trendSel), genBtn);
  genForm.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!niches.length) return toast("ضيف مجال الأول من تبويب الإعداد", true);
    const body = { niche_id: +nicheSel.value };
    if (trendSel.value) body.trend_signal_id = +trendSel.value;
    act(genBtn, async () => { await api("/content/ideas", { method: "POST", body }); await renderIdeas(); }, "تم توليد الفكرة");
  });

  show(
    el("h2", {}, "فكرة جديدة"),
    el("div", { class: "card" }, genForm),
    el("h2", {}, "الأفكار — راجع وعدّل قبل ما تولّد الفيديو"),
    ideas.length ? ideas.map((i) => ideaCard(i, piecesByIdea[i.id] || 0)) : empty("مفيش أفكار لسه")
  );
}

function ideaCard(idea, pieceCount) {
  const f = {
    title: el("input", { value: idea.title }),
    script: el("textarea", { value: idea.script, rows: 6 }),
    caption: el("textarea", { value: idea.caption, rows: 2 }),
    hashtags: el("input", { value: idea.hashtags }),
  };
  const save = el("button", { class: "btn" }, "حفظ التعديلات");
  save.addEventListener("click", () => act(save, () => api(`/content/ideas/${idea.id}`, {
    method: "PATCH",
    body: { title: f.title.value, script: f.script.value, caption: f.caption.value, hashtags: f.hashtags.value },
  }), "تم الحفظ"));

  const audio = el("input", { type: "checkbox", checked: true });
  const image = el("input", { type: "checkbox", checked: true });
  const video = el("input", { type: "checkbox", checked: true });
  const gen = el("button", { class: "btn primary" }, "ولّد الميديا");
  gen.addEventListener("click", () => act(gen, async () => {
    toast("جاري التوليد… ممكن ياخد دقيقة");
    await api("/content/pieces", { method: "POST", body: { idea_id: idea.id, with_audio: audio.checked, with_image: image.checked, with_video: video.checked } });
    location.hash = "library";
  }, "المحتوى جاهز"));

  const del = el("button", { class: "btn danger" }, "حذف");
  del.addEventListener("click", () => act(del, async () => { await api(`/content/ideas/${idea.id}`, { method: "DELETE" }); await renderIdeas(); }, "تم الحذف"));

  return el("div", { class: "card" },
    el("div", { class: "muted" }, idea.angle),
    el("div", { class: "stack", style: "display:grid;gap:8px;margin-top:8px" },
      field("العنوان", f.title), field("السكريبت", f.script), field("الكابشن", f.caption), field("الهاشتاجات", f.hashtags)),
    el("div", { class: "row between", style: "margin-top:10px" },
      el("div", { class: "row" },
        el("label", { class: "check" }, audio, "صوت"), el("label", { class: "check" }, image, "صورة"), el("label", { class: "check" }, video, "فيديو"),
        gen, save),
      pieceCount ? el("span", { class: "muted" }, `${pieceCount} محتوى مولّد`) : del)
  );
}

// -- Library
async function renderLibrary() {
  const [pieces, ideas, accounts] = await Promise.all([api("/content/pieces"), api("/content/ideas"), api("/accounts")]);
  const titles = Object.fromEntries(ideas.map((i) => [i.id, i.title]));
  const active = accounts.filter((a) => a.is_active);

  show(
    el("h2", {}, "المحتوى الجاهز"),
    pieces.length ? pieces.map((p) => pieceCard(p, titles[p.idea_id], active)) : empty("ولّد ميديا من تبويب الأفكار الأول")
  );
}

function pieceCard(p, title, accounts) {
  const media = el("div", { class: "media" },
    p.video_url && el("video", { src: p.video_url, controls: true, preload: "metadata" }),
    !p.video_url && p.image_url && el("img", { src: p.image_url, alt: title || "" }),
    p.audio_url && el("audio", { src: p.audio_url, controls: true })
  );

  const acc = el("select", {}, accounts.map((a) => el("option", { value: a.id }, `${PLATFORMS[a.platform]} — ${a.display_name || a.id}`)));
  const when = el("input", { type: "datetime-local", value: defaultWhen() });
  const btn = el("button", { class: "btn primary" }, "جدولة");
  btn.addEventListener("click", () => {
    if (!accounts.length) return toast("ضيف حساب من تبويب الإعداد", true);
    if (!when.value) return toast("اختار الموعد", true);
    act(btn, async () => {
      // Sent as a naive local time; the server interprets it in its own timezone.
      await api("/schedule", { method: "POST", body: { content_piece_id: p.id, account_id: +acc.value, scheduled_for: when.value } });
      location.hash = "schedule";
    }, "تمت الجدولة");
  });

  return el("div", { class: "card" },
    el("h3", {}, title || `فكرة #${p.idea_id}`), media,
    el("div", { class: "row" }, acc, when, btn)
  );
}

// -- Schedule
async function renderSchedule() {
  const posts = await api("/schedule");
  posts.sort((a, b) => new Date(b.scheduled_for) - new Date(a.scheduled_for));

  const actions = (p) => {
    if (p.status === "queued") {
      const b = el("button", { class: "btn danger" }, "إلغاء");
      b.addEventListener("click", () => act(b, async () => { await api(`/schedule/${p.id}`, { method: "DELETE" }); await renderSchedule(); }, "تم الإلغاء"));
      return b;
    }
    if (p.status === "failed") {
      const b = el("button", { class: "btn" }, "إعادة المحاولة");
      b.addEventListener("click", () => act(b, async () => { await api(`/schedule/${p.id}/retry`, { method: "POST" }); await renderSchedule(); }, "رجع للطابور"));
      return b;
    }
    return null;
  };

  show(
    el("h2", {}, "الجدولة"),
    posts.length
      ? el("div", { class: "table-wrap" }, el("table", {},
          el("thead", {}, el("tr", {}, ["المنصة", "المحتوى", "الموعد", "الحالة", ""].map((h) => el("th", {}, h)))),
          el("tbody", {}, posts.map((p) => el("tr", {},
            el("td", {}, platChip(p.platform)),
            el("td", {}, p.idea_title || `#${p.content_piece_id}`, p.error_message && el("div", { class: "err" }, p.error_message)),
            el("td", {}, fmtTime(p.scheduled_for)),
            el("td", {}, chip(p.status)),
            el("td", {}, actions(p))
          )))))
      : empty("مفيش منشورات مجدولة")
  );
}

// -- Login
function renderLogin() {
  const pw = el("input", { type: "password", name: "password", required: true, autocomplete: "current-password" });
  const form = el("form", { class: "stack", style: "max-width:340px;margin:40px auto" },
    el("h2", {}, "تسجيل الدخول"), field("كلمة السر", pw), el("button", { class: "btn primary", type: "submit" }, "دخول"));
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    act(e.submitter, async () => { await api("/auth/login", { method: "POST", body: { password: pw.value } }); await route(); });
  });
  show(el("div", { class: "card" }, form));
  pw.focus();
}

// ---------- router ----------
const ROUTES = { overview: renderOverview, setup: renderSetup, trends: renderTrends, ideas: renderIdeas, library: renderLibrary, schedule: renderSchedule };

async function route() {
  const name = ROUTES[location.hash.slice(1)] ? location.hash.slice(1) : "overview";
  document.querySelectorAll("#tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  try {
    await ROUTES[name]();
  } catch (e) {
    if (e instanceof AuthError) return renderLogin();
    show(el("div", { class: "empty" }, "تعذّر الاتصال بالـ API: " + e.message));
  }
}

document.getElementById("tabs").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-tab]");
  if (b) location.hash = b.dataset.tab;
});
window.addEventListener("hashchange", route);

document.getElementById("logout").addEventListener("click", async () => {
  await api("/auth/logout", { method: "POST" });
  location.hash = "";
  route();
});

(async () => {
  try {
    const st = await api("/auth/status");
    document.getElementById("logout").hidden = !st.required;
  } catch (_) { /* older backend without /auth */ }
  try { SERVER_TZ = (await api("/health")).timezone || SERVER_TZ; } catch (_) { /* keep default */ }
  route();
})();
