let sessionSecurityRequest=0,sessionSecurityBusy=false;
const sessionSecurityButtons=['sessions-refresh','sessions-logout-others','sessions-logout-all'];
function resetSessionSecurityView(user){
  sessionSecurityRequest++;sessionSecurityBusy=false;
  el('sessions-status').textContent='';
  for(const id of sessionSecurityButtons)el(id).disabled=!user;
}
async function manageSessions(action){
  if(sessionSecurityBusy||!token||!role)return;
  const epoch=sessionEpoch,request=++sessionSecurityRequest;
  sessionSecurityBusy=true;
  for(const id of sessionSecurityButtons)el(id).disabled=true;
  el('sessions-status').textContent='Sprawdzanie sesji…';
  try{
    const data=await api(action==='refresh'?'/auth/sessions':action==='others'?'/auth/logout-others':'/auth/logout-all',action==='refresh'?'GET':'POST');
    if(epoch!==sessionEpoch||request!==sessionSecurityRequest)return;
    if(action==='all'){
      if(data.ok!==true)throw Error('Nie potwierdzono wylogowania.');
      loginAttempt++;sessionEpoch++;token=null;logged(null);msg('Wszystkie sesje zostały wylogowane.');return;
    }
    if(action==='others'){
      if(data.ok!==true||data.other_sessions!==0)throw Error('Nie potwierdzono wylogowania pozostałych sesji.');
      el('sessions-status').textContent='Pozostałe sesje zostały wylogowane. Bieżąca sesja pozostaje aktywna.';
    }else{
      if(!Number.isSafeInteger(data.active_sessions)||data.active_sessions<1||!Number.isSafeInteger(data.other_sessions)||data.other_sessions!==data.active_sessions-1)throw Error('Nieprawidłowa odpowiedź o sesjach.');
      el('sessions-status').textContent=`Aktywne sesje: ${data.active_sessions}. Pozostałe: ${data.other_sessions}. Stan w chwili sprawdzenia.`;
    }
  }catch(error){
    if(epoch!==sessionEpoch||request!==sessionSecurityRequest||error.message==='SESSION_CHANGED')return;
    el('sessions-status').textContent=error.message+(action==='refresh'?'':' Po utracie odpowiedzi sprawdź sesje ponownie; operacja mogła zostać wykonana.');
  }finally{
    if(request===sessionSecurityRequest){sessionSecurityBusy=false;for(const id of sessionSecurityButtons)el(id).disabled=false}
  }
}
el('sessions-refresh').onclick=()=>manageSessions('refresh');
el('sessions-logout-others').onclick=()=>manageSessions('others');
el('sessions-logout-all').onclick=()=>manageSessions('all');
