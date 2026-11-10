"use strict";
let adminSellerRequest=0,adminSellerBusy=false,adminSellerOffset=0,adminSellerMore=false;
const adminSellerLabels={pending:'Oczekuje',approved:'Zatwierdzony testowo',needs_information:'Do wyjaśnienia',rejected:'Odrzucony testowo'};
function clearAdminSellerRows(){
  const host=el('admin-seller-results');
  for(const old of host.querySelectorAll('*')){if('value' in old)old.value='';old.textContent=''}
  host.replaceChildren();adminSellerMore=false;
}
function adminSellerButtons(){
  const disabled=role!=='admin'||adminSellerBusy;
  el('admin-seller-refresh').disabled=disabled;el('admin-seller-filter').disabled=disabled;
  el('admin-seller-previous').disabled=disabled||adminSellerOffset===0;
  el('admin-seller-next').disabled=disabled||!adminSellerMore||adminSellerOffset+20>10000;
}
function resetAdminSellerReview(user){
  adminSellerRequest++;adminSellerBusy=false;adminSellerOffset=0;clearAdminSellerRows();
  el('admin-seller-filter').value='pending';el('admin-seller-status').textContent='';
  el('admin-seller-review').hidden=user?.role!=='admin';
  for(const id of ['admin-seller-refresh','admin-seller-filter','admin-seller-previous','admin-seller-next'])el(id).disabled=true;
  el('admin-seller-refresh').disabled=user?.role!=='admin';el('admin-seller-filter').disabled=user?.role!=='admin';
}
async function loadAdminSellerQueue(){
  if(adminSellerBusy||role!=='admin'||!token)return;
  const epoch=sessionEpoch,request=++adminSellerRequest,offset=adminSellerOffset;
  adminSellerBusy=true;clearAdminSellerRows();adminSellerButtons();el('admin-seller-status').textContent='Pobieranie profili…';
  try{
    const params=new URLSearchParams({limit:'20',offset:String(offset)});
    if(el('admin-seller-filter').value)params.set('status',el('admin-seller-filter').value);
    const data=await api('/admin/farmers/compliance-queue?'+params.toString());
    if(epoch!==sessionEpoch||request!==adminSellerRequest||role!=='admin')return;
    if(data.mode!=='test'||!Array.isArray(data.profiles)||data.profiles.length>20||!Number.isSafeInteger(data.total)||data.total<0||data.offset!==offset||data.limit!==20||typeof data.has_more!=='boolean')throw Error('Nieprawidłowa odpowiedź kolejki.');
    for(const profile of data.profiles){
      if(!Number.isSafeInteger(profile.farmer_id)||profile.farmer_id<1||!Object.hasOwn(adminSellerLabels,profile.review_status)||typeof profile.rules_version!=='string'||!(profile.reviewed_at===null||typeof profile.reviewed_at==='string'))throw Error('Nieprawidłowy profil w kolejce.');
    }
    adminSellerMore=data.has_more;
    el('admin-seller-status').textContent=`Profile: ${data.total}. Strona ${Math.floor(offset/20)+1}. `+(data.profiles.length?'':'Brak profili dla wybranego filtra.');
    for(const profile of data.profiles){
      const card=node('article','','card');card.append(node('h3',`Rolnik #${profile.farmer_id}`),node('p',`Stan: ${adminSellerLabels[profile.review_status]}; zasady: ${profile.rules_version}`));
      const choice=node('select');choice.setAttribute('aria-label',`Decyzja dla rolnika ${profile.farmer_id}`);
      for(const value of ['approved','needs_information','rejected']){const option=node('option',adminSellerLabels[value]);option.value=value;choice.append(option)}
      const reason=node('textarea');reason.maxLength=500;reason.setAttribute('aria-label',`Uzasadnienie testowe dla rolnika ${profile.farmer_id}`);
      const label=node('label','Uzasadnienie testowe (3–500 znaków)');label.append(reason);
      const button=node('button','Zapisz decyzję testową');button.type='button';
      button.onclick=()=>saveAdminSellerReview(profile,choice.value,reason,card,epoch,request);
      card.append(choice,label,button);el('admin-seller-results').append(card);
    }
  }catch(error){
    if(epoch!==sessionEpoch||request!==adminSellerRequest||error.message==='SESSION_CHANGED')return;
    clearAdminSellerRows();el('admin-seller-status').textContent=error.message+' Odśwież kolejkę.';
  }finally{if(request===adminSellerRequest){adminSellerBusy=false;adminSellerButtons()}}
}
async function saveAdminSellerReview(profile,decision,reason,card,epoch,request){
  if(adminSellerBusy||role!=='admin'||!token||epoch!==sessionEpoch||request!==adminSellerRequest||!card.isConnected)return;
  const text=reason.value.trim();
  if(text.length<3||text.length>500||!['approved','needs_information','rejected'].includes(decision)){el('admin-seller-status').textContent='Wpisz uzasadnienie testowe od 3 do 500 znaków.';return}
  adminSellerBusy=true;adminSellerButtons();reason.value='';
  for(const control of el('admin-seller-results').querySelectorAll('button,select,textarea'))control.disabled=true;
  el('admin-seller-status').textContent='Zapisywanie decyzji…';
  try{
    await api(`/admin/farmers/${profile.farmer_id}/compliance/review`,'POST',{decision,reason:text,expected_rules_version:profile.rules_version,expected_review_status:profile.review_status,expected_reviewed_at:profile.reviewed_at});
    if(epoch!==sessionEpoch||request!==adminSellerRequest||role!=='admin')return;
    clearAdminSellerRows();el('admin-seller-status').textContent='Decyzja testowa zapisana. Odśwież kolejkę. Rzeczywiste wypłaty pozostają wyłączone.';
  }catch(error){
    if(epoch!==sessionEpoch||request!==adminSellerRequest||error.message==='SESSION_CHANGED')return;
    clearAdminSellerRows();el('admin-seller-status').textContent=error.message+' Odśwież kolejkę; po utracie odpowiedzi decyzja mogła zostać zapisana.';
  }finally{if(request===adminSellerRequest){adminSellerBusy=false;adminSellerButtons()}}
}
el('admin-seller-refresh').onclick=loadAdminSellerQueue;
el('admin-seller-filter').onchange=()=>{if(adminSellerBusy)return;adminSellerOffset=0;return loadAdminSellerQueue()};
el('admin-seller-previous').onclick=()=>{if(adminSellerBusy)return;adminSellerOffset=Math.max(0,adminSellerOffset-20);return loadAdminSellerQueue()};
el('admin-seller-next').onclick=()=>{if(adminSellerBusy||!adminSellerMore||adminSellerOffset+20>10000)return;adminSellerOffset+=20;return loadAdminSellerQueue()};
