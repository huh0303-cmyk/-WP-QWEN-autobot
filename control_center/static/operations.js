(() => {
    'use strict';
    const serverData = (() => {
        try { return JSON.parse(document.getElementById('ceo-board-data')?.textContent || '{}'); }
        catch (_) { return {}; }
    })();
    const groups = new Set(['wp25', 'news2', 'blogspot33', 'tistory5']);
    const managed = group => groups.has(group) || /^(wp_|blogspot_|tistory_)/.test(group);
    const labels = {accepted:'요청 접수',dispatching:'요청 접수',queued:'요청 접수',working:'작업 중',review_ready:'검토 준비',publishing:'게시 중',published:'게시 완료',stopped:'중단',failed:'실패',attention:'확인 필요'};
    const terminal = new Set(['published','stopped','failed']);
    const el = (tag, text, cls) => { const node = document.createElement(tag); if (text) node.textContent = text; if (cls) node.className = cls; return node; };
    const time = value => value ? new Date(value * 1000).toLocaleString('ko-KR', {timeZone:'Asia/Seoul',hour12:false}) + ' KST' : '확인 대기';
    function link(text, href) {
        if (!/^https:\/\//.test(href) && !/^\/review\/tistory\//.test(href)) return el('span', text);
        const node = el('a', text, 'operation-action'); node.href = href;
        if (href.startsWith('https:')) {node.target = '_blank'; node.rel = 'noopener noreferrer';}
        return node;
    }
    const summary = el('section', '', 'operation-summary'); summary.id = 'operation-summary'; summary.tabIndex = -1;
    summary.append(el('h2','지금 확인할 작업'), el('p','사이트별 최근 요청 기준입니다. 게시 완료는 오늘 발행량이 아닙니다. 상태를 누르면 해당 작업만 보입니다.'));
    const connection = el('p','운영 기록 연결 중…'); connection.setAttribute('role','status'); summary.append(connection);
    const news = el('p', '뉴스룸 RSS 감시 기록 확인 중…'); summary.append(news);
    const feeds = el('details');feeds.append(el('summary','매체별 RSS 연결 상태'));const feedBody=el('div');feeds.append(feedBody);summary.append(feeds);
    const totals = el('div', '', 'operation-totals'); summary.append(totals);
    const history = el('details'); history.append(el('summary','최근 요청 이력 보기')); const historyBody = el('div'); history.append(historyBody); summary.append(history);
    const anchor = document.getElementById('publish-all-button'); document.getElementById('publish-everything').before(summary);
    if (!summary.isConnected) anchor.parentElement.before(summary);
    const notice = el('div', '', 'operation-notice'); notice.hidden = true; notice.setAttribute('role','status'); summary.prepend(notice);
    let lastJobs = [], polling = false, selectedPhase = 'needs-action';
    const focused = el('div'); focused.id='operation-focus'; summary.append(focused);
    const focusLabel=el('h3','진행·검토·문제 항목');focused.append(focusLabel);
    const focusList=el('div');focused.append(focusList);
    let currentJobs=[];
    const normalize=job=>['dispatching','queued'].includes(job.phase)?'accepted':job.phase;
    function filterJobs(){
        focusLabel.textContent=selectedPhase==='needs-action'?'진행·검토·문제 항목':labels[selectedPhase]+' · 최근 요청';
        const jobs=currentJobs.filter(job=>selectedPhase==='needs-action'?job.phase!=='published':normalize(job)===selectedPhase);
        refreshList(focusList,jobs);
        if(!jobs.length)focusList.replaceChildren(el('p','해당 상태의 작업 기록이 없습니다.'));
        totals.querySelectorAll('button').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.phase===selectedPhase)));
    }

    function showNotice(text, target, failed=false) {
        notice.hidden = false; notice.replaceChildren(el('p',text)); notice.dataset.error = String(failed);
        if (target) {
            const jump = el('a',target.startsWith('bulk-status-tistory') ? '검토본 실시간 보기' : '작업 상태 바로 보기','operation-action');
            jump.href = '#' + target;
            jump.onclick = event => {event.preventDefault(); jumpTo(target);}; notice.append(jump);
        }
        if (failed) {const refresh = el('button','화면 새로고침','operation-action'); refresh.onclick=()=>location.reload(); notice.append(refresh);}
    }
    function jumpTo(id) {
        const target = document.getElementById(id); if (!target) return;
        window.revealDashboardTarget?.(target); target.tabIndex=-1; target.scrollIntoView({block:'center',behavior:'smooth'}); target.focus({preventScroll:true});
    }
    function card(job) {
        const row = el('div','','operation-row'); row.dataset.phase=job.phase;
        row.dataset.operationId=job.id;
        row.append(el('strong',job.label + ' · ' + labels[job.phase]), el('p',job.detail));
        row.append(el('small',(job.source === 'rss' ? 'RSS 새 기사 자동 실행' : job.source === 'schedule' ? '이전 예약 실행' : '수동 요청') + ' · 접수 ' + time(job.created_at)));
        row.append(el('small','마지막 상태 확인 ' + time(job.checked_at)));
        if (job.connection_warning || (job.checked_at && Date.now()/1000-job.checked_at>120 && !terminal.has(job.phase))) row.append(el('p',job.connection_warning || '상태 확인 지연 · 마지막으로 확인된 상태입니다.','operation-warning'));
        const actions = el('div','','operation-actions');
        if (job.review_url && job.phase === 'review_ready') actions.append(link('검토본 확인 → 승인·게시',job.review_url));
        if (job.public_url) actions.append(link('게시된 글 확인',job.public_url));
        if (job.run_url) actions.append(link('실행 기록',job.run_url));
        row.append(actions);
        const details = el('details'); details.append(el('summary','진행 이력 · 요청 ' + job.id.slice(0,8)));
        (job.history || []).forEach(event=>details.append(el('p',time(event.at) + ' · ' + labels[event.phase] + ' · ' + event.detail)));
        (job.milestones || []).forEach(event=>details.append(el('p',time(event.at) + ' · 실행 서버 확인: ' + labels[event.phase] + ' · ' + event.detail)));
        row.append(details); return row;
    }
    function refreshList(list,jobs) {
        if(list.contains(document.activeElement)) return;
        const opened=new Set([...list.querySelectorAll('.operation-row')].filter(row=>row.querySelector('details')?.open).map(row=>row.dataset.operationId));
        const rows=jobs.map(job=>{const row=card(job);if(opened.has(job.id))row.querySelector('details').open=true;return row;});
        list.replaceChildren(...rows);
    }
    const platformMeta = {
        wp25: {label:'WordPress', total:25, test:j=>j.platform==='wordpress'},
        blogspot33: {label:'Blogspot', total:33, test:j=>j.platform==='blogger'},
        tistory5: {label:'Tistory', total:5, test:j=>j.platform==='tistory'},
        naver1: {label:'Naver Blog', total:1, test:j=>j.platform==='naver', manual:true},
        news2: {label:'뉴스룸', total:2, test:j=>j.platform==='news'},
    };
    // CEO-facing simplification: the detailed 10-phase job model collapses to
    // exactly the four states the CEO screen is allowed to show.
    const simplePhase = job => {
        if (job.phase === 'published') return 'done';
        if (['working','publishing','dispatching','queued','accepted'].includes(job.phase)) return 'running';
        if (job.phase === 'review_ready') return 'review';
        return 'problem'; // failed, stopped, attention
    };
    const simpleLabel = {done:'완료', running:'진행중', review:'검토대기', problem:'문제'};
    // Best-effort cause bucket from the same free-text `detail` already shown
    // elsewhere on this page — never a new data source, just a coarser label.
    function causeLabel(job) {
        const text = (job.detail || '') + ' ' + (job.error || '');
        if (/이미지|image/i.test(text)) return '이미지 실패';
        if (/인증|401|403|forbidden|auth/i.test(text)) return '인증 실패';
        if (/색인|index|gsc|search console/i.test(text)) return 'Google 수집 실패';
        return '발행 실패';
    }
    const kstDate = seconds => new Date(seconds*1000).toLocaleDateString('en-CA',{timeZone:'Asia/Seoul'});
    function renderMissionBoard(jobs) {
        const stats=document.getElementById('mission-board-stats');
        const platforms=document.getElementById('mission-board-platforms');
        const boardTime=document.getElementById('mission-board-time');
        if (!stats || !platforms) return;
        const today=kstDate(Date.now()/1000);
        const todays=jobs.filter(job=>kstDate(job.created_at)===today);
        const tile=(label,count,color)=>{
            const box=el('div','','rounded-xl border border-white/10 bg-white/5 p-3 text-center');
            box.append(el('p',String(count),'text-2xl font-black '+color+' sm:text-3xl'));
            box.append(el('p',label,'mt-0.5 text-[10px] font-bold text-slate-400 sm:text-xs'));
            return box;
        };
        stats.replaceChildren(
            tile('게시 완료', todays.filter(j=>j.phase==='published').length, 'text-emerald-400'),
            tile('진행 중', todays.filter(j=>['working','publishing'].includes(j.phase)).length, 'text-sky-400'),
            tile('검토 대기', todays.filter(j=>j.phase==='review_ready').length, 'text-amber-400'),
            tile('문제 발생', todays.filter(j=>['failed','attention','stopped'].includes(j.phase)).length, 'text-rose-400'),
        );
        platforms.replaceChildren(...Object.entries(platformMeta).map(([group,meta])=>{
            const done=todays.filter(j=>meta.test(j) && j.phase==='published').length;
            const problem=todays.filter(j=>meta.test(j) && ['failed','attention'].includes(j.phase)).length;
            const box=el('div','','rounded-xl border border-white/10 bg-white/5 p-3 text-center');
            if (meta.manual && done===0) {
                // No automated pipeline exists yet for this platform — say so plainly
                // instead of showing a "0/1" that reads as a missed target.
                box.append(el('p','수동 운영','text-lg font-black text-slate-500 sm:text-xl'));
            } else {
                // News has no fixed daily quota (RSS-driven, published as many qualify) — a "/N" target would misread as a cap.
                box.append(el('p',(group==='news2'||meta.manual)?String(done)+'건':done+'/'+meta.total,'text-lg font-black text-white sm:text-xl'));
            }
            box.append(el('p',meta.label+(problem?' · 문제 '+problem:''),'mt-0.5 text-[10px] font-bold sm:text-xs '+(problem?'text-rose-400':'text-slate-400')));
            return box;
        }));
        if (boardTime) boardTime.textContent=today+' KST 기준 · 자동 갱신';
    }
    function renderCoreBusiness(jobs) {
        const ids = new Set(serverData.core_business || []);
        if (!ids.size) return;
        const today = kstDate(Date.now()/1000);
        document.querySelectorAll('.core-business-card').forEach(card => {
            const siteId = card.dataset.siteId; if (!ids.has(siteId)) return;
            const box = card.querySelector('.core-business-today'); if (!box) return;
            const siteJobs = jobs.filter(j => j.site_id === siteId);
            const todays = siteJobs.filter(j => kstDate(j.created_at) === today);
            const published = siteJobs.filter(j => j.phase === 'published').sort((a,b)=>b.checked_at-a.checked_at);
            const active = siteJobs.find(j => !terminal.has(j.phase));
            const lines = [
                '오늘 발행 ' + todays.filter(j=>j.phase==='published').length + '건',
                '마지막 발행 ' + (published[0] ? time(published[0].checked_at) : '기록 없음'),
                active ? '상태: ' + labels[active.phase] : (todays.some(j=>['failed','attention'].includes(j.phase)) ? '상태: 문제 있음' : '상태: 정상'),
            ];
            box.className = 'core-business-today mt-2 rounded-lg px-2 py-1.5 text-[11px] ' +
                (active && ['failed','attention'].includes(active.phase) ? 'bg-rose-50 text-rose-700' : 'bg-slate-50 text-slate-600');
            box.replaceChildren(...lines.map(t => el('p', t)));
        });
    }
    function renderRedAlert(jobs) {
        const body = document.getElementById('red-alert-body'); if (!body) return;
        const today = kstDate(Date.now()/1000);
        const rows = [];
        const ps = serverData.problem_summary || {};
        if (ps.wp_issues?.length) rows.push({label:'WP 인증·연결 실패 '+ps.wp_issues.length, jump:'wordpress'});
        if (ps.blogger_issues?.length) rows.push({label:'Blogspot 미연결 '+ps.blogger_issues.length, jump:'blogspot'});
        if (ps.tistory_issues?.length) rows.push({label:'Tistory 피드 실패 '+ps.tistory_issues.length, jump:'tistory'});
        if (ps.youtube_issues?.length) rows.push({label:'YouTube 채널ID 없음 '+ps.youtube_issues.length, jump:'youtube'});
        if (ps.sns_issues?.length) rows.push({label:'SNS 오류 '+ps.sns_issues.length, jump:'sns'});
        const todaysProblems = jobs.filter(j => kstDate(j.created_at)===today && ['failed','attention'].includes(j.phase));
        const byCause = new Map();
        todaysProblems.forEach(job => {
            const key = (platformMeta[job.group]?.label || job.platform) + ' ' + causeLabel(job);
            if (!byCause.has(key)) byCause.set(key, []);
            byCause.get(key).push(job);
        });
        byCause.forEach((jobsForCause, key) => rows.push({label: key+' '+jobsForCause.length, jobs: jobsForCause}));
        if (!rows.length) { body.replaceChildren(el('p','✅ 현재 긴급 문제 없음','text-sm font-black text-emerald-700')); return; }
        body.replaceChildren(...rows.map(row => {
            const line = el('div','','flex items-center justify-between gap-2 rounded-xl bg-rose-50 px-3 py-2');
            line.append(el('span',row.label,'text-xs font-black text-rose-800'));
            const actions = el('div','','flex items-center gap-2');
            if (row.jump) { const a=el('a','확인하기','text-[11px] font-bold text-rose-700 underline'); a.href='#'+row.jump; actions.append(a); }
            if (row.jobs) {
                const btn = el('button','상세보기','text-[11px] font-bold text-rose-700 underline'); btn.type='button';
                btn.onclick = () => {
                    const open = line.nextElementSibling?.classList.contains('red-alert-detail');
                    if (open) { line.nextElementSibling.remove(); return; }
                    const detail = el('div','','red-alert-detail rounded-xl bg-white border border-rose-100 px-3 py-2 text-[11px] text-slate-600 space-y-1');
                    row.jobs.forEach(j => detail.append(el('p', j.label+' · '+j.detail)));
                    line.after(detail);
                };
                actions.append(btn);
            }
            line.append(actions);
            return line;
        }));
    }
    let todayDetailTab = 'all';
    function renderTodayDetail(jobs) {
        const tabsBox = document.getElementById('today-detail-tabs');
        const listBox = document.getElementById('today-detail-list');
        if (!tabsBox || !listBox) return;
        const today = kstDate(Date.now()/1000);
        const todays = jobs.filter(j => kstDate(j.created_at) === today);
        const tabs = [['all','전체'],['wp25','WP'],['blogspot33','Blogspot'],['tistory5','Tistory'],['naver1','Naver'],['news2','뉴스룸']];
        tabsBox.replaceChildren(...tabs.map(([key,label]) => {
            const count = key==='all' ? todays.length : todays.filter(j=>platformMeta[key]?.test(j)).length;
            const btn = el('button',label+' '+count,'rounded-full border px-3 py-1 text-[11px] font-bold '+(todayDetailTab===key?'border-slate-900 bg-slate-900 text-white':'border-slate-200 text-slate-600'));
            btn.type='button'; btn.onclick=()=>{todayDetailTab=key;renderTodayDetail(lastJobs);};
            return btn;
        }));
        const rows = todays.filter(j => todayDetailTab==='all' || platformMeta[todayDetailTab]?.test(j))
            .sort((a,b)=>b.created_at-a.created_at);
        if (!rows.length) { listBox.replaceChildren(el('p','오늘 발행 기록이 없습니다.','text-xs text-slate-400')); return; }
        listBox.replaceChildren(...rows.map(job => {
            const state = simplePhase(job);
            const row = el('div','','flex flex-col gap-1 rounded-xl border border-slate-100 px-3 py-2 sm:flex-row sm:items-center sm:justify-between');
            const left = el('div');
            left.append(el('p',job.label,'text-xs font-black text-slate-900'));
            left.append(el('p','예정 '+time(job.created_at)+(job.phase==='published'?' · 발행 '+time(job.checked_at):''),'text-[10px] text-slate-500'));
            row.append(left);
            const right = el('div','','flex items-center gap-2');
            right.append(el('span',simpleLabel[state],'rounded-full px-2 py-0.5 text-[10px] font-black '+
                (state==='done'?'bg-emerald-100 text-emerald-700':state==='running'?'bg-sky-100 text-sky-700':state==='review'?'bg-amber-100 text-amber-700':'bg-rose-100 text-rose-700')));
            if (job.public_url) right.append(link('글 보기',job.public_url));
            if (state==='problem') {
                const btn=el('button','문제 보기','text-[11px] font-bold text-rose-700 underline'); btn.type='button';
                btn.onclick=()=>{
                    const open=row.nextElementSibling?.classList.contains('today-detail-problem');
                    if(open){row.nextElementSibling.remove();return;}
                    const box=el('p',job.detail,'today-detail-problem rounded-xl bg-rose-50 px-3 py-2 text-[11px] text-rose-800');
                    row.after(box);
                };
                right.append(btn);
            }
            row.append(right);
            return row;
        }));
    }
    function render(data) {
        lastJobs = data.jobs || [];
        connection.textContent = '통제실 연결됨 · ' + time(data.server_time);
        news.textContent = data.automatic_news?.message || '뉴스룸 RSS 감시 기록 확인 대기';
        feedBody.replaceChildren(...(data.automatic_news?.feeds || []).map(feed=>el('p',(feed.name||feed.key)+' · '+(feed.error||'RSS 연결 확인')+' · '+time(feed.checked))));
        const latest = new Map(); lastJobs.forEach(job=>{if (!latest.has(job.site_id)) latest.set(job.site_id,job);});
        lastJobs.filter(job=>!terminal.has(job.phase)).reverse().forEach(job=>latest.set(job.site_id,job));
        totals.replaceChildren();
        ['accepted','working','review_ready','publishing','published','stopped','failed','attention'].forEach(phase=>{
            const count = [...latest.values()].filter(j=>(['dispatching','queued'].includes(j.phase)?'accepted':j.phase)===phase).length;
            const button=el('button',labels[phase]+' '+count);button.type='button';button.dataset.phase=phase;button.onclick=()=>{selectedPhase=phase;filterJobs();};totals.append(button);
        });
        currentJobs=[...latest.values()]; filterJobs();
        document.querySelectorAll('[id^="bulk-status-"]').forEach(box=>{
            const group=box.id.slice('bulk-status-'.length); if(!managed(group)) return;
            const jobs = groups.has(group) ? [...latest.values()].filter(j=> group==='wp25'?j.platform==='wordpress': group==='news2'?j.platform==='news':group==='tistory5'?j.platform==='tistory':j.platform==='blogger') : [...latest.values()].filter(j=>j.site_group===group);
            const head=document.getElementById('bulk-headline-'+group), counts=document.getElementById('bulk-counts-'+group);
            if(head) head.textContent=jobs.length===1?labels[jobs[0].phase]+' · '+jobs[0].detail:jobs.length?'사이트별 실제 작업 상태':'아직 접수된 요청 없음';
            if(counts) counts.textContent=jobs.length && groups.has(group)?['accepted','working','review_ready','publishing','published','stopped','failed','attention'].filter(p=>jobs.some(j=>(['dispatching','queued'].includes(j.phase)?'accepted':j.phase)===p)).map(p=>labels[p]+' '+jobs.filter(j=>(['dispatching','queued'].includes(j.phase)?'accepted':j.phase)===p).length).join(' · '):'';
            let list=box.querySelector('.operation-list');
            if(!list) {
                list=el('div','','operation-list');
                if(groups.has(group)){const details=el('details');details.append(el('summary','사이트별 진행 상태·이력 보기'),list);box.append(details);}
                else box.append(list);
            }
            refreshList(list,jobs);
            const failures=document.getElementById('bulk-failures-'+group); if(failures) failures.replaceChildren();
            const button=document.getElementById('bulk-button-'+group); if(button) button.disabled=jobs.some(j=>!terminal.has(j.phase));
        });
        document.querySelectorAll('[data-quick-status]').forEach(status=>{
            const button=status.parentElement.querySelector('[data-quick-group]'); if(!button||!managed(button.dataset.quickGroup)) return;
            const job=[...latest.values()].find(j=>j.site_group===button.dataset.quickGroup);
            status.textContent=job?labels[job.phase]+' · '+job.detail:'아직 접수된 요청 없음';
            let jump=status.parentElement.querySelector('[data-operation-jump]');
            if(!jump) {jump=el('button','작업 상태·이력 보기','operation-action');jump.dataset.operationJump='';jump.onclick=()=>jumpTo('bulk-status-'+button.dataset.quickGroup);status.after(jump);}
        });
        refreshList(historyBody,lastJobs.slice(0,60));
        renderMissionBoard(lastJobs);
        renderCoreBusiness(lastJobs);
        renderRedAlert(lastJobs);
        renderTodayDetail(lastJobs);
    }
    async function poll() {
        if(polling) return; polling=true;
        try {const response=await fetch('/api/operations',{cache:'no-store',headers:{Accept:'application/json'}});if(!response.ok) throw Error();render(await response.json());}
        catch(_) {connection.textContent='통제실 연결 지연 · 표시된 상태는 마지막 확인 기록입니다. 자동으로 재확인합니다.';}
        finally {polling=false;}
    }
    async function submit(form) {
        let requestId=form.dataset.operationRequestId;
        if(!requestId) {requestId=crypto.randomUUID();form.dataset.operationRequestId=requestId;}
        const payload=new FormData(form); payload.set('operation_request_id',requestId);
        showNotice('요청을 보내고 있습니다. 아직 접수 확인 전입니다.');
        try {
            const response=await fetch(form.action,{method:'POST',body:payload,headers:{Accept:'application/json'},credentials:'same-origin'});
            const result=await response.json();
            if(response.status!==202 || !result.accepted) {showNotice(result.message || '요청을 접수하지 못했습니다.',result.target,true);await poll();return false;}
            delete form.dataset.operationRequestId;
            await poll(); showNotice(result.message,result.target); jumpTo(result.target);return true;
        } catch(_) {showNotice('요청 전달 결과를 확인하지 못했습니다. 작업 상태를 먼저 확인하세요. 같은 버튼을 다시 눌러도 동일 요청 번호로 확인합니다.','operation-summary',true);await poll();return false;}
    }
    document.querySelectorAll('[id^="bulk-button-"]').forEach(button=>{
        if(!managed(button.id.slice('bulk-button-'.length))) return;
        const form=button.closest('form');
        form.addEventListener('submit',async event=>{if(event.defaultPrevented)return;event.preventDefault();button.disabled=true;await submit(form);await poll();});
    });
    window.controlOperations={managed,submit,poll};
    poll();setInterval(poll,8000);
})();
