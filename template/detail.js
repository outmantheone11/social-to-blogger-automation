/* ===== صفحة تفاصيل العرض ===== */
(function(){
  var st = document.createElement("style");
  st.textContent = [
    ".dm{position:fixed;inset:0;z-index:100000;background:rgba(6,14,11,.72);backdrop-filter:blur(6px);display:flex;align-items:center;justify-content:center;padding:14px;opacity:0;transition:opacity .25s}",
    ".dm.on{opacity:1}",
    ".dm-box{position:relative;width:min(980px,100%);max-height:calc(100vh - 28px);overflow:auto;background:var(--surface);color:var(--ink);border-radius:22px;border:1px solid var(--line);box-shadow:0 30px 80px -20px rgba(0,0,0,.6);display:grid;grid-template-columns:1fr}",
    "@media (min-width:820px){.dm-box{grid-template-columns:1.15fr .85fr}}",
    ".dm-gal{background:#000;display:flex;flex-direction:column;min-height:240px}",
    ".dm-main{flex:1;position:relative;display:flex;align-items:center;justify-content:center;aspect-ratio:4/3;overflow:hidden}",
    ".dm-main img,.dm-main video{width:100%;height:100%;object-fit:contain}",
    ".dm-main iframe{width:100%;height:100%;border:0}",
    ".dm-thumbs{display:flex;gap:6px;padding:8px;overflow-x:auto;background:#0b1512}",
    ".dm-thumbs button{flex:none;width:64px;height:48px;border-radius:8px;border:2px solid transparent;overflow:hidden;padding:0;background:#222;cursor:pointer;color:#fff}",
    ".dm-thumbs button[aria-current='true']{border-color:var(--gold)}",
    ".dm-thumbs img{width:100%;height:100%;object-fit:cover}",
    ".dm-body{padding:22px;display:flex;flex-direction:column;gap:14px}",
    ".dm-badge{align-self:flex-start;background:var(--gold-soft);color:var(--gold);font-size:12px;font-weight:700;padding:5px 11px;border-radius:999px}",
    ".dm-body h2{font-size:clamp(19px,2.6vw,24px);font-weight:800;line-height:1.35}",
    ".dm-facts{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0}",
    ".dm-facts div{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:10px 12px}",
    ".dm-facts dt{font-size:12px;color:var(--muted)}",
    ".dm-facts dd{margin:2px 0 0;font-weight:700;font-size:14.5px}",
    ".dm-desc{font-size:14.5px;color:var(--muted);white-space:pre-line}",
    ".dm-cta{display:grid;gap:10px;margin-top:auto}",
    ".dm-cta a{min-height:48px;display:flex;align-items:center;justify-content:center;gap:8px;border-radius:999px;font-weight:700;font-size:14.5px;text-decoration:none}",
    ".dm-close{position:absolute;top:10px;inset-inline-end:10px;z-index:3;width:42px;height:42px;border-radius:50%;border:0;background:rgba(10,15,12,.6);color:#fff;font-size:24px;cursor:pointer}",
    ".dm-empty{color:#fff;opacity:.7;padding:30px;text-align:center}",
    "body.dm-lock{overflow:hidden}"
  ].join("");
  document.head.appendChild(st);
})();

var DM = null, DM_ITEMS = [], DM_I = 0, DM_LAST = null;

function dmItems(L){
  var out = [];
  (L.images || []).forEach(function(u){
    var src = fullUrl(u);
    if(src) out.push({k:"img", src:src, thumb:src});
  });
  [L.video_url, L.social_url].forEach(function(u){
    var m = u && parseMedia(u);
    if(!m) return;
    if(m.k === "img") out.push({k:"img", src:m.src, thumb:m.src});
    else if(m.k === "video") out.push({k:"video", src:m.src, thumb:""});
    else out.push({k:m.k, src:m.src, thumb:m.thumb || ""});
  });
  return out;
}

function dmShow(i){
  if(!DM_ITEMS.length) return;
  DM_I = (i + DM_ITEMS.length) % DM_ITEMS.length;
  var it = DM_ITEMS[DM_I], main = DM.querySelector(".dm-main");
  if(it.k === "img") main.innerHTML = '<img alt="" src="' + esc(it.src) + '">';
  else if(it.k === "video") main.innerHTML = '<video controls playsinline src="' + esc(it.src) + '"></video>';
  else main.innerHTML = '<iframe allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen loading="lazy" src="' + esc(it.src) + '"></iframe>';
  DM.querySelectorAll(".dm-thumbs button").forEach(function(b, n){
    b.setAttribute("aria-current", String(n === DM_I));
  });
}

