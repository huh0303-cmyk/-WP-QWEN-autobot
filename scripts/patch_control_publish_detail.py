from pathlib import Path
p=Path(__file__).resolve().parents[1]/'docs'/'index.html'
s=p.read_text(encoding='utf-8')
anchor=" document.addEventListener('click',function(e){var b=e.target.closest('.wp-ops-expand');"
assert anchor in s
patch='''
// Connect every WordPress and Blogspot publish action to its own detail row.
// External publishing is still handled by the existing authorized publisher.
document.addEventListener('click',function(e){
 var link=e.target.closest('a.publish-link');
 if(!link)return;
 var tr=link.closest('tr');if(!tr)return;
 var detail=tr.querySelector('.wp-ops-expand');if(!detail)return;
 var platform=detail.dataset.platform;
 if(platform!=='WordPress'&&platform!=='Blogspot')return;
 var next=tr.nextElementSibling;
 if(!next||!next.classList.contains('wp-ops-detail'))detail.click();
 var row=tr.nextElementSibling;
 if(row&&row.classList.contains('wp-ops-detail')){
  var cell=row.querySelector('td');
  var note=document.createElement('p');note.className='publish-dispatch-note';
  note.style.cssText='border-left:4px solid #2563eb;padding:8px;background:#eff6ff';
  note.textContent='발행 화면을 열었습니다. 실제 실행 접수 및 단계별 성공은 GitHub 실행 로그와 게시 URL로 확인합니다.';
  var old=cell.querySelector('.publish-dispatch-note');if(old)old.remove();
  cell.prepend(note);row.scrollIntoView({behavior:'smooth',block:'nearest'});
 }
 // Existing external publish link opens normally; no fake success is reported.
});
'''
s=s.replace(anchor,patch+anchor,1)
# Keep Blogspot details open and refreshing from evidence, rather than overwriting with WP panel.
s=s.replace("if(c)c.innerHTML=panel(btn.dataset.site)","if(c)c.innerHTML=btn.dataset.platform==='WordPress'?panel(btn.dataset.site):socialPanel(btn.dataset.platform,btn.dataset.account||btn.dataset.site,btn.dataset.site)")
p.write_text(s,encoding='utf-8')
print('patched',p)
