/* TR YouTube 24H Live Studio — frontend (no fake status, real backend only) */
const $ = s => document.querySelector(s);
const backendInput = $('#backendUrl'), tokenInput = $('#adminToken');
let BACKEND = localStorage.getItem('tr_live_backend') || 'http://localhost:5000';
let TOKEN = localStorage.getItem('tr_live_token') || '';
backendInput.value = BACKEND; tokenInput.value = TOKEN;
let uploadXHR = null;

function showAlert(msg, ok=false){ const a=$('#alert'); a.textContent=msg; a.className='alert '+(ok?'ok':'err'); a.classList.remove('hidden'); setTimeout(()=>a.classList.add('hidden'), 6000); }
function headers(){ return {'Content-Type':'application/json','X-Admin-Token':TOKEN}; }
async function api(path, opts={}){
  const res = await fetch(BACKEND.replace(/\/$/,'')+path, {...opts, headers:{...headers(), ...(opts.headers||{})}});
  const data = await res.json().catch(()=>({}));
  if(!res.ok) throw new Error(data.error || ('HTTP '+res.status));
  return data;
}
function fmtHMS(s){ s=Math.max(0,Math.floor(s)); const h=String(Math.floor(s/3600)).padStart(2,'0'), m=String(Math.floor(s%3600/60)).padStart(2,'0'), x=String(s%60).padStart(2,'0'); return `${h}:${m}:${x}`; }
function fmtSize(b){ if(!b) return '—'; if(b>1e9) return (b/1e9).toFixed(2)+' GB'; if(b>1e6) return (b/1e6).toFixed(1)+' MB'; return (b/1024).toFixed(0)+' KB'; }

// Navigation
document.querySelectorAll('.nav').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.nav').forEach(x=>x.classList.remove('active')); b.classList.add('active');
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  $('#page-'+b.dataset.page).classList.add('active');
  if(b.dataset.page==='logs') refreshLogs();
}));

$('#saveConn').addEventListener('click',()=>{
  BACKEND=backendInput.value.trim(); TOKEN=tokenInput.value.trim();
  localStorage.setItem('tr_live_backend',BACKEND); localStorage.setItem('tr_live_token',TOKEN);
  showAlert('Connection saved. Checking backend…', true); refreshAll();
});

// Upload — drag & drop + progress + cancel
const drop=$('#dropZone'), fileInput=$('#fileInput');
['dragover','dragenter'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.style.borderColor='#7c3aed';}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.style.borderColor='';}));
drop.addEventListener('drop',ev=>{ const f=ev.dataTransfer.files[0]; if(f) uploadFile(f); });
fileInput.addEventListener('change',()=>{ if(fileInput.files[0]) uploadFile(fileInput.files[0]); });
$('#btnCancelUpload').addEventListener('click',()=>{ if(uploadXHR) uploadXHR.abort(); });

function uploadFile(file){
  if(!/\.(mp4|mkv|mov)$/i.test(file.name)) return showAlert('Only MP4, MKV or MOV.');
  const fd=new FormData(); fd.append('video',file);
  $('#uploadProgress').classList.remove('hidden'); $('#btnCancelUpload').classList.remove('hidden');
  $('#uploadInfo').textContent='Uploading '+file.name+'…';
  uploadXHR=new XMLHttpRequest();
  uploadXHR.open('POST', BACKEND.replace(/\/$/,'')+'/api/upload');
  uploadXHR.setRequestHeader('X-Admin-Token', TOKEN);
  uploadXHR.upload.onprogress=e=>{ if(e.lengthComputable){ const p=Math.round(e.loaded/e.total*100); $('#uploadBar').style.width=p+'%'; $('#uploadInfo').textContent=`Uploading… ${p}%`; }};
  uploadXHR.onload=()=>{
    $('#btnCancelUpload').classList.add('hidden');
    let d={}; try{d=JSON.parse(uploadXHR.responseText);}catch(e){}
    if(uploadXHR.status>=400) return showAlert(d.error||'Upload failed.');
    const v=d.video; $('#uploadInfo').textContent=`Uploaded: ${v.name} • ${fmtSize(v.size)} • ${v.duration?v.duration.toFixed(1)+'s':''} • ${v.width}x${v.height}`;
    $('#videoMeta').innerHTML=`<p><strong>${v.name}</strong><br>${fmtSize(v.size)} • ${v.duration?v.duration.toFixed(1)+' seconds':''} • ${v.width}×${v.height}</p>`;
    const prev=$('#preview'); prev.classList.remove('hidden'); prev.src=URL.createObjectURL(file);
    showAlert('Video uploaded to server. Ready to go live.', true); refreshAll();
  };
  uploadXHR.onerror=()=>showAlert('Upload failed — is the backend running? Check Backend URL + token.');
  uploadXHR.onabort=()=>{ $('#uploadInfo').textContent='Upload cancelled.'; $('#uploadProgress').classList.add('hidden'); };
  uploadXHR.send(fd);
}

