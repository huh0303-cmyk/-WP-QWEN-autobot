// Run in an unsplash.com tab via javascript tool, then: await card({...})
window.card=(o)=>{document.documentElement.innerHTML = `<head><meta charset="utf-8"><style>
html,body{margin:0;overflow:hidden;background:#000;cursor:none}
#c{width:100vw;height:100vh;position:relative;overflow:hidden;font-family:'Noto Sans KR','Malgun Gothic',sans-serif;color:#fff}
#c img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.g{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.7) 0%,rgba(0,0,0,.1) 30%,rgba(0,0,0,.25) 50%,rgba(0,0,0,.9) 100%)}
.tag{position:absolute;top:34px;left:34px;background:#e63946;padding:9px 22px;border-radius:30px;font-size:22px;font-weight:800;letter-spacing:1px}
.n{position:absolute;top:30px;right:34px;font-size:40px;font-weight:900;text-shadow:0 2px 10px #000}
.n small{font-size:24px;opacity:.85}
.t{position:absolute;left:34px;right:34px;top:92px;font-size:78px;font-weight:900;line-height:1.1;text-shadow:0 4px 18px #000}
.t2{position:absolute;left:34px;right:34px;top:188px;font-size:28px;font-weight:700;text-shadow:0 3px 12px #000}
.k{position:absolute;left:34px;right:34px;top:600px;font-size:${o.fs||88}px;font-weight:900;text-shadow:0 4px 18px #000;line-height:1.05}
.r{position:absolute;left:34px;top:${o.rt||715}px;font-size:36px;color:#ffd166;font-weight:800;text-shadow:0 2px 10px #000}
.e{position:absolute;left:34px;right:34px;top:${o.et||765}px;font-size:34px;font-weight:600;text-shadow:0 2px 10px #000}
.f{position:absolute;left:34px;bottom:16px;font-size:16px;opacity:.85}
.p{position:absolute;left:34px;right:34px;top:${o.pt||822}px;font-size:${o.pf||22}px;line-height:1.35;color:#fff;background:rgba(0,0,0,.45);border-left:5px solid #ffd166;padding:8px 14px;border-radius:8px;font-weight:600}
.p b{color:#ffd166;margin-right:8px}
</style></head><body><div id="c"><img id="im" src="${o.img}?w=1400&q=80"><div class="g"></div>
<div class="tag">KOREAN SOS · 필수 표현 100</div><div class="n">${o.n}<small>/100</small></div>
<div class="t">한국어 필수 표현</div><div class="t2">한국인이 매일 쓰는 · 무조건 외워야 할 표현</div><div class="k">${o.ko}</div><div class="r">${o.rom}</div><div class="e">= ${o.en}</div>
<div class="p"><b>🔊 따라 읽기 ×5</b>${[1,2,3,4,5].map(i=>i+'. '+o.rom).join('  ')}</div>
<div class="f">KOREAN SOS · @korean_sos1 · Photo: ${o.by} / Unsplash</div></div></body>`; return new Promise(r=>setTimeout(()=>r(document.getElementById('im').naturalWidth),3000))};
// example: await card({img:'https://images.unsplash.com/photo-1765243947068-ff03be6b9894',n:1,ko:'안녕하세요',rom:'annyeonghaseyo',en:'Hello',by:'Albert Sidorov'})
