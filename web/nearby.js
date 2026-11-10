// No customer location in URLs, browser storage, analytics or console logs.
let nearbySerial=0,nearbyController=null,nearbyPage=null;
let pointEditorSerial=0,pointEditorItems=[];

function coordinateE6(value,limit){
  const text=String(value).trim().replace(',','.');
  const match=/^([+-]?)(\d{1,3})(?:\.(\d{1,6}))?$/.exec(text);
  if(!match)throw Error('Podaj współrzędne dziesiętne, maksymalnie 6 cyfr po przecinku.');
  const amount=(Number(match[2])*1000000+Number((match[3]||'').padEnd(6,'0')))*(match[1]==='-'?-1:1);
  if(!Number.isSafeInteger(amount)||Math.abs(amount)>limit*1000000)throw Error('Współrzędne poza dozwolonym zakresem.');
  return amount===0?0:amount;
}
function coordinateText(value){
  if(value===null||value===undefined)return '';
  const amount=Math.abs(value);
  return (value<0?'-':'')+Math.trunc(amount/1000000)+','+String(amount%1000000).padStart(6,'0');
}
function invalidateNearby(){
  nearbySerial++;if(nearbyController)nearbyController.abort();nearbyController=null;nearbyPage=null;
  el('nearby-results').replaceChildren();el('nearby-next').hidden=true;
  el('nearby-status').textContent='';el('nearby-submit').disabled=false;el('nearby-geolocate').disabled=false;
}
function resetNearbySearch(){
  if(!el('nearby-form'))return;
  invalidateNearby();el('nearby-form').reset();
  if(typeof clearAddressSelection==='function')clearAddressSelection();
  // reset() respects the HTML defaults; sensitive coordinates have no defaults.
  el('nearby-lat').value='';el('nearby-lon').value='';
}
async function searchNearby(offset=0){
  if(!el('nearby-lat').value||!el('nearby-lon').value){el('nearby-status').textContent='Wpisz miejscowość i wybierz miejsce lub użyj swojej lokalizacji.';return;}
  const payload={latitude_e6:coordinateE6(el('nearby-lat').value,90),longitude_e6:coordinateE6(el('nearby-lon').value,180),
    radius_m:Number(el('nearby-radius').value),q:el('nearby-query').value.trim(),limit:24,offset};
  if(el('nearby-min-price').value.trim())payload.min_price_grosze=parseGrosze(el('nearby-min-price').value);
  if(el('nearby-max-price').value.trim())payload.max_price_grosze=parseGrosze(el('nearby-max-price').value);
  if(payload.min_price_grosze!==undefined&&payload.max_price_grosze!==undefined&&payload.min_price_grosze>payload.max_price_grosze)throw Error('Cena od nie może być wyższa niż cena do.');
  invalidateNearby();const serial=nearbySerial,epoch=sessionEpoch;
  const controller=new AbortController();nearbyController=controller;
  el('nearby-submit').disabled=true;el('nearby-next').disabled=true;el('nearby-status').textContent='Szukam aktywnych punktów…';
  try{
    // Public query deliberately sends no account bearer token.
    const response=await fetch('/marketplace/nearby',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),cache:'no-store',signal:controller.signal});
    const data=await response.json();
    if(serial!==nearbySerial||epoch!==sessionEpoch)return;
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Sprawdź zakres współrzędnych, promień i ceny.');
    nearbyPage={offset,limit:payload.limit};
    el('nearby-status').textContent=data.items.length?`Wyniki ${offset+1}–${offset+data.items.length}. Najbliższe punkty w promieniu ${payload.radius_m} m.`:'Brak dostępnych produktów w wybranym promieniu. Zwiększ odległość lub zmień nazwę.';
    for(const offer of data.items){
      const product=offer.product,point=offer.pickup_point;
      const card=node('article','', 'card');
      card.append(node('h3',product.name),node('p',`${money(product.price_grosze)} / ${saleUnitLabel(product)}${packageLabel(product)} • Dostępne: ${product.stock}`),
        node('p',`${offer.distance_m} m w linii prostej • przedział do ${offer.distance_bucket_m} m`),
        node('p',`${point.name} — ${point.city}, ${point.street}; ${point.opening_hours}`));
      if(role==='klient'){
        const qty=node('input');qty.type='number';qty.min='1';qty.max=String(Math.min(1000,product.stock));qty.value='1';qty.inputMode='numeric';qty.setAttribute('aria-label','Ilość w jednostce '+saleUnitLabel(product)+' produktu '+product.name);
        const add=node('button','Dodaj do koszyka');add.type='button';
        add.onclick=()=>act(()=>singleWrite('nearby-cart:'+product.id,add,async()=>{
          if(serial!==nearbySerial||epoch!==sessionEpoch||role!=='klient')return;
          requireResolvedCheckout();const quantity=Number(qty.value);
          if(!Number.isSafeInteger(quantity)||quantity<1||quantity>Math.min(1000,product.stock))throw Error('Podaj poprawną liczbę pełnych jednostek.');
          await api('/cart/items','PUT',{product_id:product.id,quantity});
          if(serial!==nearbySerial||epoch!==sessionEpoch)return;
          msg('Produkt zapisany w koszyku. Wybierz punkt odbioru przy zamówieniu.');await loadCart();
        }));
        card.append(qty,add,node('p','Punkt i dostępność są ponownie sprawdzane przy zamówieniu. W koszyku wybierz wskazany punkt odbioru.'));
      }else card.append(node('p','Zaloguj się jako klient, aby dodać produkt do koszyka.'));
      el('nearby-results').append(card);
    }
    el('nearby-next').hidden=!data.has_more||offset+payload.limit>10000;
  }catch(error){
    if(serial!==nearbySerial||epoch!==sessionEpoch||error.name==='AbortError')return;
    el('nearby-status').textContent=error.message==='Failed to fetch'?'Nie udało się wyszukać. Spróbuj ponownie.':error.message;
  }finally{
    if(serial===nearbySerial&&epoch===sessionEpoch){nearbyController=null;el('nearby-submit').disabled=false;el('nearby-next').disabled=false;}
  }
}
function locateNearby(){
  invalidateNearby();const serial=nearbySerial,epoch=sessionEpoch;
  if(!globalThis.navigator?.geolocation){el('nearby-status').textContent='Lokalizacja urządzenia jest niedostępna. Wpisz miejscowość i wybierz miejsce.';return;}
  el('nearby-geolocate').disabled=true;el('nearby-status').textContent='Oczekuję na zgodę przeglądarki na bieżącą lokalizację…';
  navigator.geolocation.getCurrentPosition(position=>{
    if(serial!==nearbySerial||epoch!==sessionEpoch)return;
    el('nearby-geolocate').disabled=false;
    const lat=Math.round(position.coords.latitude*1000000),lon=Math.round(position.coords.longitude*1000000);
    if(!Number.isSafeInteger(lat)||!Number.isSafeInteger(lon)||Math.abs(lat)>90000000||Math.abs(lon)>180000000){el('nearby-status').textContent='Nieprawidłowa lokalizacja urządzenia. Wpisz miejscowość i wybierz miejsce.';return;}
    el('nearby-lat').value=coordinateText(lat);el('nearby-lon').value=coordinateText(lon);act(()=>searchNearby());
  },error=>{
    if(serial!==nearbySerial||epoch!==sessionEpoch)return;
    el('nearby-geolocate').disabled=false;
    el('nearby-status').textContent=error.code===1?'Nie udzielono zgody na lokalizację. Możesz wpisać miejscowość i wybrać miejsce.':'Nie udało się ustalić lokalizacji. Wpisz miejscowość i wybierz miejsce.';
  },{enableHighAccuracy:false,timeout:10000,maximumAge:60000});
}

