/* SAREMBOK_UI_RUNTIME_V4_20260915 */
(function(){
'use strict';

let ws=null;
let rpcId=0;
let pending=new Map();
let sessionToken='';
let activeRequest=null;
let reconnectTimer=null;
let reconnectDelay=1000;
let connecting=null;

const $=id=>document.getElementById(id);

function setStatus(text,online){
  const status=$('runtime-status');
  const dot=$('runtime-dot');
  if(status)status.textContent=text;
  if(dot)dot.className='dot '+(online?'online':'offline');
}
function setMeta(text){const el=$('connection-meta');if(el)el.textContent=text;}
function escapeHtml(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function normalizeText(value){
  if(value==null)return '';
  if(typeof value==='string')return value;
  if(Array.isArray(value))return value.map(normalizeText).filter(Boolean).join('');
  if(typeof value==='object'){
    for(const key of ['response','text','content','delta','message','output','answer'])if(value[key]!=null)return normalizeText(value[key]);
    try{return JSON.stringify(value,null,2)}catch{return String(value)}
  }
  return String(value);
}
function youtubeEmbed(url){
  try{
    const u=new URL(url);
    let id=u.searchParams.get('v');
    if(!id&&u.hostname.includes('youtu.be'))id=u.pathname.replace(/^\//,'');
    if(!id)return '';
    id=id.replace(/[^a-zA-Z0-9_-]/g,'');
    return '<div class="media-card"><div class="media-label">VIDEO</div><iframe class="media-frame" src="https://www.youtube.com/embed/'+id+'" title="Sarembok video" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe><a class="media-link" href="https://www.youtube.com/watch?v='+id+'" target="_blank" rel="noopener">Open on YouTube ↗</a></div>';
  }catch{return ''}
}
function renderDirectiveBlocks(raw){
  let text=String(raw??'');
  const blocks=[];
  text=text.replace(/:::video\s*([^\n]*)\n([\s\S]*?)\n:::/gi,(_,title,body)=>{
    const lines=String(body).split(/\r?\n/).map(s=>s.trim()).filter(Boolean);const url=lines.find(v=>/^https?:\/\//i.test(v))||'';
    const embed=youtubeEmbed(url);blocks.push(embed||('<div class="media-card"><div class="media-label">VIDEO</div><div class="media-title">'+escapeHtml(title||'Sarembok video')+'</div><a class="media-link" href="'+escapeHtml(url)+'" target="_blank" rel="noopener">Open media ↗</a></div>'));return '\n';
  });
  text=text.replace(/:::music\s*([^\n]*)\n([\s\S]*?)\n:::/gi,(_,title,body)=>{
    const lines=String(body).split(/\r?\n/).map(s=>s.trim()).filter(Boolean);const url=lines.find(v=>/^https?:\/\//i.test(v))||'';const embed=youtubeEmbed(url);
    blocks.push(embed?embed.replace('VIDEO','AUDIO').replace('Open on YouTube','Open media'):'<div class="media-card"><div class="media-label">AUDIO</div><div class="media-title">'+escapeHtml(title||'Sarembok audio')+'</div></div>');return '\n';
  });
  if(blocks.length)blocks.forEach(b=>{text+='\n\n'+b;});
  return text;
}
function renderMarkdown(raw){
  const withBlocks=renderDirectiveBlocks(raw);
  const extracted=[];
  const placeholdered=withBlocks.replace(/<div class="media-card">[\s\S]*?<\/div>/g,m=>{const token='@@MEDIA_'+extracted.length+'@@';extracted.push(m);return token;});
  let text=placeholdered.replace(/\\([*_`#>|])/g,'$1');
  let html=escapeHtml(text);
  html=html.replace(/(https?:\/\/[^\s<]+)/g,'<a href="$1" target="_blank" rel="noopener">$1</a>');
  html=html.replace(/```(?:[a-zA-Z0-9_-]+)?\n?([\s\S]*?)```/g,(_,code)=>'<pre><code>'+escapeHtml(code.trim())+'</code></pre>');
  html=html.replace(/`([^`\n]+)`/g,'<code>$1</code>');
  html=html.replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>');
  html=html.replace(/__([^_\n]+)__/g,'<strong>$1</strong>');
  html=html.replace(/^###\s+(.+)$/gm,'<h4>$1</h4>');
  html=html.replace(/^##\s+(.+)$/gm,'<h3>$1</h3>');
  html=html.replace(/^#\s+(.+)$/gm,'<h2>$1</h2>');
  html=html.replace(/^[-*]\s+(.+)$/gm,'<li>$1</li>');
  html=html.replace(/(<li>.*?<\/li>)(?:\s*<br>)+(?!<li>)/gs,'<ul>$1</ul>');
  html=html.replace(/^>\s+(.+)$/gm,'<blockquote>$1</blockquote>');
  html=html.replace(/\n{2,}/g,'</p><p>');
  html=html.replace(/\n/g,'<br>');
  html='<p>'+html+'</p>';
  extracted.forEach((fragment,i)=>{html=html.replace(new RegExp('@@MEDIA_'+i+'@@','g'),fragment)});
  return html;
}
function renderStructured(data){
  const sr=data&&data.structuredResponse;
  if(!sr||typeof sr!=='object')return '';
  const parts=[];
  if(sr.title)parts.push('<h3>'+escapeHtml(sr.title)+'</h3>');
  const sections=Array.isArray(sr.sections)?sr.sections:[];
  for(const section of sections){
    if(!section||typeof section!=='object')continue;
    if(section.heading)parts.push('<h4>'+escapeHtml(section.heading)+'</h4>');
    const body=section.content??section.text;
    if(body)parts.push(renderMarkdown(normalizeText(body)));
    const items=Array.isArray(section.items)?section.items:[];
    if(items.length)parts.push('<ul>'+items.map(i=>'<li>'+renderMarkdown(normalizeText(i)).replace(/^<p>|<\/p>$/g,'')+'</li>').join('')+'</ul>');
  }
  return parts.join('');
}
function renderInto(bubble,text,data){
  if(!bubble)return;
  bubble.innerHTML=renderStructured(data)||renderMarkdown(text);
  const conv=$('conversation');if(conv)conv.scrollTop=conv.scrollHeight;
}
function addMessage(role,text,data){
  const empty=$('empty-state');if(empty)empty.remove();
  const wrap=document.createElement('div');wrap.className='message '+role;
  const label=role==='user'?'YOU':'SAREMBOK';
  wrap.innerHTML='<div><div class="message-label">'+label+'</div><div class="bubble" tabindex="0"></div></div>';
  const conversation=$('conversation');if(conversation){conversation.appendChild(wrap);conversation.scrollTop=conversation.scrollHeight;}
  const bubble=wrap.querySelector('.bubble');renderInto(bubble,text,data);return bubble;
}
function showWorking(show){
  const typing=$('typing'),send=$('send-btn'),stop=$('stop-btn');
  if(typing)typing.hidden=!show;if(send)send.hidden=show;if(stop)stop.hidden=!show;
}
async function initSession(force=false){
  if(sessionToken&&!force)return sessionToken;
  const response=await fetch('/session',{cache:'no-store',credentials:'same-origin',headers:{Accept:'application/json'}});
  if(!response.ok)throw new Error('Secure session failed ('+response.status+')');
  const data=await response.json();sessionToken=String(data.sessionToken||'');
  if(!sessionToken)throw new Error('Secure session returned no token');
  return sessionToken;
}
function scheduleReconnect(){
  if(reconnectTimer||activeRequest)return;
  reconnectTimer=setTimeout(()=>{reconnectTimer=null;connect().catch(()=>{});},reconnectDelay);
  reconnectDelay=Math.min(reconnectDelay*2,8000);
}
async function connect(){
  if(ws&&ws.readyState===WebSocket.OPEN)return ws;
  if(connecting)return connecting;
  connecting=(async()=>{
    setStatus('AUTHENTICATING',false);setMeta('ESTABLISHING SECURE SESSION');await initSession();
    await new Promise((resolve,reject)=>{
      const proto=location.protocol==='https:'?'wss:':'ws:';const socket=new WebSocket(proto+'//'+location.host+'/ws');let settled=false;
      const timer=setTimeout(()=>{if(!settled){settled=true;try{socket.close()}catch{}reject(new Error('WebSocket connection timeout'));}},10000);
      socket.onopen=()=>{if(settled)return;settled=true;clearTimeout(timer);ws=socket;reconnectDelay=1000;setStatus('ONLINE',true);setMeta('SECURE RUNTIME SESSION');resolve();refreshRuntime();};
      socket.onerror=()=>{if(!settled){settled=true;clearTimeout(timer);reject(new Error('WebSocket connection failed'));}};
      socket.onclose=()=>{
        if(ws===socket)ws=null;setStatus('OFFLINE',false);setMeta('RECONNECTING…');
        for(const [id,q] of pending){q.reject(new Error('Connection closed'));pending.delete(id)}
        if(activeRequest&&!activeRequest.finished)finishMessage('Connection closed before Sarembok completed the request.',true);
        scheduleReconnect();
      };
      socket.onmessage=event=>handleMessage(event.data);
    });
    return ws;
  })();
  try{return await connecting}finally{connecting=null}
}
function handleMessage(raw){
  let data;try{data=JSON.parse(raw)}catch{return;}
  const method=String(data.method||'');const params=data.params||{};
  if(method==='SarembokChat.delta'||method==='SarembokChat.stream'||method==='chat.delta'||method==='stream.delta'){
    const id=params.id||params.requestId||data.id;const delta=normalizeText(params.text??params.delta??params.content??params.response??data.result??'');
    const q=(id&&pending.get(id));if(q&&q.onDelta&&delta)q.onDelta(delta);else if(activeRequest&&activeRequest.onDelta&&delta)activeRequest.onDelta(delta);return;
  }
  if(data.id!=null){
    const q=pending.get(String(data.id))||pending.get(data.id);if(!q)return;
    pending.delete(String(data.id));pending.delete(data.id);
    if(data.error)q.reject(new Error(String(data.error.message||'RPC error')));else q.resolve(data.result??data);
  }
}
async function sendRPC(method,params={},onDelta=null){
  await connect();if(!sessionToken)await initSession();
  const id='rpc-'+(++rpcId);const payload={...params,sessionToken};
  return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{pending.delete(id);reject(new Error('Request timed out: '+method));},125000);
    pending.set(id,{resolve:v=>{clearTimeout(timer);resolve(v)},reject:e=>{clearTimeout(timer);reject(e)},onDelta});
    try{ws.send(JSON.stringify({jsonrpc:'2.0',id,method,params:payload}));}catch(error){clearTimeout(timer);pending.delete(id);reject(error)}
  });
}
function resultText(result){return result?normalizeText(typeof result==='string'?result:(result.response??result.text??result.content??result.output??result.answer??result.message??'')):'';}
function finishMessage(text,error=false,data=null){
  if(!activeRequest)return;const request=activeRequest;request.finished=true;
  renderInto(request.bubble,text||'Directive completed.',data);if(error)request.bubble.classList.add('error-bubble');
  activeRequest=null;showWorking(false);
}
async function submit(text){
  text=String(text||'').trim();if(!text||activeRequest)return;
  addMessage('user',text);const prompt=$('prompt');if(prompt){prompt.value='';resize();}
  showWorking(true);const bubble=addMessage('assistant','Sarembok is working…');
  activeRequest={bubble,finished:false,full:'',onDelta:delta=>{if(!activeRequest||activeRequest.finished)return;activeRequest.full+=String(delta);renderInto(bubble,activeRequest.full,null);}};
  try{
    const result=await sendRPC('SarembokChat',{prompt:text,stream:true},activeRequest.onDelta);
    const finalText=activeRequest.full||resultText(result)||'Directive completed.';
    finishMessage(finalText,false,result);
  }catch(error){finishMessage('Execution failed: '+String(error&&error.message||error||'Unknown execution error'),true);}
}
function resize(){const p=$('prompt');if(!p)return;p.style.height='auto';p.style.height=Math.min(p.scrollHeight,150)+'px';}
async function refreshRuntime(){
  try{
    const r=await sendRPC('GetRuntimeInfo',{});
    if($('drawer-runtime'))$('drawer-runtime').textContent=r.status||'ONLINE';
    if($('runtime-detail'))$('runtime-detail').textContent=JSON.stringify(r,null,2);
    refreshInventory();
  }catch(error){
    if($('drawer-runtime'))$('drawer-runtime').textContent='Unavailable';
    if($('runtime-detail'))$('runtime-detail').textContent=String(error&&error.message||error||'Runtime query failed');
  }
}
async function refreshInventory(){
  for(const [method,id,key] of [['ListWorkers','workers-count','workers'],['ListAgents','agents-count','agents'],['ListTasks','tasks-count','tasks']]){
    try{const r=await sendRPC(method,{});const items=Array.isArray(r)?r:(r&&Array.isArray(r[key])?r[key]:[]);const count=r&&Number.isFinite(Number(r.count))?Number(r.count):items.length;if($(id))$(id).textContent=String(count);}
    catch{if($(id))$(id).textContent='Unavailable';}
  }
}
function openDrawer(){const drawer=$('system-drawer');if(!drawer)return;drawer.classList.add('open');drawer.setAttribute('aria-hidden','false');const backdrop=$('drawer-backdrop');if(backdrop)backdrop.hidden=false;refreshRuntime();}
function closeDrawer(){const drawer=$('system-drawer');if(drawer){drawer.classList.remove('open');drawer.setAttribute('aria-hidden','true')}const backdrop=$('drawer-backdrop');if(backdrop)backdrop.hidden=true;}
function stopCurrent(){if(!activeRequest)return;finishMessage('Request stopped by user.',true);}
function boot(){
  const form=$('chat-form'),prompt=$('prompt');
  if(form)form.addEventListener('submit',event=>{event.preventDefault();submit(prompt?prompt.value:'')});
  if(prompt){prompt.addEventListener('input',resize);prompt.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();submit(prompt.value)}});setTimeout(()=>prompt.focus(),150)}
  const stop=$('stop-btn');if(stop)stop.addEventListener('click',stopCurrent);const system=$('system-btn');if(system)system.addEventListener('click',openDrawer);const close=$('close-system');if(close)close.addEventListener('click',closeDrawer);const backdrop=$('drawer-backdrop');if(backdrop)backdrop.addEventListener('click',closeDrawer);
  document.querySelectorAll('[data-prompt]').forEach(button=>button.addEventListener('click',()=>submit(button.dataset.prompt||'')));
  connect().catch(error=>{setStatus('OFFLINE',false);setMeta('RUNTIME CONNECTION UNAVAILABLE');scheduleReconnect();console.warn('Sarembok connection:',error)});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
