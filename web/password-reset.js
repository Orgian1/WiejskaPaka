// Reset links use fragments: browsers never send the secret in an HTTP URL.
(async()=>{
  const section=el('password-reset-section'),status=el('reset-status');
  let incoming=null,enabled=false;
  function captureResetFragment(){
    if(!location.hash.startsWith('#reset-token='))return;
    incoming=location.hash.slice('#reset-token='.length);
    history.replaceState(null,'',location.pathname+location.search);
    if(enabled){
      el('reset-token').value=/^[A-Za-z0-9_-]{43}$/.test(incoming)?incoming:'';
      incoming=null;
    }
  }
  captureResetFragment();
  globalThis.addEventListener('hashchange',captureResetFragment);
  async function post(path,body){
    const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body),cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer'});
    if(!response.ok){
      if(response.status===429)throw Error('Zbyt wiele prób. Spróbuj za 15 minut.');
      if(response.status===400)throw Error('Link jest nieprawidłowy, wykorzystany lub wygasł. Poproś o nowy.');
      throw Error('Nie udało się potwierdzić operacji. Sprawdź połączenie.');
    }
    return response.json();
  }
  try{
    const response=await fetch('/auth/password-reset-test/options',{cache:'no-store',credentials:'omit'});
    if(!response.ok||!(await response.json()).enabled)return;
    enabled=true;section.hidden=false;
    if(incoming&&/^[A-Za-z0-9_-]{43}$/.test(incoming))el('reset-token').value=incoming;
  }catch(_e){return}
  finally{incoming=null}
  el('request-password-reset').onsubmit=async event=>{
    event.preventDefault();const button=el('request-reset-submit');if(button.disabled)return;
    const email=el('reset-email').value.trim(),epoch=sessionEpoch;
    el('request-password-reset').reset();button.disabled=true;status.textContent='';
    try{
      await post('/auth/password-reset-test/request',{email});
      if(epoch===sessionEpoch)status.textContent='Jeśli adres jest przypisany do konta, otrzymasz instrukcję zmiany hasła.';
    }catch(_e){if(epoch===sessionEpoch)status.textContent='Nie udało się potwierdzić wysłania instrukcji. Sprawdź połączenie.'}
    finally{button.disabled=false}
  };
  el('confirm-password-reset').onsubmit=async event=>{
    event.preventDefault();const button=el('confirm-reset-submit');if(button.disabled)return;
    const secret=el('reset-token').value,next=el('reset-new-password').value,
      repeat=el('reset-repeat-password').value,epoch=sessionEpoch;
    if(next!==repeat){status.textContent='Nowe hasła muszą być takie same.';return}
    if(!/^[A-Za-z0-9_-]{43}$/.test(secret)||next.length<12||next.length>256){
      status.textContent='Sprawdź kod z linku i długość nowego hasła (12–256 znaków).';return;
    }
    el('confirm-password-reset').reset();button.disabled=true;status.textContent='';
    try{
      const result=await post('/auth/password-reset-test/confirm',{token:secret,new_password:next});
      if(epoch!==sessionEpoch)return;
      if(result.changed!==true||result.reauthentication_required!==true)throw Error('Nie potwierdzono zmiany hasła.');
      loginAttempt++;sessionEpoch++;token=null;logged(null);
      status.textContent='Hasło zmienione. Wszystkie sesje wylogowane. Zaloguj się nowym hasłem.';
    }catch(error){if(epoch===sessionEpoch)status.textContent=error.message+' Po utracie odpowiedzi sprawdź logowanie nowym hasłem.'}
    finally{button.disabled=false}
  };
})();
