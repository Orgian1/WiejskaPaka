// Private delivery drafts remain in memory/DOM and are cleared on account changes.
let addressDeliveryEnabled=false,deliveryViewSerial=0,deliveryCartFields=null,deliveryCartFarmer=null,deliveryNextBefore=null;
const deliveryDays=['Poniedziałek','Wtorek','Środa','Czwartek','Piątek','Sobota','Niedziela'];
const deliveryStates={pending:'Oczekuje na akceptację sprzedawcy',accepted:'Zaakceptowana',declined:'Odrzucona'};
function deliveryLabel(text,input){const label=node('label',text);label.append(input);return label}
function addressDeliveryFields(farmerId){
  if(!addressDeliveryEnabled)return null;
  const area=node('fieldset');area.append(node('legend','Termin dostawy do domu'));
  const select=node('select'),day=node('input'),from=node('input'),to=node('input'),phone=node('input'),status=node('p');
  select.append(node('option','Wybierz miejscowość, dzień i godziny sprzedawcy'));select.firstChild.value='';
  day.type='date';from.type='time';to.type='time';phone.type='tel';phone.autocomplete='tel';phone.maxLength=24;
  select.setAttribute('aria-label','Termin dostawy sprzedawcy');day.setAttribute('aria-label','Data dostawy');
  from.setAttribute('aria-label','Odbiorę w domu od godziny');to.setAttribute('aria-label','Odbiorę w domu do godziny');phone.setAttribute('aria-label','Prywatny numer telefonu klienta');
  area.append(deliveryLabel('Dostępne terminy sprzedawcy',select),deliveryLabel('Data dostawy',day),
    deliveryLabel('Mogę odebrać od godziny',from),deliveryLabel('Mogę odebrać do godziny',to),
    deliveryLabel('Numer telefonu',phone),node('p','Numer telefonu pozostaje prywatny. Nie jest wyświetlany sprzedawcy ani dostawcy.'),
    node('p','Sprzedawca musi zaakceptować dostawę. Rezerwacja bez płatności trwa 30 minut.'),status);
  const epoch=sessionEpoch;
  api(`/farmers/${farmerId}/delivery-windows`).then(data=>{
    if(epoch!==sessionEpoch||!area.isConnected)return;
    for(const slot of data.items){const option=node('option',`${slot.city}, ${slot.postal_code} — ${deliveryDays[slot.weekday]}, ${slot.from_time}–${slot.to_time}`);option.value=slot.id;select.append(option)}
    status.textContent=data.items.length?'Wybierz zgodny dzień, datę i godziny dostępności w domu.':'Sprzedawca nie podał dostępnych terminów dostawy na adres.';
  }).catch(()=>{if(epoch===sessionEpoch&&area.isConnected)status.textContent='Nie udało się pobrać terminów. Odśwież ofertę.'});
  return {element:area,payload:()=>{
    if(!select.value||!day.value||!from.value||!to.value||!phone.value.trim())throw Error('Wybierz termin, datę, godziny odbioru i podaj numer telefonu.');
    return {window_id:select.value,delivery_date:day.value,available_from:from.value,available_to:to.value,phone:phone.value.trim()};
  }};
}
function refreshDeliveryCartFields(farmer){
  const host=el('cart-delivery-preferences');if(!host)return;
  if(!addressDeliveryEnabled||!farmer){host.replaceChildren();deliveryCartFields=null;deliveryCartFarmer=null;return;}
  if(deliveryCartFarmer===farmer&&deliveryCartFields)return;
  host.replaceChildren();deliveryCartFarmer=farmer;deliveryCartFields=addressDeliveryFields(farmer);
  if(deliveryCartFields)host.append(deliveryCartFields.element);
}
function resetAddressDeliveryViews(){
  deliveryViewSerial++;deliveryCartFields=null;deliveryCartFarmer=null;deliveryNextBefore=null;
  if(el('address-delivery-panel')){el('address-delivery-panel').hidden=true;el('delivery-requests').replaceChildren();el('delivery-window-list').replaceChildren();el('delivery-window-form').reset();el('delivery-view-status').textContent='';}
  if(el('cart-delivery-preferences'))el('cart-delivery-preferences').replaceChildren();
}
async function loadAddressDeliveryViews(before=null){
  if(!el('address-delivery-panel'))return;
  const visible=addressDeliveryEnabled&&['klient','rolnik'].includes(role);
  el('address-delivery-panel').hidden=!visible;if(!visible)return;
  const serial=++deliveryViewSerial,epoch=sessionEpoch,actor=role;
  const current=()=>serial===deliveryViewSerial&&epoch===sessionEpoch&&role===actor;
  el('delivery-settings-tab').hidden=actor!=='rolnik';el('delivery-settings-view').hidden=true;
  el('delivery-requests-view').hidden=false;el('delivery-view-status').textContent='Pobieranie dostaw…';
  try{
    const data=await api('/address-delivery/requests/mine'+(before?'?before='+String(before):''));if(!current())return;
    deliveryNextBefore=data.next_before;el('delivery-view-next').hidden=!deliveryNextBefore;
    const host=el('delivery-requests');host.replaceChildren();const seen=new Set();
    for(const request of data.items){
      const key=request.shipment_id||String(request.order_id);if(seen.has(key))continue;seen.add(key);
      const card=node('article','', 'card');card.append(node('h3',request.shipment_id?'Przesyłka '+request.shipment_id:'Zamówienie '+request.pickup_code),
        node('p',`${request.delivery_city}, ${request.delivery_street}, ${request.delivery_postal_code}`),
        node('p',`Data: ${request.delivery_date} • dostępność klienta: ${coordinateTime(request.customer_from)}–${coordinateTime(request.customer_to)}`),
        node('p',`Wspólne godziny dostawy: ${coordinateTime(request.agreed_from)}–${coordinateTime(request.agreed_to)}`),
        node('p',`${deliveryStates[request.state]||request.state} • status zamówienia: ${request.status}`));
      for(const item of data.items.filter(x=>(x.shipment_id||String(x.order_id))===key)){
        card.append(node('p',`${item.product_name||'Produkt'} • ilość: ${item.quantity} • ${money(item.total_grosze)}`));
      }
      if(actor==='rolnik'&&request.state==='pending'&&request.status==='oczekuje_na_platnosc_testowa'){
        const buttons=[];
        for(const [decision,label] of [['accepted','Akceptuję dostawę'],['declined','Odrzucam dostawę']]){
          const button=node('button',label);button.type='button';buttons.push(button);
          button.onclick=()=>act(async()=>{
            if(!current()||button.disabled)return;buttons.forEach(b=>b.disabled=true);
            try{await api(`/address-delivery/requests/${request.order_id}/decision`,'POST',{decision,revision:request.revision});if(current()){await loadAddressDeliveryViews();await loadOrders();await loadDashboard();}}
            finally{if(current())buttons.forEach(b=>b.disabled=false)}
          });card.append(button);
        }
      }
      host.append(card);
    }
    if(!data.items.length)host.append(node('p','Brak zamówień z terminem dostawy na adres.'));
    el('delivery-view-status').textContent='';
    if(actor==='rolnik'){
      const windows=await api('/address-delivery/windows/mine');if(!current())return;
      const list=el('delivery-window-list');list.replaceChildren();
      for(const slot of windows.items){const row=node('article','', 'card');row.append(node('p',`${slot.city}, ${slot.postal_code} — ${deliveryDays[slot.weekday]}, ${slot.from_time}–${slot.to_time}${slot.active?'':' — wyłączony'}`));
        const toggle=node('button',slot.active?'Wyłącz termin':'Włącz termin');toggle.type='button';
        toggle.onclick=()=>act(async()=>{if(toggle.disabled||!current())return;toggle.disabled=true;try{await api(`/address-delivery/windows/${slot.id}`,'PATCH',{active:!slot.active});if(current())await loadAddressDeliveryViews()}finally{if(current())toggle.disabled=false}});row.append(toggle);list.append(row);
      }
    }
  }catch(error){if(current())el('delivery-view-status').textContent='Nie udało się pobrać dostaw. Odśwież zakładkę.';}
}
function coordinateTime(value){return String(Math.trunc(value/60)).padStart(2,'0')+':'+String(value%60).padStart(2,'0')}
async function initializeAddressDelivery(){
  if(!el('address-delivery-panel'))return;
  try{const r=await fetch('/address-delivery/config',{cache:'no-store'});if(!r.ok||(await r.json()).enabled!==true)return;}catch{return;}
  addressDeliveryEnabled=true;
  el('delivery-requests-tab').onclick=()=>{el('delivery-requests-view').hidden=false;el('delivery-settings-view').hidden=true;};
  el('delivery-settings-tab').onclick=()=>{el('delivery-requests-view').hidden=true;el('delivery-settings-view').hidden=false;};
  el('delivery-view-refresh').onclick=()=>act(()=>loadAddressDeliveryViews());
  el('delivery-view-next').onclick=()=>{if(deliveryNextBefore)act(()=>loadAddressDeliveryViews(deliveryNextBefore))};
  el('delivery-window-form').onsubmit=event=>{event.preventDefault();act(()=>singleWrite('delivery-window-form',el('delivery-window-save'),async()=>{
    if(role!=='rolnik')return;const epoch=sessionEpoch;
    await api('/address-delivery/windows','POST',{city:el('delivery-window-city').value.trim(),postal_code:el('delivery-window-postal').value.trim(),weekday:Number(el('delivery-window-day').value),from_time:el('delivery-window-from').value,to_time:el('delivery-window-to').value});
    if(epoch!==sessionEpoch||role!=='rolnik')return;el('delivery-window-form').reset();await loadAddressDeliveryViews();el('delivery-requests-view').hidden=true;el('delivery-settings-view').hidden=false;
  }));};
  await loadAddressDeliveryViews();if(role==='klient'){await loadProducts();await loadCart();}
}
initializeAddressDelivery();
