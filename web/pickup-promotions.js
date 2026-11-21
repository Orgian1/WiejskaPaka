"use strict";
let pickupPromoSerial=0;
const pickupShortcuts=document.createElement('div');
pickupShortcuts.id='seller-pickup-shortcuts';
pickupShortcuts.hidden=true;
const sellerPointNav=el('seller-point-nav');
sellerPointNav.before(pickupShortcuts);
const pickupPromoShortcut=node('button','Kod rabatowy');
pickupPromoShortcut.type='button';
pickupPromoShortcut.id='seller-promo-shortcut';
pickupShortcuts.append(sellerPointNav,pickupPromoShortcut);

pickupPromoShortcut.onclick=()=>{
  if(role!=='rolnik')return;
  const input=el('pickup-promo-code');
  if(!input.value)input.value=pickupPromoShortcut.dataset.code||'';
  navigateApp('points');
  input.focus();
};

async function refreshPickupPromoShortcut(epoch,serial){
  try{
    const {code,kind}=await api('/farmers/me/pickup-promotions/featured');
    if(epoch!==sessionEpoch||serial!==pickupPromoSerial||role!=='rolnik')return;
    pickupPromoShortcut.dataset.code=code||'';
    pickupPromoShortcut.textContent=kind==='seventh'
      ? 'Siódmy punkt gratis na 30 dni: '+code
      : code?'Kod rabatowy: '+code:'Kod rabatowy';
  }catch(_error){/* Manual entry remains available. */}
}
function pickupPromoSettings(form){return {expires_on:form.elements.expires_on.value,max_redemptions:Number(form.elements.max_redemptions.value),active:form.elements.active.checked}}
async function refreshPickupPromotions(){
  const epoch=sessionEpoch,serial=++pickupPromoSerial;
  el('pickup-promotions-admin').hidden=role!=='admin';el('pickup-promo-seller').hidden=role!=='rolnik';
  el('pickup-promotions-list').replaceChildren();el('pickup-promo-grants').replaceChildren();
  if(role==='rolnik'){
    void refreshPickupPromoShortcut(epoch,serial);
    const data=await api('/farmers/me/pickup-promotions');if(epoch!==sessionEpoch||serial!==pickupPromoSerial)return;
    el('pickup-promo-status').textContent=`Dostępne darmowe punkty z promocji: ${data.available_points}. Demo nie nalicza opłat za pozostałe punkty.`;
    for(const grant of data.items){
      const terms=grant.granted_points===1
        ? 'Darmowy siódmy punkt na 30 dni. Przy dodaniu musisz mieć sześć jednocześnie aktywnych punktów.'
        : 'Trzy darmowe punkty.';
      el('pickup-promo-grants').append(node('p',`${grant.code}: ${terms} Pozostało ${grant.remaining} z ${grant.granted_points}, do ${grant.expires_on} włącznie (czas polski).`));
    }
  }else if(role==='admin'){
    const data=await api('/admin/pickup-promotions');if(epoch!==sessionEpoch||serial!==pickupPromoSerial)return;
    for(const promo of data.items){
      const form=node('form','', 'card');
      const terms=promo.kind==='seventh'?'Siódmy punkt gratis na 30 dni.':'Trzy darmowe punkty na 30 dni.';
      form.append(node('h3',promo.code),node('p',`${terms} Wykorzystania: ${promo.redemption_count}.`));
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
  pickupPromoSerial++;
  pickupShortcuts.hidden=role!=='rolnik';
  sellerPointNav.open=false;
  pickupPromoShortcut.dataset.code='';
  pickupPromoShortcut.textContent='Kod rabatowy';
  el('pickup-promo-redeem-form').reset();el('pickup-promo-create-form').reset();
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
const pickupPromoCreate=el('pickup-promo-create-form');
const pickupPromoKindLabel=node('label','Rodzaj promocji');
const pickupPromoKind=node('select');
pickupPromoKind.name='kind';
for(const [value,title] of [['starter','Trzy darmowe punkty'],['seventh','Siódmy aktywny punkt gratis']]){
  const option=node('option',title);option.value=value;pickupPromoKind.append(option);
}
pickupPromoKindLabel.append(pickupPromoKind);
pickupPromoCreate.prepend(pickupPromoKindLabel);
el('pickup-promotions-admin').querySelector('h2').textContent='Kody na darmowe punkty odbioru';
el('pickup-promo-seller').querySelector('h3').textContent='Kody promocyjne na punkty odbioru';
el('pickup-promo-seller').querySelector('p').textContent=
  'Promocja startowa obejmuje trzy punkty. Po ich wykorzystaniu możesz dostać siódmy aktywny punkt gratis. Każdy punkt jest darmowy przez 30 dni od aktywacji.';

el('pickup-promo-create-form').onsubmit=event=>{
  event.preventDefault();const form=event.currentTarget;
  act(()=>singleWrite('promo-create',el('pickup-promo-create-submit'),async()=>{
    const epoch=sessionEpoch;await api('/admin/pickup-promotions','POST',{code:form.elements.code.value,kind:form.elements.kind.value,...pickupPromoSettings(form)});
    if(epoch!==sessionEpoch)return;form.reset();msg('Kod promocyjny utworzony.');await refreshPickupPromotions();
  }));
};