// Settings
$('#settingsForm').addEventListener('submit', async ev=>{
  ev.preventDefault();
  const fd=new FormData(ev.target); const body={};
  fd.forEach((v,k)=>body[k]=v);
  body.fps=parseInt(body.fps); body.video_bitrate_kbps=parseInt(body.video_bitrate_kbps);
  body.audio_bitrate_kbps=parseInt(body.audio_bitrate_kbps); body.duration_hours=parseFloat(body.duration_hours);
  try{ const d=await api('/api/settings',{method:'POST',body:JSON.stringify(body)}); showAlert('Settings saved. Stream key stored on server only.', true); loadSettingsIntoForm(d.settings); }
  catch(e){ showAlert('Save failed: '+e.message); }
});
async function loadSettingsIntoForm(s){
  if(!s) return;
  const f=$('#settingsForm');
  f.rtmp_url.value=s.rtmp_url||''; f.title.value=s.title||''; f.description.value=s.description||'';
  f.category.value=s.category||'Entertainment'; f.privacy.value=s.privacy||'public';
  f.resolution.value=s.resolution||'720p'; f.fps.value=String(s.fps||30);
  f.video_bitrate_kbps.value=String(s.video_bitrate_kbps||2500); f.audio_bitrate_kbps.value=String(s.audio_bitrate_kbps||128);
  f.duration_hours.value=s.duration_hours||24;
  // Never put the real key back in the field. Keep placeholder + hint.
  f.stream_key.value=''; f.stream_key.placeholder = s.has_stream_key ? 'Key saved (****'+(s.stream_key||'').slice(-4)+') — leave blank to keep it' : 'Paste from YouTube Studio → Go Live';
  $('#keyHint').textContent = s.has_stream_key ? 'Saved key: '+s.stream_key+' — leave the field blank to keep it, or paste a new key to replace it.' : 'Saved key: not set yet.';
}

// Controls
$('#btnStart').addEventListener('click', async ()=>{ try{ const d=await api('/api/start',{method:'POST',body:'{}'}); showAlert('LIVE started — check YouTube Studio → Go Live to confirm.', true); refreshAll(); }catch(e){ showAlert('Start failed: '+e.message); }});
$('#btnStop').addEventListener('click', async ()=>{ if(!confirm('Stop the live stream?')) return; try{ await api('/api/stop',{method:'POST',body:'{}'}); showAlert('Live stopped.', true); refreshAll(); }catch(e){ showAlert('Stop failed: '+e.message); }});
$('#btnRestart').addEventListener('click', async ()=>{ try{ await api('/api/restart',{method:'POST',body:'{}'}); showAlert('Live restarted.', true); refreshAll(); }catch(e){ showAlert('Restart failed: '+e.message); }});
$('#btnClearLogs').addEventListener('click',()=>{ $('#logBox').textContent=''; });

// Polling — real backend only
async function refreshAll(){
  try{
    const d=await api('/api/status'); const s=d.status;
    const live=s.live;
    $('#statusPill').classList.toggle('live', live); $('#statusText').textContent=live?'● LIVE':'OFFLINE';
    $('#stLive').textContent=live?'● LIVE':'OFFLINE'; $('#mLive').textContent=live?'● LIVE':'OFFLINE';
    $('#stElapsed').textContent=fmtHMS(s.elapsed_seconds); $('#mElapsed').textContent=fmtHMS(s.elapsed_seconds);
    $('#stRemaining').textContent=live?fmtHMS(s.remaining_seconds):'—'; $('#mRemaining').textContent=live?fmtHMS(s.remaining_seconds):'—';
    $('#stVideo').textContent=s.video_name||'No video'; $('#stVideoMeta').textContent=s.video_duration?Math.round(s.video_duration)+'s':''; 
    $('#stSize').textContent=fmtSize(s.video_size); $('#stRes').textContent=s.video_resolution||'—';
    $('#stConn').textContent=live?'Connected':'—';
    $('#mBitrate').textContent=s.last_bitrate||'—'; $('#mPid').textContent=s.ffmpeg_pid||'—'; $('#mRestarts').textContent=s.restart_count||0;
    $('#mError').textContent=s.last_error||'—';
    $('#liveNote').textContent=live?`Live since ${new Date(Date.now()-s.elapsed_seconds*1000).toLocaleTimeString()} • auto-stops after remaining time • FFmpeg auto-reconnects on drop.`:'';
    if(s.settings) loadSettingsIntoForm(s.settings);
  }catch(e){
    $('#statusPill').classList.remove('live'); $('#statusText').textContent='BACKEND OFFLINE';
    $('#stLive').textContent='BACKEND OFFLINE'; $('#stConn').textContent='Backend unreachable — check URL + token';
  }
  try{
    const st=await api('/api/server-stats');
    $('#stCpu').textContent=st.cpu_percent!=null?st.cpu_percent.toFixed(1)+'%':'—';
    $('#mCpu').textContent=st.cpu_percent!=null?st.cpu_percent.toFixed(1)+'%':'—';
    $('#stRam').textContent=st.memory?st.memory.percent.toFixed(0)+'%':'—';
    $('#mMem').textContent=st.memory?`${st.memory.percent.toFixed(0)}% (${st.memory.used_mb} / ${st.memory.total_mb} MB)`:'—';
  }catch(e){}
}
async function refreshLogs(){
  try{ const d=await api('/api/logs'); $('#logBox').textContent=d.logs.map(l=>`${l.time} [${l.level}] ${l.message}`).join('\n')||'No logs yet.'; }
  catch(e){ $('#logBox').textContent='Cannot load logs: '+e.message+' — check Backend URL + Admin Token.'; }
}
refreshAll(); setInterval(refreshAll, 2000); setInterval(()=>{ if($('#page-logs').classList.contains('active')) refreshLogs(); }, 5000);
