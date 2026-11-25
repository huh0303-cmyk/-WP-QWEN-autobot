// Run in an unsplash.com tab via the javascript tool, then: await cardX('en'|'ja'|'zh', {img,n,ex,rd,ko,by,fs,rt,et,pt,pf})
// Output is a 4:5 card (Instagram-safe). Resize the window first so innerWidth/innerHeight = 0.8.
window.LANGS={
 en:{title:'영어 필수 표현',sub:'원어민이 매일 쓰는 · 무조건 외워야 할 표현',tag:'ENGLISH SOS · 필수 표현 100',handle:'@english_sos1',foot:'ENGLISH SOS',font:"'Noto Sans KR','Malgun Gothic',sans-serif"},
 ja:{title:'일본어 필수 표현',sub:'일본인이 매일 쓰는 · 무조건 외워야 할 표현',tag:'JAPANESE SOS · 필수 표현 100',handle:'@japanese_sos1',foot:'JAPANESE SOS',font:"'Noto Sans JP','Noto Sans KR','Yu Gothic','Malgun Gothic',sans-serif"},
 zh:{title:'중국어 필수 표현',sub:'중국인이 매일 쓰는 · 무조건 외워야 할 표현',tag:'CHINESE SOS · 필수 표현 100',handle:'@chinese.sos1',foot:'CHINESE SOS',font:"'Noto Sans SC','Noto Sans KR','Microsoft YaHei','Malgun Gothic',sans-serif"}
};
window.cardX=(lang,o)=>{const L=LANGS[lang];document.documentElement.innerHTML = `<head><meta charset="utf-8"><style>
html,body{margin:0;overflow:hidden;background:#000;cursor:none}
#c{width:780px;height:975px;position:absolute;left:0;top:0;transform-origin:0 0;overflow:hidden;font-family:${L.font};color:#fff}
#c img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.g{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.7) 0%,rgba(0,0,0,.1) 30%,rgba(0,0,0,.25) 50%,rgba(0,0,0,.9) 100%)}
.tag{position:absolute;top:34px;left:34px;background:#e63946;padding:9px 22px;border-radius:30px;font-size:22px;font-weight:800;letter-spacing:1px}
.n{position:absolute;top:30px;right:34px;font-size:40px;font-weight:900;text-shadow:0 2px 10px #000}
.n small{font-size:24px;opacity:.85}
.t{position:absolute;left:34px;right:34px;top:92px;font-size:78px;font-weight:900;line-height:1.1;text-shadow:0 4px 18px #000}
.t2{position:absolute;left:34px;right:34px;top:188px;font-size:28px;font-weight:700;text-shadow:0 3px 12px #000}
.k{position:absolute;left:34px;right:34px;top:${o.kt||580}px;font-size:${o.fs||80}px;font-weight:900;text-shadow:0 4px 18px #000;line-height:1.05}
.r{position:absolute;left:34px;right:34px;top:${o.rt||700}px;font-size:36px;color:#ffd166;font-weight:800;text-shadow:0 2px 10px #000}
.e{position:absolute;left:34px;right:34px;top:${o.et||750}px;font-size:34px;font-weight:600;text-shadow:0 2px 10px #000}
.f{position:absolute;left:34px;bottom:16px;font-size:16px;opacity:.85}
.p{position:absolute;left:34px;right:34px;top:${o.pt||808}px;font-size:${o.pf||22}px;line-height:1.35;color:#fff;background:rgba(0,0,0,.45);border-left:5px solid #ffd166;padding:8px 14px;border-radius:8px;font-weight:600}
.p b{color:#ffd166;margin-right:8px}
</style></head><body><div id="c"><img id="im" src="${o.img}?w=1400&q=80"><div class="g"></div>
<div class="tag">${L.tag}</div><div class="n">${o.n}<small>/100</small></div>
<div class="t">${L.title}</div><div class="t2">${L.sub}</div><div class="k">${o.ex}</div><div class="r">${o.rd}</div><div class="e">= ${o.ko}</div>
<div class="p"><b>🔊 따라 읽기 ×5</b>${[1,2,3,4,5].map(i=>i+'. '+o.rd).join('  ')}</div>
<div class="f">${L.foot} · ${L.handle} · Photo: ${o.by} / Unsplash</div></div></body>`;
 const c=document.getElementById('c');c.style.transform='scale('+Math.min(innerWidth/780,innerHeight/975)+')';
 return new Promise(r=>setTimeout(()=>r({w:document.getElementById('im').naturalWidth,ratio:(innerWidth/innerHeight).toFixed(3)}),3000))};
// example: await cardX('ja',{img:'https://images.unsplash.com/photo-XXXX',n:1,ex:'こんにちは',rd:'konnichiwa',ko:'안녕하세요',by:'Name'})