function showPointEditor(){
  const point=pointEditorItems.find(p=>String(p.id)===el('point-edit-select').value);
  el('point-edit-form').hidden=!point;
  if(!point)return;
  if(typeof editPickupCalendar==='function')editPickupCalendar(point);
  for(const [field,key] of [['name','name'],['city','city'],['street','street'],['hours','opening_hours']])el('point-edit-'+field).value=point[key];
  el('point-edit-lat').value=coordinateText(point.latitude_e6);el('point-edit-lon').value=coordinateText(point.longitude_e6);
  el('point-edit-active').checked=Boolean(point.active);el('point-edit-clear-coordinates').checked=false;
  el('point-edit-lat').disabled=false;el('point-edit-lon').disabled=false;
}
async function loadPointEditor(){
  if(!el('point-location-panel')||role!=='rolnik')return;
  const serial=++pointEditorSerial,epoch=sessionEpoch,selected=el('point-edit-select').value;
  try{
    const points=await api('/farmers/me/pickup-points');
    if(serial!==pointEditorSerial||epoch!==sessionEpoch||role!=='rolnik')return;
    pointEditorItems=points;el('point-edit-select').replaceChildren();
    for(const point of points){const option=node('option',point.name+(point.active?'':' — nieaktywny'));option.value=String(point.id);el('point-edit-select').append(option);}
    if(points.some(p=>String(p.id)===selected))el('point-edit-select').value=selected;
    el('point-edit-status').textContent=points.length?'':'Najpierw dodaj punkt w profilu gospodarstwa.';showPointEditor();
  }catch(error){if(serial===pointEditorSerial&&epoch===sessionEpoch&&role==='rolnik'&&error.message!=='SESSION_CHANGED')el('point-edit-status').textContent=error.message;}
}
function refreshNearbyRole(){
  if(!el('point-location-panel'))return;
  pointEditorSerial++;pointEditorItems=[];el('point-edit-form').reset();el('point-edit-form').hidden=true;
  el('point-edit-select').replaceChildren();el('point-edit-status').textContent='';el('point-location-panel').hidden=role!=='rolnik';
}
async function savePointEditor(){
  if(role!=='rolnik')return;
  const point=pointEditorItems.find(p=>String(p.id)===el('point-edit-select').value);
  if(!point)throw Error('Wybierz swój punkt odbioru.');
  const epoch=sessionEpoch,serial=pointEditorSerial;
  const body={name:el('point-edit-name').value,city:el('point-edit-city').value,street:el('point-edit-street').value,
    opening_hours:el('point-edit-hours').value,active:el('point-edit-active').checked,...(typeof pickupDatesPayload==='function'?pickupDatesPayload(true):{})};
  if(el('point-edit-clear-coordinates').checked)body.clear_coordinates=true;
  else{
    const lat=el('point-edit-lat').value.trim(),lon=el('point-edit-lon').value.trim();
    if(Boolean(lat)!==Boolean(lon))throw Error('Podaj obie współrzędne punktu.');
    if(lat){body.latitude_e6=coordinateE6(lat,90);body.longitude_e6=coordinateE6(lon,180);}
    else if(point.latitude_e6!==null&&point.latitude_e6!==undefined)throw Error('Aby usunąć lokalizację, zaznacz pole usunięcia współrzędnych.');
  }
  await api('/pickup-points/'+point.id,'PUT',body);
  if(epoch!==sessionEpoch||serial!==pointEditorSerial||role!=='rolnik')return;
  await loadFarmer();if(epoch!==sessionEpoch||role!=='rolnik')return;
  el('point-edit-status').textContent='Punkt zapisany. Wyłączenie punktu nie anuluje wcześniejszych zamówień.';
}

if(el('nearby-form')){
  el('nearby-form').onsubmit=event=>{event.preventDefault();act(()=>searchNearby());};
  el('nearby-form').oninput=invalidateNearby;el('nearby-form').onchange=invalidateNearby;
  el('nearby-clear').onclick=resetNearbySearch;el('nearby-geolocate').onclick=locateNearby;
  el('nearby-next').onclick=()=>{if(nearbyPage)act(()=>searchNearby(nearbyPage.offset+nearbyPage.limit));};
  el('point-edit-select').onchange=()=>{pointEditorSerial++;el('point-edit-status').textContent='';showPointEditor();};
  el('point-edit-clear-coordinates').onchange=()=>{const clear=el('point-edit-clear-coordinates').checked;el('point-edit-lat').disabled=clear;el('point-edit-lon').disabled=clear;};
  el('point-edit-form').onsubmit=event=>{event.preventDefault();act(()=>singleWrite('point-editor',el('point-edit-submit'),savePointEditor));};
  refreshNearbyRole();
}