function dmBuild(L){
  DM_ITEMS = dmItems(L);
  var thumbs = DM_ITEMS.map(function(it, n){
    var inner = it.thumb ? '<img alt="" src="' + esc(it.thumb) + '">' : '<span>▶</span>';
    return '<button type="button" data-n="' + n + '" aria-label="عنصر ' + (n + 1) + '">' + inner + '</button>';
  }).join("");
  var facts = [["الموقع", L.location], ["المساحة", L.area], ["السعر", L.price]]
    .filter(function(f){ return f[1]; })
    .map(function(f){ return '<div><dt>' + esc(f[0]) + '</dt><dd>' + esc(f[1]) + '</dd></div>'; })
    .join("");
  var desc = L.desc || L.excerpt || "";
  DM.innerHTML =
    '<div class="dm-box" role="document">' +
      '<button class="dm-close" type="button" aria-label="إغلاق">×</button>' +
      '<div class="dm-gal"><div class="dm-main"></div>' +
        (DM_ITEMS.length > 1 ? '<div class="dm-thumbs">' + thumbs + '</div>' : '') +
      '</div>' +
      '<div class="dm-body">' +
        (L.badge ? '<span class="dm-badge">' + esc(L.badge) + '</span>' : '') +
        '<h2>' + esc(L.title) + '</h2>' +
        '<dl class="dm-facts">' + facts + '</dl>' +
        (desc ? '<p class="dm-desc">' + esc(desc) + '</p>' : '') +
        '<div class="dm-cta">' +
          '<a href="' + esc(waLink(L.wa || L.title)) + '" target="_blank" rel="noopener" style="background:var(--good);color:#fff">تواصل مع إدارة المنصة عبر واتساب</a>' +
          '<a href="tel:+' + esc(CONFIG.whatsappNumber) + '" style="background:var(--gold);color:#241a08">اتصال مباشر</a>' +
          '<a href="' + esc(CONFIG.facebookUrl) + '" target="_blank" rel="noopener" style="border:1px solid var(--line);color:var(--ink)">صفحتنا على فيسبوك</a>' +
        '</div>' +
      '</div>' +
    '</div>';
  dmShow(0);
}

function dmOpen(L){
  if(!DM){
    DM = document.createElement("div");
    DM.className = "dm";
    DM.setAttribute("role", "dialog");
    DM.setAttribute("aria-modal", "true");
    document.body.appendChild(DM);
    DM.addEventListener("click", function(e){
      if(e.target === DM || e.target.closest(".dm-close")) return dmClose();
      var b = e.target.closest(".dm-thumbs button");
      if(b) dmShow(+b.getAttribute("data-n"));
    });
  }
  dmBuild(L);
  DM_LAST = document.activeElement;
  document.body.classList.add("dm-lock");
  requestAnimationFrame(function(){ DM.classList.add("on"); });
  DM.querySelector(".dm-close").focus();
}

function dmClose(){
  if(!DM || !DM.classList.contains("on")) return;
  DM.classList.remove("on");
  DM.innerHTML = "";
  document.body.classList.remove("dm-lock");
  if(DM_LAST && DM_LAST.focus) DM_LAST.focus();
}

document.addEventListener("keydown", function(e){
  if(!DM || !DM.classList.contains("on")) return;
  if(e.key === "Escape") dmClose();
  if(e.key === "ArrowLeft") dmShow(DM_I + 1);
  if(e.key === "ArrowRight") dmShow(DM_I - 1);
});

/* النقر على أي بطاقة يفتح التفاصيل (ويمنع معرض الصور القديم) */
grid.addEventListener("click", function(e){
  var card = e.target.closest && e.target.closest(".card");
  if(!card) return;
  if(e.target.closest("a,button,iframe,video")) return;
  e.stopPropagation();
  var h = card.querySelector("h3");
  var title = h ? h.textContent.trim() : "";
  var L = null;
  for(var i = 0; i < LISTINGS.length; i++){
    if(LISTINGS[i].title === title){ L = LISTINGS[i]; break; }
  }
  if(!L){
    var badge = card.querySelector(".card-badge"), price = card.querySelector(".card-price");
    L = {
      title: title,
      badge: badge ? badge.textContent.trim() : "",
      price: price ? price.textContent.trim() : "",
      wa: "مرحباً، أرغب في تفاصيل: " + title,
      images: [].map.call(card.querySelectorAll("img"), function(im){ return im.getAttribute("src"); }).filter(Boolean)
    };
  }
  dmOpen(L);
}, true);
