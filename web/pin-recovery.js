// PIN and reauthentication password exist only in the current view/request.
function resetPinRecoveryViews(){
  for(const view of document.querySelectorAll('[data-pin-recovery]')){
    if(typeof view._clearPinRecovery==='function')view._clearPinRecovery();
  }
}
function pinRecoveryControls(kind,id){
  const host=node('div');host.dataset.pinRecovery='true';
  if(role!=='klient'||!['order','shipment'].includes(kind))return host;
  const button=node('button','Odzyskaj PIN istniejącego zakupu (TEST)');button.type='button';
  let version=0,timer=null;
  const clear=()=>{
    version++;if(timer!==null)clearTimeout(timer);timer=null;
    for(const input of host.querySelectorAll('input'))input.value='';
    for(const text of host.querySelectorAll('p'))text.textContent='';
    host.replaceChildren(button);button.disabled=false;
  };
  host._clearPinRecovery=clear;
  button.onclick=()=>{
    if(role!=='klient')return;
    clear();const epoch=sessionEpoch;
    const form=node('form'),label=node('label','Potwierdź hasłem konta: '),password=node('input');
    password.type='password';password.required=true;password.maxLength=256;
    password.autocomplete='current-password';password.setAttribute('aria-label','Hasło do odzyskania PIN-u');
    label.append(password);
    const info=node('p','Dostępne do 24 godzin od zakupu, przed wykorzystaniem lub blokadą PIN-u. Maksymalnie 5 prób na konto w 15 minut. PIN zniknie z ekranu po 30 sekundach. Nie twórz drugiego zamówienia.');
    const submit=node('button','Pokaż PIN testowy');submit.type='submit';
    const cancel=node('button','Zamknij i ukryj PIN');cancel.type='button';cancel.onclick=clear;
    const output=node('p');output.setAttribute('role','status');output.setAttribute('aria-live','polite');
    form.append(info,label,submit,cancel,output);host.replaceChildren(form);password.focus();
    timer=setTimeout(clear,120000);
    form.onsubmit=async event=>{
      event.preventDefault();if(submit.disabled)return;
      if(epoch!==sessionEpoch||role!=='klient'||!host.isConnected){clear();return}
      const entered=password.value;password.value='';
      if(!entered){output.textContent='Podaj hasło konta.';return}
      submit.disabled=true;const request=++version;
      if(timer!==null)clearTimeout(timer);
      const active=()=>epoch===sessionEpoch&&role==='klient'&&request===version&&host.isConnected;
      timer=setTimeout(clear,30000); // also close a stalled request
      try{
        const result=await api(`/${kind==='order'?'orders':'shipments'}/${encodeURIComponent(id)}/recover-pin-test`,'POST',{password:entered});
        if(!active())return;
        if(result.mode!=='test'||typeof result.pin_test_only!=='string'||!/^[0-9]{6}$/.test(result.pin_test_only))throw Error('Nie można bezpiecznie wyświetlić PIN-u. Sprawdź istniejący zakup.');
        output.textContent='PIN TESTOWY: '+result.pin_test_only+'. Sprawdź towar przed jego przekazaniem. Zakup już istnieje.';
        clearTimeout(timer);timer=setTimeout(clear,30000);
      }catch(error){
        if(!active()||error.message==='SESSION_CHANGED')return;
        output.textContent=error.message;submit.disabled=false;
      }
    };
  };
  host.append(button);return host;
}
document.addEventListener('visibilitychange',()=>{if(document.hidden)resetPinRecoveryViews()});
globalThis.addEventListener('pagehide',resetPinRecoveryViews);
