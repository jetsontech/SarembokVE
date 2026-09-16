/* SAREMBOK_UI_SIMPLIFIED_V1_20260915 */
(function(){
  'use strict';
  function boot(){
    document.body.classList.add('srbk-simple-mode');
    document.documentElement.dataset.sarembokUi='simplified-v1';
    /* Do not replace runtime controls. This layer only changes presentation. */
    var input=document.getElementById('global-input-field');
    if(input) input.setAttribute('aria-label','Ask Sarembok anything');
    var send=document.getElementById('global-send-btn');
    if(send) send.setAttribute('aria-label','Send message');
    var mic=document.getElementById('global-mic-btn');
    if(mic) mic.setAttribute('aria-label','Voice input');
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot,{once:true}); else boot();
})();
