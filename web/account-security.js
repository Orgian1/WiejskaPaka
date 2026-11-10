let passwordChangeRequest=0;
function resetPasswordChangeView(user){
  passwordChangeRequest++;
  el('account-security').hidden=!user;
  el('change-password').reset();
  el('change-password-submit').disabled=false;
}
el('change-password').onsubmit=async event=>{
  event.preventDefault();const button=el('change-password-submit');
  if(button.disabled||!token||!role)return;
  const epoch=sessionEpoch,request=++passwordChangeRequest;
  const current=el('current-password').value,next=el('next-password').value,repeat=el('repeat-password').value;
  el('change-password').reset();
  if(next!==repeat){msg('Nowe hasła muszą być takie same.');return}
  if(!current||current.length>256||next.length<12||next.length>256){msg('Podaj obecne hasło i nowe hasło o długości od 12 do 256 znaków.');return}
  if(current===next){msg('Nowe hasło musi różnić się od obecnego.');return}
  button.disabled=true;
  try{
    const result=await api('/auth/change-password','POST',{current_password:current,new_password:next});
    if(epoch!==sessionEpoch||request!==passwordChangeRequest)return;
    if(result.changed!==true||result.reauthentication_required!==true)throw Error('Nie udało się potwierdzić zmiany hasła. Sprawdź możliwość ponownego logowania.');
    loginAttempt++;sessionEpoch++;token=null;logged(null);
    msg('Hasło zmienione. Wszystkie sesje zostały wylogowane. Zaloguj się nowym hasłem.');
  }catch(error){
    if(epoch!==sessionEpoch||request!==passwordChangeRequest||error.message==='SESSION_CHANGED')return;
    msg(error.message+' Po utracie odpowiedzi sprawdź logowanie nowym hasłem.');
  }finally{
    if(request===passwordChangeRequest)button.disabled=false;
  }
};
