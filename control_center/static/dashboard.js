(() => {
    'use strict';
    function reveal(target) {
        for (let parent=target; parent; parent=parent.parentElement) if(parent.tagName==='DETAILS') parent.open=true;
        target.scrollIntoView({block:'start',behavior:'smooth'});
    }
    window.revealDashboardTarget=reveal;
    function hashTarget() {const target=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(target)reveal(target);}
    window.addEventListener('hashchange',hashTarget);
    if(location.hash)requestAnimationFrame(hashTarget);
    document.addEventListener('click',event=>{const a=event.target.closest('a[href^="#"]');if(a){const t=document.getElementById(a.getAttribute('href').slice(1));if(t)reveal(t);}});
    const search=document.getElementById('quick-site-search');
    search?.addEventListener('input',()=>document.querySelectorAll('[data-tile-group]').forEach(row=>{row.hidden=!row.textContent.toLowerCase().includes(search.value.trim().toLowerCase());}));
    document.querySelectorAll('.dashboard-video-group').forEach((card,index)=>{
        let section=document.getElementById('video-group-history');
        if(!section){section=document.createElement('details');section.id='video-group-history';section.className='dashboard-disclosure';const label=document.createElement('summary');label.textContent='YouTube · 이전 제작 결과와 실행';section.append(label);document.getElementById('bulk-publish').after(section);}
        section.append(card);
    });
    // One dated report remains the source for both email and dashboard.
    const host=document.getElementById('daily-core-metrics-content');
    const controls=document.createElement('div');controls.className='metrics-controls';
    const filter=document.createElement('input');filter.type='search';filter.placeholder='사이트 이름으로 검색';filter.setAttribute('aria-label','통계 사이트 검색');filter.className='dashboard-search';
    const select=document.createElement('select');select.setAttribute('aria-label','통계 플랫폼 선택');select.className='dashboard-search';
    [['전체','전체'],['WordPress','WP 25'],['Blogspot','Blogspot 33'],['뉴스룸','뉴스룸 2']].forEach(([value,label])=>{const option=document.createElement('option');option.value=value;option.textContent=label;select.append(option);});
    controls.append(select,filter);host.before(controls);
    function applyFilter(){
        host.querySelectorAll('[data-metrics-platform]').forEach(group=>{
            const platform=group.dataset.metricsPlatform;
            group.hidden=select.value!=='전체'&&!platform.includes(select.value);
            group.querySelectorAll('tr').forEach((row,i)=>{
                if(i)[...row.cells].forEach((cell,index)=>{cell.dataset.label=['순위','사이트','오늘 방문(증감)','누적 방문(증감)','총 발행 글(증감)','Google 색인(증감)','확인 필요'][index];});if(i)row.hidden=!row.cells[1]?.textContent.toLowerCase().includes(filter.value.trim().toLowerCase());});
        });
    }
    filter.oninput=applyFilter;select.onchange=applyFilter;
    window.simplifyMetrics=()=>{
        // Wrap each platform without changing values, dates, ranks or email markup.
        [...host.querySelectorAll('h3')].forEach(heading=>{
            if(heading.closest('[data-metrics-platform]'))return;
            const group=document.createElement('section');group.dataset.metricsPlatform=heading.textContent;heading.before(group);
            let node=heading;
            while(node){const next=node.nextElementSibling;group.append(node);if(node.tagName==='DIV'&&node.querySelector('table'))break;if(next?.tagName==='H3')break;node=next;}
            group.querySelectorAll('tr').forEach((row,i)=>{
                if(i)[...row.cells].forEach((cell,index)=>{cell.dataset.label=['순위','사이트','오늘 방문(증감)','누적 방문(증감)','총 발행 글(증감)','Google 색인(증감)','확인 필요'][index];});
                if(i&&row.cells[6]?.textContent){const cell=row.cells[6];const details=document.createElement('details');const label=document.createElement('summary');label.textContent='확인 내역';const text=document.createElement('p');text.textContent=cell.textContent;details.append(label,text);cell.replaceChildren(details);}
            });
        });
        if(!host.querySelector('.metrics-definitions')){
            const notes=[...host.children].filter(node=>node.tagName==='P'&&!node.textContent.startsWith('기준:'));
            if(notes.length){const details=document.createElement('details');details.className='metrics-definitions';const label=document.createElement('summary');label.textContent='증감·조회수·색인 집계 기준';details.append(label,...notes);host.querySelector('h2').after(details);}
        }
        applyFilter();
    };
    window.simplifyMetrics();
})();
