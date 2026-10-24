'use strict';
let emailProofEnabled=false,emailProofToken='',emailProofOwner=null,emailProofVersion=0;
function captureEmailProof(){
  if(!location.hash.startsWith('#verify-email='))return;
  const candidate=location.hash.slice(14);
  emailProofToken=/^[A-Za-z0-9_-]{43}$/.test(candidate)?candidate:'';
  history.replaceState(null,'',location.pathname+location.search);
  if(!emailProofToken)msg('Link potwierdzający jest nieprawidłowy.');
  else msg('Zaloguj się na właściwe konto i potwierdź adres w sekcji Bezpieczeństwo konta.');
  el('email-verification-confirm').hidden=!emailProofToken||!emailProofOwner;
}
async function refreshEmailProof(version){
  if(!emailProofEnabled||!emailProofOwner)return;
  try{
    const result=await api('/auth/email-verification/status');
    if(version!==emailProofVersion)return;
    el('email-verification').hidden=false;
    el('email-verification-status').textContent=result.verified?'Adres e-mail potwierdzony.':'Potwierdź adres e-mail, aby otrzymywać wiadomości dotyczące zamówień.';
    el('email-verification-request').hidden=result.verified;
    el('email-verification-confirm').hidden=result.verified||!emailProofToken;
  }catch(e){if(version===emailProofVersion&&e.message!=='SESSION_CHANGED')msg(e.message)}
}
function resetEmailVerificationView(user){
  if(emailProofOwner&&emailProofOwner!==user?.id)emailProofToken='';
  emailProofOwner=user?.id??null;
  const version=++emailProofVersion;
  el('email-verification').hidden=true;
  el('email-verification-status').textContent='';
  el('email-verification-confirm').hidden=true;
  void refreshEmailProof(version);
}
captureEmailProof();
addEventListener('hashchange',captureEmailProof);
el('email-verification-request').onclick=()=>act(async()=>{
  const version=emailProofVersion,button=el('email-verification-request');
  if(button.disabled)return;button.disabled=true;
  try{const r=await api('/auth/email-verification/request','POST');if(version===emailProofVersion)msg(r.message)}
  finally{button.disabled=false}
});
el('email-verification-confirm').onclick=()=>act(async()=>{
  const version=emailProofVersion,button=el('email-verification-confirm');
  if(button.disabled||!emailProofToken)return;button.disabled=true;
  const secret=emailProofToken;emailProofToken='';button.hidden=true;
  try{await api('/auth/email-verification/confirm','POST',{token:secret});if(version===emailProofVersion){msg('Adres e-mail potwierdzony.');await refreshEmailProof(version)}}
  finally{button.disabled=false}
});
(async()=>{try{
  const r=await fetch('/auth/email-verification/options',{cache:'no-store'});
  if(!r.ok)return;emailProofEnabled=(await r.json()).enabled===true;
  await refreshEmailProof(emailProofVersion);
}catch(_e){/* Optional feature remains hidden. */}})();
