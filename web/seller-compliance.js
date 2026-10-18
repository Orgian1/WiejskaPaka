"use strict";
let sellerComplianceRequest=0,sellerComplianceBusy=false,sellerRulesVersion=null,sellerRulesAcknowledged=false;
function resetSellerComplianceView(user){
  sellerComplianceRequest++;sellerComplianceBusy=false;sellerRulesVersion=null;sellerRulesAcknowledged=false;
  el('seller-compliance').hidden=user?.role!=='rolnik';
  el('seller-compliance-status').textContent='';
  el('seller-rules-check').checked=false;el('seller-rules-check').disabled=true;
  el('seller-rules-submit').disabled=true;
  el('seller-compliance-refresh').disabled=user?.role!=='rolnik';
}
function sellerComplianceButtons(){
  const available=role==='rolnik'&&!sellerComplianceBusy;
  el('seller-compliance-refresh').disabled=!available;
  el('seller-rules-check').disabled=!available||!sellerRulesVersion||sellerRulesAcknowledged;
  el('seller-rules-submit').disabled=!available||!sellerRulesVersion||sellerRulesAcknowledged||!el('seller-rules-check').checked;
}
async function manageSellerCompliance(acknowledge=false){
  if(sellerComplianceBusy||!token||role!=='rolnik')return;
  if(acknowledge&&(!sellerRulesVersion||sellerRulesAcknowledged||!el('seller-rules-check').checked))return;
  const epoch=sessionEpoch,request=++sellerComplianceRequest;
  sellerComplianceBusy=true;sellerComplianceButtons();
  el('seller-compliance-status').textContent='Sprawdzanie profilu…';
  try{
    const data=await api('/farmers/me/compliance'+(acknowledge?'/acknowledge':''),acknowledge?'POST':'GET',acknowledge?{rules_version:sellerRulesVersion,accepted:true}:undefined);
    if(epoch!==sessionEpoch||request!==sellerComplianceRequest||role!=='rolnik')return;
    if(!Number.isSafeInteger(data.completed_transaction_count)||data.completed_transaction_count<0||data.profile_reminder_threshold!==20||typeof data.profile_reminder_due!=='boolean'||typeof data.rules_acknowledged!=='boolean'||typeof data.current_rules_version!=='string'||!data.current_rules_version||!['not_started','pending','approved','needs_information','rejected'].includes(data.review_status))throw Error('Nieprawidłowa odpowiedź o profilu.');
    sellerRulesVersion=data.current_rules_version;sellerRulesAcknowledged=data.rules_acknowledged&&data.rules_version===data.current_rules_version;
    el('seller-rules-check').checked=false;
    const labels={not_started:'jeszcze nie rozpoczęto',pending:'oczekuje na przegląd testowy',approved:'zatwierdzony testowo',needs_information:'wymaga wyjaśnienia',rejected:'odrzucony testowo'};
    el('seller-compliance-status').textContent=`Zakończone transakcje: ${data.completed_transaction_count}. Stan profilu: ${labels[data.review_status]}. `+(data.profile_reminder_due?'Osiągnięto próg 20 transakcji — przypomnienie o przeglądzie profilu. ':'')+(sellerRulesAcknowledged?'Zasady demo potwierdzone.':'Zaznacz zapoznanie się z zasadami, aby je potwierdzić.')+' Rzeczywiste wypłaty są wyłączone.';
  }catch(error){
    if(epoch!==sessionEpoch||request!==sellerComplianceRequest||error.message==='SESSION_CHANGED')return;
    sellerRulesVersion=null;sellerRulesAcknowledged=false;el('seller-rules-check').checked=false;
    el('seller-compliance-status').textContent=error.message+(acknowledge?' Sprawdź stan profilu ponownie; potwierdzenie mogło zostać zapisane.':' Spróbuj ponownie sprawdzić stan profilu.');
  }finally{
    if(request===sellerComplianceRequest){sellerComplianceBusy=false;sellerComplianceButtons()}
  }
}
el('seller-compliance-refresh').onclick=()=>manageSellerCompliance();
el('seller-rules-check').onchange=sellerComplianceButtons;
el('seller-rules-submit').onclick=()=>manageSellerCompliance(true);
