let evtSrc=null, timer=null, rowCount=0, activeFilter='all';

function doStart(){
  fetch('/start',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})
    .then(r=>r.json()).then(d=>{
      if(!d.ok){alert(d.error);return;}
      document.getElementById('log').innerHTML='';
      document.getElementById('res-body').innerHTML='';
      document.getElementById('res-tbl').style.display='none';
      document.getElementById('no-data').style.display='block';
      document.getElementById('res-info').textContent='';
      rowCount=0; document.getElementById('res-cnt').textContent='0';
      updStats({total:0,bez_www:0,ma_www:0,pominieto:0,brak_danych:0,cities_done:0,cities_total:40,current_city:'',elapsed_sec:0});
      setChip('running');
      document.getElementById('btn-start').disabled=true;
      document.getElementById('btn-stop').style.display='inline-flex';
      document.getElementById('btn-dl').style.display='none';
      doStream(); doPoll();
    });
}

function doStop(){ fetch('/stop',{method:'POST'}); }

function doStream(){
  if(evtSrc) evtSrc.close();
  evtSrc = new EventSource('/stream');
  evtSrc.onmessage = e => {
    const d = JSON.parse(e.data);
    if(d.typ==='end'){evtSrc.close();return;}
    addLog(d);
  };
}

function addLog(e){
  const log = document.getElementById('log');
  const em = log.querySelector('.log-empty');
  if(em) em.remove();

  const row = document.createElement('div');
  row.className = 'log-row';
  row.dataset.typ = e.typ;
  if(activeFilter !== 'all' && e.typ !== activeFilter) row.classList.add('hidden');

  row.innerHTML = `<span class="log-time">${e.ts}</span><span class="log-txt ${e.typ}">${esc(e.msg)}</span>`;
  log.appendChild(row);
  // Auto-scroll tylko jeśli użytkownik jest blisko dołu
  if(log.scrollTop + log.clientHeight >= log.scrollHeight - 60) {
    log.scrollTop = log.scrollHeight;
  }
}

function setFilter(f, btn){
  activeFilter = f;
  document.querySelectorAll('.lf-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('#log .log-row').forEach(row=>{
    if(f==='all' || row.dataset.typ===f) row.classList.remove('hidden');
    else row.classList.add('hidden');
  });
}

function doPoll(){
  clearInterval(timer);
  timer = setInterval(()=>{
    fetch('/status').then(r=>r.json()).then(d=>{
      updStats(d.stats);
      if(d.has_file) document.getElementById('btn-dl').style.display='inline-flex';
      if(!d.running){
        clearInterval(timer);
        document.getElementById('btn-start').disabled=false;
        document.getElementById('btn-stop').style.display='none';
        setChip(d.error?'error':'done');
        const s=d.stats;
        if(s) document.getElementById('res-info').textContent=`${s.bez_www} bez www · ${s.total} sprawdzono · ${s.pominieto} pominięto`;
      }
    });
    fetch('/results').then(r=>r.json()).then(data=>{
      if(data.length>rowCount){
        const tb = document.getElementById('res-body');
        document.getElementById('res-tbl').style.display='table';
        document.getElementById('no-data').style.display='none';
        for(let i=rowCount;i<data.length;i++) tb.appendChild(mkRow(data[i],i+1));
        rowCount=data.length;
        document.getElementById('res-cnt').textContent=rowCount;
      }
    });
  },1500);
}

function mkRow(f,n){
  const tr=document.createElement('tr');
  const rat=f.ocena?`<span class="rat"><b>${f.ocena}</b>${f.liczba_opinii?` · ${f.liczba_opinii}`:''}</span>`:'<span class="rat">—</span>';
  tr.innerHTML=`
    <td style="color:var(--text3);font-family:var(--mono);font-size:0.68rem;">${n}</td>
    <td class="nm" title="${esc(f.nazwa)}">${esc(f.nazwa)}</td>
    <td>${f.branza?`<span class="tag">${esc(f.branza)}</span>`:'—'}</td>
    <td title="${esc(f.adres)}">${esc(f.adres||'—')}</td>
    <td style="font-family:var(--mono);font-size:0.7rem;">${esc(f.telefon||'—')}</td>
    <td>${rat}</td>
    <td style="font-size:0.7rem;" title="${esc(f.godziny)}">${esc((f.godziny||'').slice(0,25)||'—')}</td>
    <td><a class="maps-a" href="${esc(f.url_gmaps)}" target="_blank">↗ otwórz</a></td>`;
  return tr;
}

function updStats(s){
  if(!s) return;
  set('s-bwww', s.bez_www||0);
  set('s-total', s.total||0);
  set('s-mawww', s.ma_www||0);
  set('s-pomin', s.pominieto||0);
  set('s-brakd', s.brak_danych||0);
  const pct = s.total>0 ? (s.bez_www/s.total*100).toFixed(1)+'%' : '0%';
  set('s-pct', pct);
  set('s-city', s.current_city||'—');

  const pctNum = s.cities_total ? Math.round((s.cities_done/s.cities_total)*100) : 0;
  document.getElementById('prog').style.width=pctNum+'%';
  set('prog-pct', pctNum+'%');
  set('prog-lbl', `${s.cities_done||0} / ${s.cities_total||40} miast`);

  // Timer
  const sec = s.elapsed_sec||0;
  const m=Math.floor(sec/60), ss=sec%60;
  set('s-time', `${String(m).padStart(2,'0')}:${String(ss).padStart(2,'0')}`);
}

function set(id,v){ const el=document.getElementById(id); if(el) el.textContent=v; }

function setChip(s){
  document.getElementById('chip').className='chip chip-'+s;
  document.getElementById('chip-txt').textContent={idle:'Gotowy',running:'Skanowanie...',done:'Ukończono',error:'Błąd'}[s]||s;
}

function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
