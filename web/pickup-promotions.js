"use strict";
let pickupPromoSerial=0;
function pickupPromoSettings(form){return {expires_on:form.elements.expires_on.value,max_redemptions:Number(form.elements.max_redemptions.value),active:form.elements.active.checked}}
async function refreshPickupPromotions(){
  const epoch=sessionEpoch,serial=++pickupPromoSerial;
  el('pickup-promotions-admin').hidden=role!=='admin';el('pickup-promo-seller').hidden=role!=='rolnik';
  el('pickup-promotions-list').replaceChildren();el('pickup-promo-grants').replaceChildren();
  if(role==='rolnik'){
    const data=await api('/farmers/me/pickup-promotions');if(epoch!==sessionEpoch||serial!==pickupPromoSerial)return;
    el('pickup-promo-status').textContent=`Dostępne darmowe punkty z promocji: ${data.available_points}. Demo nie nalicza opłat za pozostałe punkty.`;
    for(const grant of data.items)el('pickup-promo-grants').append(node('p',`${grant.code}: pozostało ${grant.remaining} z 3 punktów, do ${grant.expires_on} włącznie (czas polski).`));
  }else if(role==='admin'){
    const data=await api('/admin/pickup-promotions');if(epoch!==sessionEpoch||serial!==pickupPromoSerial)return;
    for(const promo of data.items){
      const form=node('form','', 'card');form.append(node('h3',promo.code),node('p',`Wykorzystania: ${promo.redemption_count}. Każde konto może użyć kodu raz i otrzymać 3 punkty.`));
      for(const [name,title,type,value] of [['expires_on','Termin nowych realizacji kodu','date',promo.expires_on],['max_redemptions','Łączny limit kont','number',promo.max_redemptions]]){
        const label=node('label',title),input=node('input');input.name=name;input.type=type;input.value=String(value);input.required=true;if(type==='number'){input.min=String(Math.max(1,promo.redemption_count));input.max='1000000'}label.append(input);form.append(label);
      }
      const active=node('input');active.type='checkbox';active.name='active';active.checked=Boolean(promo.active);const label=node('label','Kod aktywny dla nowych kont');label.append(active);form.append(label);
      const save=node('button','Zapisz ustawienia kodu');save.type='submit';form.append(save);
      form.onsubmit=event=>{event.preventDefault();act(()=>singleWrite('promo-settings:'+promo.code,save,async()=>{
        await api('/admin/pickup-promotions/'+encodeURIComponent(promo.code),'PUT',pickupPromoSettings(form));if(epoch!==sessionEpoch)return;
        msg('Ustawienia zapisane. Wcześniej przyznane uprawnienia zachowują swój termin.');await refreshPickupPromotions();
      }))};el('pickup-promotions-list').append(form);
    }
  }
}
function resetPickupPromotionViews(){
  pickupPromoSerial++;el('pickup-promo-redeem-form').reset();el('pickup-promo-create-form').reset();
  el('pickup-promo-status').textContent='';el('pickup-promo-grants').replaceChildren();el('pickup-promotions-list').replaceChildren();
  el('pickup-promotions-admin').hidden=role!=='admin';el('pickup-promo-seller').hidden=role!=='rolnik';
  if(['admin','rolnik'].includes(role))act(refreshPickupPromotions);
}
el('pickup-promo-redeem-form').onsubmit=event=>{
  event.preventDefault();const button=el('pickup-promo-redeem-submit');
  act(()=>singleWrite('promo-redeem',button,async()=>{
    const epoch=sessionEpoch;await api('/farmers/me/pickup-promotions/redeem','POST',{code:el('pickup-promo-code').value});
    if(epoch!==sessionEpoch)return;el('pickup-promo-code').value='';msg('Kod zrealizowany. Powtórzenie tego samego kodu nie przyznaje kolejnych punktów.');await refreshPickupPromotions();
  }));
};
el('pickup-promo-create-form').onsubmit=event=>{
  event.preventDefault();const form=event.currentTarget;
  act(()=>singleWrite('promo-create',el('pickup-promo-create-submit'),async()=>{
    const epoch=sessionEpoch;await api('/admin/pickup-promotions','POST',{code:form.elements.code.value,...pickupPromoSettings(form)});
    if(epoch!==sessionEpoch)return;form.reset();msg('Kod promocyjny utworzony.');await refreshPickupPromotions();
  }));
};
