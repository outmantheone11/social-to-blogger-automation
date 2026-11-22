/* app.js — منصة الوساطة العقارية (نسخة كاملة مُصلحة) */
(function(){
"use strict";
function boot(){

var CONFIG = {
  whatsappNumber: "212708565088",
  facebookUrl: "https://www.facebook.com/WassataAkariaTijaria?locale=ar_AR",
  defaultMessage: "مرحباً، أرغب في الاستفسار عن العروض العقارية",
  bloggerFeed: "/feeds/posts/default",
  listingsUrls: [],
  mediaBase: "https://cdn.jsdelivr.net/gh/outmantheone11/social-to-blogger-automation@main/"
};

var LISTINGS = [
 {category:"land",badge:"للبيع · أرض سكنية/تجارية",media:"land",title:"أرض للبيع بمدخل بوسكورة — فرصة ذهبية لعشاق الطبيعة",location:"بوسكورة، النواصر",area:"+10,000 م²",price:"ثمن قابل للتفاوض",wa:"تفاصيل أرض بوسكورة +10000 م²",lat:33.36,lng:-7.58},
 {category:"land",badge:"للبيع · أرض استثمارية",media:"land",title:"فرصة استثمارية استراتيجية بدار بوعزة على الطريق الرئيسية",location:"دار بوعزة، أولاد عزوز",area:"4.8 هكتار",price:"ثمن قابل للتفاوض",wa:"تفاصيل الأرض الاستثمارية دار بوعزة",lat:33.513,lng:-7.678},
 {category:"land",badge:"للبيع · أرض محفظة",media:"land",title:"أرض محفظة مرخصة صالحة للبناء بدوار أمالوا",location:"جماعة الدراركة، أكادير",area:"2,086 م²",price:"ثمن قابل للتفاوض",wa:"تفاصيل أرض محفظة الدراركة",lat:30.33,lng:-9.6},
 {category:"land",badge:"للبيع · أرض سياحية",media:"coast",title:"قطعة أرضية استثنائية بواجهة بحرية مباشرة بآكلو",location:"آكلو، إقليم تيزنيت",area:"17 هكتار",price:"ثمن قابل للتفاوض",wa:"تفاصيل أرض محفظة تزنيت آكلو",lat:29.6,lng:-9.73},
 {category:"residential",badge:"للبيع · شقة فاخرة · مرآب مشمول",media:"res",title:"شقة فاخرة للبيع بحي ابن تاشفين، قرب مرجان",location:"الدار البيضاء",area:"117 م² · 3 غرف + صالونين",price:"ثمن قابل للتفاوض",wa:"تفاصيل الشقة الفاخرة ابن تاشفين",lat:33.56,lng:-7.6},
 {category:"residential",badge:"للبيع · عقار محفظ",media:"res",title:"عقار محفظ بحي مستقبل، طريق رأس الماء بنسودة",location:"فاس",area:"92 م² · 3 غرف + صالونين",price:"ثمن قابل للتفاوض",wa:"تفاصيل عقار بنسودة فاس",lat:34.0331,lng:-4.9998},
 {category:"residential",badge:"للبيع · منزل بحي راقٍ",media:"res",title:"منزل محفظ بحي راقٍ وهادئ ببني ملال",location:"بني ملال",area:"220 م²",price:"ثمن قابل للتفاوض",wa:"تفاصيل منزل محفظ بني ملال",lat:32.3373,lng:-6.3498},
 {category:"residential",badge:"للبيع · شقة",media:"res",title:"شقة للبيع في مراكش - حي جليز",location:"مراكش - حي جليز",area:"95 م²",price:"1,250,000 درهم",wa:"السلام عليكم، أود الحصول على تفاصيل الشقة المعروضة للبيع في حي جليز بمراكش.",lat:31.6335,lng:-7.995},
 {category:"residential",badge:"للبيع · فيلا",media:"res",title:"فيلا فاخرة للبيع في مراكش - النخيل",location:"مراكش - النخيل",area:"400 م²",price:"4,500,000 درهم",wa:"مرحباً، أرغب في الحصول على تفاصيل الفيلا المعروضة للبيع في مراكش - النخيل.",lat:31.648,lng:-7.98},
 {category:"residential",badge:"للبيع · هنغار جديد",media:"res",title:"هنغار جديد مع 8 شقق للبيع في مراكش - طريق اسفي",location:"مراكش - طريق آسفي",area:"2200 متر مربع",price:"1.4 مليار سنتيم",video_url:"https://www.youtube.com/shorts/FSSMCZnt64w",wa:"مرحباً، أرغب في الحصول على تفاصيل الهنغار الجديد مع 8 شقق بطريق آسفي - مراكش",lat:31.58,lng:-8.06}
];

var TESTIMONIALS = [];
if(!TESTIMONIALS.length){ var _ts = document.getElementById("testimonials"); if(_ts) _ts.hidden = true; }

var FAQS = [
 {q:"كيف يتم تقييم وتثمين العقارات الخاصة بي؟",a:"يقوم فريقنا المختص بدراسة القيمة السوقية الحقيقية بناءً على موقع العقار والمساحة والأسعار الأخيرة للمعاملات المنجزة في نفس المنطقة، مع معاينة ميدانية لضمان أفضل سعر."},
 {q:"ما هي نسبة العمولات والرسوم المعتمدة في المنصة؟",a:"نعتمد الشفافية التامة؛ يُتفق على نسبة الوساطة مسبقاً وفق الأعراف العقارية المعمول بها في المغرب، وتُؤدى فقط بعد إتمام عملية البيع وتوقيع العقود."},
 {q:"هل تضمنون الأمان والشرعية القانونية للعقارات المعروضة؟",a:"نحرص على عرض عقارات محفظة أو سليمة قانونياً، ونرافق المشترين والمالكين عبر موثقين معتمدين لحماية حقوق الأطراف."}
];

var ICONS = {
 land:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 20h18M4 20V10l8-6 8 6v10"/><path d="M9 20v-6h6v6"/></svg>',
 coast:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 18c1.5 1.3 3 1.3 4.5 0s3-1.3 4.5 0 3 1.3 4.5 0 3-1.3 4.5 0"/><path d="M2 13c1.5 1.3 3 1.3 4.5 0s3-1.3 4.5 0 3 1.3 4.5 0 3-1.3 4.5 0"/><path d="M12 10V4l4 2"/></svg>',
 res:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V19a1 1 0 0 0 1 1H9.5v-5h5v5H17.5a1 1 0 0 0 1-1v-8.5"/></svg>'
};

function $(id){ return document.getElementById(id); }
function waLink(m){ return "https://wa.me/" + CONFIG.whatsappNumber + "?text=" + encodeURIComponent(m); }

["navWaBtn","heroWaBtn","fabWaBtn","footerWaLink"].forEach(function(id){ var e=$(id); if(e) e.href = waLink(CONFIG.defaultMessage); });
["navFbBtn","footerFbLink","lfFbLink"].forEach(function(id){ var e=$(id); if(e) e.href = CONFIG.facebookUrl; });
if($("fabCallBtn")) $("fabCallBtn").href = "tel:+" + CONFIG.whatsappNumber;

var phoneReadable = "+212 " + CONFIG.whatsappNumber.slice(3, 6) + " " + CONFIG.whatsappNumber.slice(6);
if($("phoneDisplay")) $("phoneDisplay").textContent = phoneReadable;
if($("telLink")) $("telLink").href = "tel:+" + CONFIG.whatsappNumber;
function fallbackCopy(t){ var ta=document.createElement("textarea"); ta.value=t; ta.style.cssText="position:fixed;opacity:0"; document.body.appendChild(ta); ta.select(); try{document.execCommand("copy");}catch(e){} document.body.removeChild(ta); }
if($("copyPhoneBtn")) $("copyPhoneBtn").addEventListener("click", function(){
  var btn=this, old=btn.innerHTML;
  function done(){ btn.innerHTML='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>'; setTimeout(function(){btn.innerHTML=old;},1500); }
  if(navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(phoneReadable).then(done).catch(function(){fallbackCopy(phoneReadable);done();});
  else { fallbackCopy(phoneReadable); done(); }
});

var menuBtn=$("menuBtn"), mobileMenu=$("mobileMenu");
if(menuBtn && mobileMenu){
  menuBtn.addEventListener("click", function(){ var open=mobileMenu.hidden===false; mobileMenu.hidden=open; menuBtn.setAttribute("aria-expanded",String(!open)); });
  mobileMenu.querySelectorAll("a").forEach(function(a){ a.addEventListener("click", function(){ mobileMenu.hidden=true; menuBtn.setAttribute("aria-expanded","false"); }); });
}

var statsDone=false;
function animateStats(){
  if(statsDone) return; statsDone=true;
  document.querySelectorAll(".stat b[data-count]").forEach(function(el){
    var target=parseFloat(el.getAttribute("data-count")), suffix=el.getAttribute("data-suffix")||"", t0=null;
    function step(ts){ if(!t0) t0=ts; var p=Math.min((ts-t0)/1100,1), v=Math.round(target*(1-Math.pow(1-p,3))); el.textContent=v.toLocaleString("ar-MA")+suffix; if(p<1) requestAnimationFrame(step); }
    requestAnimationFrame(step);
  });
}
var statsSec=document.querySelector(".stats");
if("IntersectionObserver" in window && statsSec){ new IntersectionObserver(function(es){ es.forEach(function(e){ if(e.isIntersecting) animateStats(); }); },{threshold:.4}).observe(statsSec); }
else animateStats();

var grid = document.getElementById("listingsGrid");
(function(){
  var st = document.createElement("style");
  st.textContent = [
    "#listingsGrid{align-items:stretch}",
    ".card{height:100%;transition:transform .15s,box-shadow .15s}",
    ".card:hover{transform:translateY(-3px);box-shadow:0 14px 30px -14px rgba(0,0,0,.35)}",
    ".card-media.has-media{aspect-ratio:4/3;min-height:0}",
    ".card-media img.cover[data-z]{cursor:zoom-in}",
    ".card-body h3{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.5em}",
    ".card-ex{font-size:13px;color:var(--muted);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}",
    ".count-badge{position:absolute;bottom:10px;inset-inline-end:10px;z-index:5;background:rgba(10,15,12,.68);color:#fff;font-size:11px;padding:4px 9px;border-radius:999px}",
    ".lb{position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.92);display:flex;align-items:center;justify-content:center}",
    ".lb img{max-width:94vw;max-height:84vh;object-fit:contain}",
    ".lb button{position:absolute;background:rgba(255,255,255,.18);color:#fff;border:0;width:44px;height:44px;border-radius:50%;font-size:24px;cursor:pointer}"
  ].join("");
  document.head.appendChild(st);
})();
/* معرض الصور: النقر على صورة الغلاف */
grid.addEventListener("click", function(e){
  var im = e.target.closest("img.cover");
  if(!im) return;
  var box = im.closest(".card-media"), raw = box && box.getAttribute("data-gal");
  if(!raw) return;
  var g; try{ g = JSON.parse(raw); }catch(x){ return; }
  var i = Math.max(0, g.indexOf(im.getAttribute("src")));
  var lb = document.createElement("div");
  lb.className = "lb"; lb.dir = "ltr";
  lb.innerHTML = '<img alt=""><button data-d="-1" style="left:14px;top:50%">‹</button><button data-d="1" style="right:14px;top:50%">›</button><button data-d="0" style="right:14px;top:14px">×</button>';
  function show(){ lb.querySelector("img").src = g[i]; }
  lb.addEventListener("click", function(ev){
    var d = ev.target.getAttribute ? ev.target.getAttribute("data-d") : null;
    if(d === null){ if(ev.target === lb) lb.remove(); return; }
    d = +d; if(d === 0){ lb.remove(); return; }
    i = (i + d + g.length) % g.length; show();
  });
  document.body.appendChild(lb); show();
});

/* CSS صغير يُحقن تلقائياً */
(function(){
  var st = document.createElement("style");
  st.textContent = ".card-media.has-media{position:relative;aspect-ratio:16/10;min-height:210px;overflow:hidden;background:#000}" +
    ".card-media.has-media>svg{position:absolute;inset:0;margin:auto}" +
    ".empty-note{grid-column:1/-1;text-align:center;color:var(--muted);padding:30px 0}";
  document.head.appendChild(st);
})();

function esc(s){
  return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
  });
}

/* يقبل رابطاً كاملاً أو مساراً نسبياً (يُضاف له mediaBase — صور مخزنة في GitHub) */
function fullUrl(u){
  u = String(u || "").trim();
  if(!u) return "";
  if(/^https?:\/\//i.test(u)) return u;
  if(/^[\w\-\/.%]+\.(jpe?g|png|webp|gif|mp4|webm)$/i.test(u)) return (CONFIG.mediaBase || "") + u.replace(/^\.?\//, "");
  return "";
}

/* تحديد نوع الرابط: يوتيوب / إنستغرام / فيسبوك / فيديو مباشر / صورة */
function parseMedia(raw){
  var u = fullUrl(raw), m;
  if(!u) return null;
  if((m = u.match(/(?:youtube\.com\/(?:watch\?(?:[^#]*&)?v=|shorts\/|embed\/|live\/)|youtu\.be\/)([\w-]{11})/)))
    return {k:"yt", src:"https://www.youtube-nocookie.com/embed/" + m[1] + "?autoplay=1&rel=0&playsinline=1",
            thumb:"https://img.youtube.com/vi/" + m[1] + "/hqdefault.jpg"};
  if((m = u.match(/instagram\.com\/(?:[\w.]+\/)?(p|reel|reels|tv)\/([\w-]+)/)))
    return {k:"ig", src:"https://www.instagram.com/" + (m[1] === "reels" ? "reel" : m[1]) + "/" + m[2] + "/embed/"};
  if(/facebook\.com\/plugins\//i.test(u)) return {k:"fb", src:u};   /* iframe جاهز من فيسبوك */
  if(/(^|\.)(facebook|fb)\.com\/|fb\.watch\//i.test(u) && !/\.(jpe?g|png|webp|gif)(\?|$)/i.test(u)){
    var isVid = /\/(videos|reel|reels|watch)\b|fb\.watch|[?&]v=/i.test(u);
    return {k:"fb", src:"https://www.facebook.com/plugins/" + (isVid ? "video" : "post") + ".php?show_text=false&href=" + encodeURIComponent(u)};
  }
  if(/\.(mp4|webm|mov)(\?|$)/i.test(u)) return {k:"video", src:u};
  return {k:"img", src:u};
}

/* توحيد شكل العرض (يقبل أسماء حقول متعددة قادمة من الأتمتة) */
function norm(it){
  var c = String(it.category || it.type || "").toLowerCase();
  var cat = (c === "residential" || /سكن|شقة|فيلا|منزل|apart|villa|house|riad|رياض/.test(c)) ? "residential" : "land";
  var icon = ICONS[it.icon] ? it.icon : (ICONS[it.media] ? it.media : (cat === "residential" ? "res" : "land"));
  var title = it.title || it.name || it.titre || "عرض عقاري";
  var urls = [].concat(it.images || [], it.image_url, it.image, it.img, it.video_url, it.video,
                       it.social_url, it.post_url, it.facebook_url, it.instagram_url, it.youtube_url, it.url)
               .filter(function(x){ return x; });
  var medias = urls.map(parseMedia).filter(Boolean);
  return {
    category:cat, icon:icon, title:title,
    badge: it.badge || (cat === "residential" ? "للبيع · عقار سكني" : "للبيع · أرض"),
    location: it.location || it.city || it.ville || "المغرب",
    area: it.area || it.surface || "",
    price: it.price || it.prix || "ثمن قابل للتفاوض",
    wa: it.wa || ("مرحباً، أرغب في تفاصيل: " + title),
    medias: medias,
    link: it.post_link || "", excerpt: it.excerpt || "", gal: medias.filter(function(m){ return m.k === "img"; }).map(function(m){ return m.src; }),
    off: it.hidden === true || it.active === false || it.sold === true
  };
}

function cardHTML(it){
  var player = null, poster = "";
  it.medias.forEach(function(m){
    if(m.k === "img" && !poster) poster = m.src;
    else if(m.k !== "img" && !player) player = m;
  });
  if(!poster && player && player.thumb) poster = player.thumb;

  var inner = ICONS[it.icon] || "";
  if(poster) inner += '<img class="cover" data-z="1" src="' + esc(poster) + '" alt="' + esc(it.title) + '" loading="lazy" referrerpolicy="no-referrer" ' +
    'onerror="this.remove()" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:2">';
  if(player){
    var bg = {yt:"#ff0000", ig:"linear-gradient(45deg,#f09433,#dc2743,#bc1888)", fb:"#1877f2", video:"#1f7a52"}[player.k];
    inner += '<button type="button" class="play" data-k="' + player.k + '" data-src="' + esc(player.src) + '" aria-label="تشغيل" ' +
      'style="position:absolute;inset:0;z-index:3;width:100%;border:0;padding:0;background:rgba(0,0,0,.28);display:flex;align-items:center;justify-content:center">' +
      '<span style="width:54px;height:54px;border-radius:50%;background:' + bg + ';display:flex;align-items:center;justify-content:center;box-shadow:0 4px 14px rgba(0,0,0,.45)">' +
      '<svg viewBox="0 0 24 24" fill="#fff" style="width:24px;height:24px;position:static;filter:none"><path d="M8 5v14l11-7z"/></svg></span></button>';
  }
  var has = (poster || player) ? " has-media" : "";

  return '<article class="card" data-cat="' + it.category + '">' +
    '<div class="card-media is-' + it.icon + has + '"' + (it.gal.length ? ' data-gal="' + esc(JSON.stringify(it.gal)) + '"' : "") + '>' +
      '<span class="card-badge' + (it.icon === "coast" ? " gold" : "") + '" style="z-index:5">' + esc(it.badge) + '</span>' + (it.gal.length > 1 ? '<span class="count-badge">' + it.gal.length + ' صور</span>' : "") + inner +
    '</div>' +
    '<div class="card-body"><h3>' + esc(it.title) + '</h3>' +
      '<div class="card-meta">' +
        '<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>' + esc(it.location) + '</span>' +
        (it.area ? '<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"/></svg>' + esc(it.area) + '</span>' : "") +
      '</div>' +
      (it.excerpt ? '<p class="card-ex">' + esc(it.excerpt) + '</p>' : "") + '<p class="card-price">' + esc(it.price) + '</p>' +
      (it.link ? '<a class="btn btn-ghost btn-block" href="' + esc(it.link) + '">قراءة التفاصيل</a>' : '') +
      '<a class="btn btn-ghost btn-block wa-item" href="' + waLink(it.wa) + '" target="_blank" rel="noopener">طلب التفاصيل والمعاينة</a>' +
    '</div></article>';
}

/* تشغيل الفيديو عند النقر فقط (أسرع للصفحة وأخف على الهاتف) */
grid.addEventListener("click", function(e){
  var b = e.target.closest(".play");
  if(!b) return;
  var box = b.closest(".card-media"), k = b.getAttribute("data-k"), s = esc(b.getAttribute("data-src")), h;
  if(k === "video"){
    h = '<video src="' + s + '" controls autoplay playsinline style="position:absolute;inset:0;width:100%;height:100%;object-fit:contain;z-index:4;background:#000"></video>';
  } else {
    h = '<iframe src="' + s + '" allow="autoplay; encrypted-media; picture-in-picture; clipboard-write; web-share" allowfullscreen ' +
        'style="position:absolute;inset:0;width:100%;height:100%;border:0;z-index:4;background:#fff"></iframe>';
    if(k !== "yt") box.style.minHeight = "480px";   // منشورات فيسبوك/إنستغرام أطول
  }
  box.insertAdjacentHTML("beforeend", h);
  b.remove();
});

/* ===== تنسيق الصفحة داخل قالب بلوجر + تصحيح النصوص ===== */
(function(){
  if(!document.querySelector(".page")) return;
  document.body.classList.add("landing-page");
  var P = "body.landing-page ";
  var hide = ["#navbar",".header-outer",".tabs-outer",".column-right-outer",".column-left-outer",".fauxcolumn-right-outer",".fauxcolumn-left-outer",".body-fauxcolumns",".sidebar",".widget.Header",".widget.BlogSearch",".widget.PageList",".widget.PopularPosts",".widget.Profile",".widget.BlogArchive",".widget.ReportAbuse",".widget.Attribution",".footer-outer",".post-header",".post-title",".post-footer",".post-share-buttons",".comments",".blog-pager",".date-header",".breadcrumbs"];
  var full = [".content-outer",".content-inner",".main-inner",".main-inner .columns",".column-center-outer",".column-center-inner",".region-inner",".widget.Blog",".blog-posts",".post-outer",".post",".post-body",".post-body-container"];
  var css = hide.map(function(x){ return P + x; }).join(",") + "{display:none!important}" +
    full.map(function(x){ return P + x; }).join(",") + "{max-width:none!important;width:100%!important;margin:0!important;padding:0!important;border:0!important;box-shadow:none!important;background:transparent!important}" +
    P + "{background:var(--bg)!important;overflow-x:hidden;margin:0}" +
    P + ".page{font-family:var(--font-body);font-size:16px;line-height:1.6;color:var(--ink);text-align:right}" +
    P + ".page a:not(.btn){color:inherit;text-decoration:none}" +
    P + ".page .btn-primary,body.landing-page .page .btn-fb{color:#fff!important}" +
    P + ".page .btn-gold{color:#241a08!important}" +
    P + ".page .btn-ghost:not([style]){color:var(--ink)}" +
    ".card-media:not(.has-media){aspect-ratio:16/5;min-height:0}" +
    ".card-media:not(.has-media)>svg{width:34px;height:34px}";
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  /* تصحيح النصوص الإنجليزية الشاذة (بقايا الترجمة التلقائية) */
  var exact = {"The strange questions":"الأسئلة الشائعة","details":"عرض عقاري","Current offers":"العروض الحالية","The full name":"الاسم الكامل","or":"أو","More than 5M":"أكثر من 5 ملايين","500,000":"أقل من 500,000"};
  var w = document.createTreeWalker(document.querySelector(".page"), NodeFilter.SHOW_TEXT), n, list = [];
  while((n = w.nextNode())) list.push(n);
  list.forEach(function(t){
    var v = t.nodeValue, k = v.trim(), pr = t.parentNode;
    if(exact[k]){ t.nodeValue = v.replace(k, exact[k]); return; }
    if(v.indexOf("Remove the water from the water") < 0) return;
    if(pr.closest(".feature-card")) t.nodeValue = v.replace("Remove the water from the water", "نوفر فرصاً استثمارية مختارة");
    else if(pr.closest(".calc-note")) t.nodeValue = "القسط المعروض تقديري ويختلف حسب شروط البنك ومدة التمويل.";
    else if(pr.closest(".contact-side")) t.nodeValue = "راسلنا عبر واتساب أو اتصل بنا مباشرة وسنرد عليك في أقرب وقت.";
  });
})();

function applyFilter(){
  var b = document.querySelector('.filter-btn[aria-pressed="true"]');
  var f = b ? b.getAttribute("data-filter") : "all";
  grid.querySelectorAll(".card").forEach(function(c){
    c.hidden = !(f === "all" || c.getAttribute("data-cat") === f);
  });
}

function render(items){
  items = items.filter(function(x){ return !x.off; }).sort(function(a, b){ return (b.medias.length ? 1 : 0) - (a.medias.length ? 1 : 0); });
  grid.innerHTML = items.length ? items.map(cardHTML).join("") : '<p class="empty-note">لا توجد عروض حالياً، تواصل معنا عبر واتساب.</p>';
  applyFilter();
}

/* جلب JSON من GitHub (raw أولاً ثم jsDelivr) مع كسر الكاش كل دقيقة */
function loadGithub(){
  var urls = CONFIG.listingsUrls || [];
  var bust = Math.floor(Date.now() / 60000);
  function attempt(i){
    if(i >= urls.length) return Promise.resolve([]);
    var u = urls[i] + (urls[i].indexOf("?") > -1 ? "&" : "?") + "t=" + bust;
    return fetch(u, {cache:"no-store"})
      .then(function(r){ if(!r.ok) throw new Error(r.status); return r.json(); })
      .then(function(d){ return Array.isArray(d) ? d : (d.listings || d.items || d.data || []); })
      .catch(function(){ return attempt(i + 1); });
  }
  return attempt(0);
}

/* 1) عرض فوري للعروض الثابتة  2) ثم دمج عروض GitHub في الأعلى */
/* منشورات بلوجر (تنشرها الأتمتة) — نفس النطاق فلا مشاكل CORS */
function fromEntry(e){
  var html = (e.content && e.content.$t) || (e.summary && e.summary.$t) || "";
  var doc = new DOMParser().parseFromString(html, "text/html");
  var imgs = [].map.call(doc.querySelectorAll("img"), function(i){ return i.getAttribute("src"); });
  var embeds = [].map.call(doc.querySelectorAll("iframe,video source,video,a[href]"), function(n){ return n.getAttribute("src") || n.getAttribute("href"); })
    .filter(function(u){ return u && /youtu|facebook\.com\/\S*(videos|reel|watch)|fb\.watch|instagram\.com|\.(mp4|webm)(\?|$)/i.test(u); });
  var text = (doc.body.textContent || "").replace(/\s+/g, " ");
  var title = ((e.title && e.title.$t) || "").replace(/[*#_`]/g, "").trim();
  var labels = (e.category || []).map(function(c){ return c.term; }).join(" ");
  var link = ""; (e.link || []).forEach(function(l){ if(l.rel === "alternate") link = l.href; });
  var area = text.match(/(\d[\d.,]*)\s*(م²|م2|متر|هكتار)/); var loc = text.match(/(?:بمنطقة|منطقة|بحي|بمدينة|مدينة)\s+([\u0600-\u06FF]+)/) || title.match(/\s(?:في|ب)\s*([\u0600-\u06FF]+)\s*$/);
  var price = text.match(/(\d[\d.,\s]*)\s*(درهم|DH|MAD|مليون|سنتيم)/i);
  var p1 = doc.querySelector("p"), fbp = [].map.call(doc.querySelectorAll("a[href]"), function(n){ return n.getAttribute("href"); }).filter(function(u){ return /facebook\.com/.test(u); })[0];
  return { title:title, category:labels + " " + title, images:imgs, social_url:embeds[0] || (imgs.length ? "" : fbp), video_url:embeds[1], excerpt: p1 ? p1.textContent.trim().slice(0, 160) : "",
           area: area ? area[1] + (area[2] === "هكتار" ? " هكتار" : " م²") : "", location: loc ? loc[1] : "", price: price ? price[0].trim() : "", post_link:link };
}
function loadBlogger(){
  if(!CONFIG.bloggerFeed) return Promise.resolve([]);
  return fetch(CONFIG.bloggerFeed + "?alt=json&max-results=50", {cache:"no-store"})
    .then(function(r){ return r.json(); })
    .then(function(d){ return ((d.feed && d.feed.entry) || []).map(fromEntry); })
    .catch(function(){ return []; });
}
function loadRemote(){
  return Promise.all([loadBlogger(), loadGithub()]).then(function(r){ return r[0].concat(r[1]); });
}

var staticItems = LISTINGS.map(norm);
render(staticItems);
loadRemote().then(function(remote){
  if(!remote.length) return;
  var seen = {}, all = remote.map(norm).concat(staticItems).filter(function(x){
    var key = x.title.trim().toLowerCase();
    if(seen[key]) return false;
    return (seen[key] = true);
  });
  render(all);
});

var filterBtns = document.querySelectorAll(".filter-btn");
filterBtns.forEach(function(btn){
  btn.addEventListener("click", function(){
    filterBtns.forEach(function(b){ b.setAttribute("aria-pressed","false"); });
    btn.setAttribute("aria-pressed","true");
    applyFilter();
  });
});

var stars="";
for(var si=0;si<5;si++) stars+='<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.9 6.6L22 9.3l-5 4.9L18.2 22 12 18.3 5.8 22 7 14.2l-5-4.9 7.1-.7z"/></svg>';
if($("testiGrid")) $("testiGrid").innerHTML = TESTIMONIALS.map(function(t){
  return '<div class="testi-card"><div class="stars">'+stars+'</div><p class="quote">«'+esc(t.text)+'»</p><div class="testi-who"><span class="testi-avatar">'+esc(t.initial)+'</span><div><b>'+esc(t.name)+'</b><span>'+esc(t.role)+'</span></div></div></div>';
}).join("");
if($("faqList")) $("faqList").innerHTML = FAQS.map(function(f,i){
  return '<details class="faq"'+(i===0?" open":"")+'><summary>'+esc(f.q)+'<span class="faq-plus"></span></summary><div class="faq-a">'+esc(f.a)+'</div></details>';
}).join("");

var rPrice=$("rPrice"), rDown=$("rDown"), rRate=$("rRate"), rYears=$("rYears");
function fmt(n){ return Math.round(n).toLocaleString("ar-MA"); }
function computeLoan(){
  var price=parseFloat(rPrice.value), down=Math.min(parseFloat(rDown.value),price), rate=parseFloat(rRate.value), years=parseFloat(rYears.value);
  $("vPrice").textContent=fmt(price); $("vDown").textContent=fmt(down); $("vRate").textContent=rate.toFixed(1)+"%"; $("vYears").textContent=years;
  var loan=Math.max(price-down,0), mr=rate/1200, n=years*12, m;
  if(mr===0) m=loan/n; else { var f=Math.pow(1+mr,n); m=loan*(mr*f)/(f-1); }
  if(!isFinite(m)||loan<=0) m=0;
  $("calcMonthly").innerHTML=fmt(m)+"<small>درهم / شهر</small>";
  $("calcLoan").textContent=fmt(loan)+" د.م.";
  $("calcInterest").textContent=fmt(Math.max(m*n-loan,0))+" د.م.";
}
if(rPrice){ [rPrice,rDown,rRate,rYears].forEach(function(el){ el.addEventListener("input",computeLoan); }); computeLoan(); }

var cf={name:$("cfName"),phone:$("cfPhone"),purpose:$("cfPurpose"),type:$("cfType"),details:$("cfDetails")}, cfSubmit=$("cfSubmit");
function updateContactLink(){
  cfSubmit.href = waLink("طلب جديد من الموقع:\nالاسم: "+(cf.name.value||"—")+"\nالهاتف: "+(cf.phone.value||"—")+"\nالغرض: "+cf.purpose.value+"\nنوع العقار: "+cf.type.value+"\nالتفاصيل: "+(cf.details.value||"—"));
}
if(cfSubmit){
  Object.keys(cf).forEach(function(k){ cf[k].addEventListener("input",updateContactLink); cf[k].addEventListener("change",updateContactLink); });
  updateContactLink();
  $("contactForm").addEventListener("submit",function(e){ e.preventDefault(); });
}
if($("yearNow")) $("yearNow").textContent=new Date().getFullYear();

}
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
var _gridEl = document.getElementById("listingsGrid");
if(_gridEl) _gridEl.addEventListener("click", function(e){
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


/* خريطة العروض (Leaflet + OpenStreetMap) */
(function(){
  function loadLeaflet(cb){
    if(window.L) return cb();
    var css=document.createElement("link"); css.rel="stylesheet";
    css.href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"; document.head.appendChild(css);
    var js=document.createElement("script"); js.src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    js.onload=cb; document.head.appendChild(js);
  }
  function init(){
    var sec=document.getElementById("listings");
    if(!sec || !window.L || !window.LISTINGS) return;
    var host=document.createElement("div");
    host.id="listingsMap";
    host.style.cssText="height:380px;border-radius:18px;margin:0 0 22px;border:1px solid var(--line);position:relative;z-index:1";
    var wrap=sec.querySelector(".wrap")||sec;
    var g=document.getElementById("listingsGrid");
    wrap.insertBefore(host, g || null);
    var map=L.map(host).setView([31.8,-7.1],6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:18,attribution:"&copy; OpenStreetMap"}).addTo(map);
    LISTINGS.forEach(function(l){
      if(typeof l.lat!=="number" || typeof l.lng!=="number") return;
      var m=L.marker([l.lat,l.lng]).addTo(map);
      m.bindPopup("<b>"+esc(l.title)+"</b><br>"+esc(l.location||""));
      m.on("dblclick",function(){ if(typeof dmOpen==="function") dmOpen(l); });
    });
  }
  loadLeaflet(function(){ if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",init); else init(); });
})();

if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",boot); else boot();
})();
