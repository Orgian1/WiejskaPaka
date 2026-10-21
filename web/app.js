"use strict";
const saleUnitLabels={szt:'szt.',kg:'kg',g:'g',l:'l',ml:'ml',opak:'opak.',peczek:'pęczek',sloik:'słoik',butelka:'butelka',worek:'worek',skrzynka:'skrzynka',tacka:'tacka'};
function saleUnitLabel(product){return saleUnitLabels[product?.sale_unit]||'szt.'}
function packageLabel(product){const c=product?.package_content;if(!c)return '';const scale=['kg','l'].includes(c.unit)?1000:1;return ` • zawartość: ${String(c.amount_atoms/scale).replace('.',',')} ${saleUnitLabels[c.unit]||''}`}
let saleUnitsEnabled=false;
let token = null, role = null; // only memory; refresh logs out
let cartRefreshSerial=0;
let cartQuoteSerial=0;
let cartQuoteItems=[];
let pendingCartCheckout = null; // Retain key and payload after a network error; reset on account switch.
// Only a non-sensitive marker is persisted for this tab. Never persist a PIN,
// access token or delivery address in browser storage.
const checkoutMarkerPrefix='wp-checkout-unresolved-v1:';
const directKeyPrefix='wp-direct-order-key-v1:';
function directStorageKey(){return checkoutOwner===null?null:directKeyPrefix+String(checkoutOwner)}
function readDirectKey(){try{return sessionStorage.getItem(directStorageKey())}catch(_e){return null}}
function clearDirectKey(){try{sessionStorage.removeItem(directStorageKey())}catch(_e){}}
let checkoutOwner=null;
function checkoutMarkerKey(){return checkoutOwner===null?null:checkoutMarkerPrefix+String(checkoutOwner)}
function markUnresolvedCheckout(){
  const key=checkoutMarkerKey();
  if(key){try{sessionStorage.setItem(key,'1')}catch(_e){/* Storage may be disabled. */}}
}
function clearUnresolvedCheckout(){
  const key=checkoutMarkerKey();
  if(key){try{sessionStorage.removeItem(key)}catch(_e){/* Storage may be disabled. */}}
}
function hasUnresolvedCheckout(){
  const key=checkoutMarkerKey();
  if(!key)return false;
  try{return sessionStorage.getItem(key)==='1'}catch(_e){return false}
}
function showUnresolvedCheckout(){
  const host=el('cart-result');
  host.replaceChildren();
  const warning=node('p','Po odświeżeniu strony nie można ustalić wyniku wcześniejszego zakupu. Sprawdź historię zamówień przed zmianą koszyka lub ponownym zakupem.');
  const button=node('button','Sprawdziłem historię — odblokuj koszyk');
  button.type='button';
  button.onclick=()=>{
    if(!globalThis.confirm('Czy sprawdzono historię zamówień? Ponowny zakup może utworzyć kolejne zamówienie.'))return;
    clearDirectKey();clearUnresolvedCheckout();pendingCartCheckout=null;host.replaceChildren();act(loadCart);
  };
  const directKey=readDirectKey();
  if(directKey){
    const check=node('button','Sprawdź wynik zakupu bezpośredniego');
    check.type='button';
    check.onclick=()=>act(async()=>{
      const epoch=sessionEpoch;
      const result=await api('/orders/idempotency-status/'+encodeURIComponent(directKey));
      if(epoch!==sessionEpoch||directKey!==readDirectKey())return;
      if(!result.completed){msg('Serwer nie potwierdził jeszcze zakupu. Poczekaj lub sprawdź historię.');return}
      clearDirectKey();clearUnresolvedCheckout();pendingCartCheckout=null;
      host.replaceChildren();msg('Zakup #'+result.order_id+' został zapisany. Szczegóły sprawdź w historii zamówień.');
      await loadCart();await loadOrders();
    });
    host.append(warning,check,button);
  }else host.append(warning,button);
}
function requireResolvedCheckout(){
  if(pendingCartCheckout||hasUnresolvedCheckout())throw Error('Wynik poprzedniego zakupu jest nieznany. Ponów zakup z tymi samymi danymi lub sprawdź historię zamówień po odświeżeniu strony. Nie zmieniaj koszyka przed wyjaśnieniem.');
}
let sessionEpoch = 0; // invalidate requests started before logout/account switch
let loginAttempt = 0; // reject superseded login responses
let productRequest = 0, orderRequest = 0;
const catalogPageSize=24;
let catalogSellerId=null;
let catalogOffset=0,catalogMore=false,catalogLoading=false; // reject stale view refreshes
const el = id => document.getElementById(id);
const money = gr => `${(gr / 100).toFixed(2).replace('.', ',')} zł`; // formatting only
function checkoutPinLabel(result,field){return typeof result[field]==='string'&&/^[0-9]{6}$/.test(result[field])?'PIN TESTOWY: '+result[field]+'. Zapisz PIN na czas testu. Rezerwacja bez płatności: 30 minut':'PIN niedostępny — zakup już istnieje. Sprawdź historię; nie składaj go ponownie.'}
function parseGrosze(text) { const s=String(text).trim().replace(',', '.'); if(!/^(0|[1-9]\d{0,7})(\.\d{1,2})?$/.test(s)) throw Error('Kwota musi mieć najwyżej dwa miejsca po przecinku'); const [a,b='']=s.split('.'); return Number(a)*100+Number(b.padEnd(2,'0')); }
let noticeVersion = 0;
function msg(t){
  const version=++noticeVersion;
  const notice=el('notice');
  notice.textContent=t;
  notice.classList.add('show');
  setTimeout(()=>{if(version===noticeVersion)notice.classList.remove('show')},6500);
}
async function api(path,method='GET',body,extraHeaders={}){const epoch=sessionEpoch;const h={'Content-Type':'application/json',...extraHeaders};if(token)h.Authorization=`Bearer ${token}`;const r=await fetch(path,{method,headers:h,body:body===undefined?undefined:JSON.stringify(body),cache:'no-store'});if(epoch!==sessionEpoch)throw Error('SESSION_CHANGED');const d=await r.json();if(epoch!==sessionEpoch)throw Error('SESSION_CHANGED');if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Błąd żądania');return d}
function node(tag,text,cls){const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n}
function clear(id){el(id).replaceChildren()}
function resetCatalogView(){
  if(typeof resetSellerDirectory==='function')resetSellerDirectory();
  catalogOffset=0;catalogMore=false;catalogLoading=false;
  el('catalog-status').textContent='';el('catalog-previous').disabled=true;el('catalog-next').disabled=true;
}
async function catalogPage(request,epoch){
  const offset=catalogOffset,q=el('catalog-query').value.trim();
  const active=()=>request===productRequest&&epoch===sessionEpoch;
  catalogLoading=true;catalogMore=false;el('catalog-previous').disabled=true;el('catalog-next').disabled=true;
  el('catalog-status').textContent='Pobieranie produktów…';
  try{
    if(q.length>120)throw Error('Nieprawidłowe wyszukiwanie');
    const params=new URLSearchParams({q,limit:String(catalogPageSize),offset:String(offset)});
    if(catalogSellerId!==null)params.set('farmer_id',String(catalogSellerId));
    const data=await api('/catalog/search?'+params.toString());
    if(!active())return null;
    const keys=['id','farmer_id','price_grosze','delivery_grosze','stock'];
    if(!data||!Array.isArray(data.items)||data.items.length>catalogPageSize||!Number.isSafeInteger(data.total)||data.total<0||data.limit!==catalogPageSize||data.offset!==offset||data.items.length>Math.max(0,data.total-offset)||!data.items.every(p=>p&&typeof p.name==='string'&&keys.every(k=>Number.isSafeInteger(p[k]))&&p.id>0&&p.farmer_id>0&&p.price_grosze>0&&p.delivery_grosze>=0&&p.stock>0))throw Error('Nieprawidłowa strona katalogu');
    catalogMore=offset+data.items.length<data.total;
    el('catalog-status').textContent=`Produkty: ${data.total}. Strona ${Math.floor(offset/catalogPageSize)+1}.`+(catalogMore&&offset+catalogPageSize>10000?' Zawęź nazwę produktu, aby zobaczyć dalsze wyniki.':'');
    return data.items;
  }catch(error){
    if(active()&&error.message!=='SESSION_CHANGED')el('catalog-status').textContent='Nie udało się pobrać katalogu. Spróbuj ponownie lub zmień wyszukiwanie.';
    return null;
  }finally{
    if(active()){catalogLoading=false;el('catalog-previous').disabled=offset===0;el('catalog-next').disabled=!catalogMore||offset+catalogPageSize>10000}
  }
}
async function loadProducts(){if(typeof sellerSearchMode==='function'&&sellerSearchMode()){productRequest++;return loadSellerDirectory();}const request=++productRequest;const epoch=sessionEpoch;const products=await catalogPage(request,epoch);if(request!==productRequest||epoch!==sessionEpoch||products===null)return;clear('products');if(!products.length)el('products').append(node('p','Brak produktów dla tej strony lub wyszukiwania.'));for(const p of products){const box=node('div','', 'card');box.append(node('b',p.name),node('p',`${money(p.price_grosze)} / ${saleUnitLabel(p)}${packageLabel(p)} • Dostawa: ${money(p.delivery_grosze)} • Dostępne: ${p.stock}`));if(role==='klient'){const qty=node('input');qty.type='number';qty.min='1';qty.max=String(p.stock);qty.value='1';qty.setAttribute('aria-label','Ilość w jednostce '+saleUnitLabel(p));qty.inputMode='numeric';const mode=node('select');for(const [v,t] of [['odbior','Odbiór w punkcie'],['dostawa','Dostawa na adres']]){const opt=node('option',t);opt.value=v;mode.append(opt)}mode.setAttribute('aria-label','Sposób realizacji zamówienia');const point=node('select');point.setAttribute('aria-label','Punkt odbioru');const addr=node('div');const city=node('input'),street=node('input'),postal=node('input');city.placeholder='Miejscowość';street.placeholder='Ulica i numer';postal.placeholder='Kod pocztowy 00-000';postal.pattern='[0-9]{2}-[0-9]{3}';postal.inputMode='numeric';postal.autocomplete='postal-code';city.autocomplete='address-level2';street.autocomplete='street-address';city.setAttribute('aria-label','Miejscowość dostawy');street.setAttribute('aria-label','Ulica i numer dostawy');postal.setAttribute('aria-label','Kod pocztowy dostawy');addr.append(city,street,postal);const deliveryPreference=typeof addressDeliveryFields==='function'?addressDeliveryFields(p.farmer_id):null;if(deliveryPreference)addr.append(deliveryPreference.element);const status=node('p','Wybierz sposób realizacji');status.setAttribute('role','status');const cardEpoch=sessionEpoch;let pointRequest=0;const update=async()=>{const request=++pointRequest;const delivery=mode.value==='dostawa';point.hidden=delivery;addr.hidden=!delivery;if(!delivery){point.replaceChildren();try{const pts=await api(`/farmers/${p.farmer_id}/pickup-points`);if(request!==pointRequest||cardEpoch!==sessionEpoch||!box.isConnected||mode.value!=='odbior')return;for(const pt of pts){const o=node('option',`${pt.name} — ${pt.city}, ${pt.street} (${pt.opening_hours})`);o.value=String(pt.id);point.append(o)}status.textContent=pts.length?'Wybierz punkt odbioru':'Rolnik nie dodał jeszcze punktu odbioru';}catch(e){if(request===pointRequest&&cardEpoch===sessionEpoch&&box.isConnected&&e.message!=='SESSION_CHANGED')status.textContent=e.message}}else status.textContent=`Opłata za dostawę: ${money(p.delivery_grosze)}`};mode.onchange=()=>act(update);const b=node('button','Zamów testowo');b.onclick=()=>act(async()=>{requireResolvedCheckout();if(b.disabled)return;const orderEpoch=sessionEpoch;const quantity=Number(qty.value);if(!Number.isSafeInteger(quantity)||quantity<1||quantity>p.stock)throw Error('Podaj prawidłową liczbę pełnych jednostek (maksymalnie dostępny stan)');if(mode.value==='dostawa'&&(!city.value.trim()||!street.value.trim()||!/^[0-9]{2}-[0-9]{3}$/.test(postal.value.trim())))throw Error('Podaj miejscowość, ulicę i kod pocztowy 00-000');b.disabled=true;try{const payload={product_id:p.id,quantity,fulfillment:mode.value};if(mode.value==='odbior'){if(!point.value)throw Error('Brak punktu odbioru');payload.pickup_point_id=Number(point.value)}else{payload.delivery_city=city.value;payload.delivery_street=street.value;payload.delivery_postal_code=postal.value;if(deliveryPreference)payload.address_delivery=deliveryPreference.payload()}// Server-side idempotency prevents duplicate direct orders when the same key is retried.
// Keep a warning and operation key across refresh; never persist address or PIN.
if(typeof offerSamePackage==='function'){const proceed=await offerSamePackage(p,quantity,true);if(!proceed||orderEpoch!==sessionEpoch)return;requireResolvedCheckout();}
const markerKey=checkoutMarkerKey();markUnresolvedCheckout();
const directKey=crypto.randomUUID();
const directStorage=directStorageKey();
if(directStorage){try{sessionStorage.setItem(directStorage,directKey)}catch(_e){}}
const d=await api('/orders','POST',payload,{'Idempotency-Key':directKey});
if(orderEpoch!==sessionEpoch)return;
if(markerKey){try{sessionStorage.removeItem(markerKey)}catch(_e){/* Storage may be disabled. */}}
clearDirectKey();
msg(`Zamówienie ${d.pickup_code}; ${checkoutPinLabel(d,'pin_test_only')}; suma ${money(d.total_grosze)}.`);await loadProducts();await loadOrders()}finally{b.disabled=false}});const addCart=node('button','Dodaj do koszyka');addCart.type='button';addCart.onclick=()=>act(async()=>{requireResolvedCheckout();if(addCart.disabled)return;addCart.disabled=true;try{const epoch=sessionEpoch;const quantity=Number(qty.value);if(!Number.isSafeInteger(quantity)||quantity<1||quantity>p.stock)throw Error('Nieprawidłowa ilość');await api('/cart/items','PUT',{product_id:p.id,quantity});if(epoch!==sessionEpoch)return;msg('Produkt zapisany w koszyku');await loadCart();if(epoch===sessionEpoch&&typeof offerSamePackage==='function')await offerSamePackage(p,quantity)}finally{addCart.disabled=false}});box.append(qty,addCart,mode,point,addr,status,b);act(update)}if(typeof userPhotosEnabled!=='undefined'&&userPhotosEnabled)box.prepend(photoImage('product',p.id));el('products').append(box)}}
let farmerRequest = 0;
async function loadFarmer(){
  if(role!=='rolnik')return;
  const request=++farmerRequest, epoch=sessionEpoch;
  const current=()=>request===farmerRequest&&epoch===sessionEpoch&&role==='rolnik';
  try{
    const p=await api('/farmers/me/profile');
    if(!current())return;
    el('farm-name').value=p.farm_name;
    el('farm-city').value=p.city;
    el('farm-description').value=p.description;
  }catch(e){
    if(!current())return;
    if(e.message==='SESSION_CHANGED')return;
    if(!e.message.includes('Uzupełnij'))msg(e.message);
  }
  const pts=await api('/farmers/me/pickup-points');
  if(!current())return;
  clear('my-points');
  if(!pts.length)el('my-points').append(node('p','Nie masz jeszcze punktów odbioru'));
  for(const pt of pts)el('my-points').append(node('p',`${pt.name} — ${pt.city}, ${pt.street}; ${pt.opening_hours}${pt.active?'':' — nieaktywny'}`));
  if(typeof loadPointEditor==='function')await loadPointEditor();
}
async function loadOrders(){if(!role||role==='dostawca')return;if(typeof loadAddressDeliveryViews==='function')act(loadAddressDeliveryViews);const request=++orderRequest;const epoch=sessionEpoch;const orders=await api('/orders/me');if(request!==orderRequest||epoch!==sessionEpoch)return;clear('orders');if(!orders.length)el('orders').append(node('p','Brak zamówień'));for(const o of orders){const box=node('div','', 'card');box.append(node('b',o.pickup_code),node('p',`${money(o.total_grosze)} • ${o.fulfillment} • ${o.status}`));if(o.reservation_expires_at&&o.status==='oczekuje_na_platnosc_testowa')box.append(node('p',`Termin rezerwacji bez płatności: ${new Date(o.reservation_expires_at).toLocaleString('pl-PL')}`));if(role==='klient'&&o.status==='oczekuje_na_platnosc_testowa'){const b=node('button','Anuluj testowo');b.onclick=()=>act(async()=>{if(b.disabled)return;b.disabled=true;try{await api(`/orders/${o.id}/cancel-test`,'POST');await loadOrders();await loadProducts()}finally{b.disabled=false}});box.append(b)}if(role==='rolnik'&&o.status==='oczekuje_na_platnosc_testowa'&&o.fulfillment==='odbior'){const b=node('button','Gotowe do odbioru (test)');b.onclick=()=>act(async()=>{if(b.disabled)return;const epoch=sessionEpoch;b.disabled=true;try{await api(`/test/orders/${o.id}/ready`,'POST');if(epoch!==sessionEpoch)return;await loadOrders()}finally{b.disabled=false}});box.append(b)}if(role==='rolnik'&&o.status==='gotowe_do_odbioru_testowo'){const pin=node('input');pin.type='text';pin.autocomplete='off';pin.placeholder='6-cyfrowy PIN klienta';pin.maxLength=6;pin.inputMode='numeric';pin.setAttribute('aria-label','Sześciocyfrowy PIN odbioru');pin.setAttribute('pattern','[0-9]{6}');const checked=node('input');checked.type='checkbox';checked.style.width='auto';const label=node('label','Klient sprawdził towar');label.prepend(checked);const b=node('button','Potwierdź odbiór');b.onclick=()=>act(async()=>{if(!/^\d{6}$/.test(pin.value))throw Error('PIN musi mieć 6 cyfr');if(!checked.checked)throw Error('Najpierw klient musi sprawdzić produkty');b.disabled=true;let d;try{d=await api(`/orders/${o.id}/confirm`,'POST',{pin:pin.value,checked_goods:true})}finally{pin.value='';b.disabled=false}msg(d.confirmed?'Odbiór potwierdzony':'Nieprawidłowy PIN; pozostało prób: '+d.remaining_attempts);await loadOrders()});box.append(pin,label,b)}if(role==='klient'&&typeof pinRecoveryControls==='function'&&!['odebrane','anulowane_testowo','nieudana_dostawa_testowo'].includes(o.status))box.append(pinRecoveryControls('order',o.id));if(typeof purchaseRecordControls==='function')box.append(purchaseRecordControls('order',o.id,box));el('orders').append(box)}}
async function act(fn){try{await fn()}catch(e){if(e.message!=='SESSION_CHANGED')msg(e.message)}}
// Clear drafts and rendered private data synchronously, including while offline.
function clearPrivateAccountViews(){
  if(typeof resetAddressDeliveryViews==='function')resetAddressDeliveryViews();
  for(const id of ['products','orders','my-points','dashboard-content','notifications-list','cart-items']){
    const host=el(id);
    // Clear detached controls/text too: pending handlers may still reference them.
    for(const old of host.querySelectorAll('*')){
      if('value' in old)old.value='';
      if('checked' in old)old.checked=false;
      old.textContent='';
    }
    host.replaceChildren();
  }
  for(const id of ['cart-checkout','profile-form','point-form','new-product'])el(id).reset();
  for(const id of ['cart-city','cart-street','cart-postal','email'])el(id).value='';
  for(const id of ['cart-point','cart-farmer-select'])el(id).replaceChildren();
  el('cart-total').textContent='';
  el('cart-address').hidden=true;el('cart-pickup').hidden=false;
}
function logged(user){if(typeof resetPackageOffer==='function')resetPackageOffer();if(typeof resetUserPhotoViews==='function')resetUserPhotoViews();if(typeof resetCatalogView==='function')resetCatalogView();if(typeof resetSupportView==='function')resetSupportView(user);if(typeof resetAdminSellerReview==='function')resetAdminSellerReview(user);if(typeof resetSellerComplianceView==='function')resetSellerComplianceView(user);if(typeof resetPinRecoveryViews==='function')resetPinRecoveryViews();if(typeof resetPasswordChangeView==='function')resetPasswordChangeView(user);if(typeof resetSessionSecurityView==='function')resetSessionSecurityView(user);pendingCartCheckout=null;checkoutOwner=user?.id??null;el('cart-result').textContent='';cartQuoteSerial++;cartQuoteItems=[];el('password').value='';el('cart-quote').textContent='';productRequest++;orderRequest++;role=user?.role||null;farmerRequest++;if(typeof resetNearbySearch==='function')resetNearbySearch();if(typeof refreshNearbyRole==='function')refreshNearbyRole();clearPrivateAccountViews();el('identity').textContent=user?user.email:'Nie zalogowano';el('identity').title=user?user.email:'';el('auth').hidden=!!user;el('logout').hidden=!user;el('account-section').className=user?'account-compact':'';el('account-nav-link').href=user?'#account-section':'#auth';el('cart-section').hidden=role!=='klient';if(role==='klient'){if(hasUnresolvedCheckout())showUnresolvedCheckout();act(loadCart)}else {cartRefreshSerial++;el('cart-items').replaceChildren();el('cart-result').textContent='';}el('farmer').hidden=role!=='rolnik';el('farmer-details').hidden=role!=='rolnik';if(role==='rolnik')act(loadFarmer);el('orders-section').hidden=!role||role==='dostawca';act(loadProducts);if(role&&role!=='dostawca')act(loadOrders);if(typeof loadDashboard==='function')act(loadDashboard);if(typeof loadAddressDeliveryViews==='function')act(loadAddressDeliveryViews);if(user&&typeof loadUserPhotoViews==='function')act(loadUserPhotoViews);if(typeof loadSellerLoginEditor==='function')act(loadSellerLoginEditor)}
el('auth').onsubmit=e=>{e.preventDefault();const attempt=++loginAttempt;const epoch=sessionEpoch;act(async()=>{
  const submittedPassword=el('password').value;el('password').value='';
  const d=await api('/auth/login','POST',{email:el('email').value,password:submittedPassword});
  if(attempt!==loginAttempt||epoch!==sessionEpoch)return; // logout or newer login won the race
  sessionEpoch++;token=d.access_token;
  try{const user=await api('/auth/me');if(attempt!==loginAttempt)return;logged(user);msg('Zalogowano')}
  catch(e){if(attempt===loginAttempt){sessionEpoch++;token=null;logged(null)}throw e}
})};
// Prevent repeated submissions while a write is in progress. This is a UI guard;
// the API must independently enforce authorization and idempotency.
const pendingWrites = new Set();
async function singleWrite(key, button, operation){
  if(pendingWrites.has(key))return;
  pendingWrites.add(key);
  if(button)button.disabled=true;
  try{await operation()}finally{
    pendingWrites.delete(key);
    if(button)button.disabled=false;
  }
}
el('register').onclick=()=>act(()=>singleWrite('register',el('register'),async()=>{
  const submittedPassword=el('password').value;el('password').value='';
  await api('/auth/register','POST',{email:el('email').value,password:submittedPassword,role:el('role').value});
  msg('Konto testowe utworzone. Teraz się zaloguj.');
}));
el('logout').onclick=()=>act(async()=>{
 const previousToken=token;loginAttempt++;sessionEpoch++;const logoutEpoch=sessionEpoch;
 token=null;logged(null);msg('Wylogowano na tym urządzeniu.');
 if(previousToken){try{
   const response=await fetch('/auth/logout',{method:'POST',headers:{Authorization:`Bearer ${previousToken}`},cache:'no-store'});
   if(!response.ok&&response.status!==401)throw Error('Logout not confirmed');
 }catch(_e){
   if(logoutEpoch===sessionEpoch)msg('Wylogowano na tym urządzeniu. Nie potwierdzono cofnięcia sesji na serwerze. Po przywróceniu połączenia zaloguj się i wyloguj pozostałe sesje lub zmień hasło.');
 }}
});
el('new-product').onsubmit=e=>{e.preventDefault();act(()=>singleWrite('new-product',el('new-product').querySelector('button'),async()=>{
  const epoch=sessionEpoch;
  const payload={name:el('pname').value,price_grosze:parseGrosze(el('price').value),delivery_grosze:parseGrosze(el('delivery').value),stock:Number(el('stock').value)};
  if(saleUnitsEnabled){payload.sale_unit=el('sale-unit').value;if(!el('package-content-fields').hidden){payload.content_amount=el('content-amount').value;payload.content_unit=el('content-unit').value}}
  await api('/products','POST',payload);
  if(epoch!==sessionEpoch)return;
  msg('Produkt dodany');await loadProducts();
}))};
el('refresh').onclick=()=>{catalogOffset=0;return act(loadProducts)};
el('catalog-form').onsubmit=e=>{e.preventDefault();catalogOffset=0;return act(loadProducts)};
el('catalog-previous').onclick=()=>{if(catalogLoading||catalogOffset===0)return;catalogOffset=Math.max(0,catalogOffset-catalogPageSize);return act(loadProducts)};
el('catalog-next').onclick=()=>{if(catalogLoading||!catalogMore||catalogOffset+catalogPageSize>10000)return;catalogOffset+=catalogPageSize;return act(loadProducts)};el('refresh-orders').onclick=()=>act(loadOrders);logged(null);

el('profile-form').onsubmit=e=>{e.preventDefault();act(()=>singleWrite('profile-form',el('profile-form').querySelector('button'),async()=>{
  const epoch=sessionEpoch;
  await api('/farmers/me/profile','PUT',{farm_name:el('farm-name').value,city:el('farm-city').value,description:el('farm-description').value});
  if(epoch===sessionEpoch)msg('Profil gospodarstwa zapisany');
}))};
el('point-form').onsubmit=e=>{e.preventDefault();act(()=>singleWrite('point-form',el('point-form').querySelector('button'),async()=>{
  const epoch=sessionEpoch;
  await api('/pickup-points','POST',{name:el('point-name').value,city:el('point-city').value,street:el('point-street').value,opening_hours:el('point-hours').value});
  if(epoch!==sessionEpoch)return;
  msg('Punkt odbioru dodany');el('point-form').reset();await loadFarmer();
}))};

// B/431-460: saved cart interface, test-only checkout.

async function loadCart(){
 if(role!=='klient')return;
 const serial=++cartRefreshSerial, epoch=sessionEpoch;
 const data=await api('/cart/items');
 if(serial!==cartRefreshSerial||epoch!==sessionEpoch)return;
 cartQuoteItems=data.items.filter(item=>item.name!==null).map(item=>({product_id:item.product_id,quantity:item.quantity,farmer_id:item.farmer_id}));
 const host=el('cart-items');host.replaceChildren();
 let sum=0;const farmers=new Set();
 for(const item of data.items){
   const row=node('div','', 'card');
   if(item.name===null){row.append(node('p','Produkt usunięty — usuń go z koszyka'));}
   else {row.append(node('b',item.name),node('p',`${item.quantity} ${saleUnitLabel(item)} × ${money(item.price_grosze)} / ${saleUnitLabel(item)}${packageLabel(item)} • dostępne: ${item.stock}`));sum+=item.quantity*item.price_grosze;farmers.add(item.farmer_id)}
   const qty=node('input');qty.type='number';qty.min='1';qty.max='1000';qty.value=String(item.quantity);qty.setAttribute('aria-label','Ilość produktu '+(item.name||item.product_id));
   const save=node('button','Zapisz ilość');save.type='button';save.onclick=()=>act(async()=>{requireResolvedCheckout();const n=Number(qty.value);if(!Number.isSafeInteger(n)||n<1||n>1000)throw Error('Nieprawidłowa ilość');await api('/cart/items','PUT',{product_id:item.product_id,quantity:n});await loadCart()});
   const del=node('button','Usuń');del.type='button';del.onclick=()=>act(async()=>{requireResolvedCheckout();await api('/cart/items/'+item.product_id,'DELETE');await loadCart()});
   row.append(qty,save,del);host.append(row);
 }
 el('cart-total').textContent='Suma produktów (bez dostawy): '+money(sum);
 const farmerSelect=el('cart-farmer-select');
 const previous=farmerSelect.value;farmerSelect.replaceChildren();
 for(const farmer of [...farmers].sort((a,b)=>a-b)){const opt=node('option','Rolnik #'+farmer);opt.value=String(farmer);farmerSelect.append(opt)}
 if([...farmers].some(x=>String(x)===previous))farmerSelect.value=previous;
 el('cart-submit').disabled=!farmers.size||hasUnresolvedCheckout();
 if(farmers.size>1)host.prepend(node('p','Wybierz rolnika. Zamówienie obejmie tylko jego produkty, pozostałe zostaną w koszyku.'));
 const point=el('cart-point');point.replaceChildren();
 if(farmers.size){const farmer=Number(farmerSelect.value);const pts=await api('/farmers/'+farmer+'/pickup-points');if(serial!==cartRefreshSerial||epoch!==sessionEpoch)return;for(const pt of pts){const opt=node('option',pt.name+' — '+pt.city+', '+pt.street);opt.value=String(pt.id);point.append(opt)}}
 if(typeof refreshDeliveryCartFields==='function')refreshDeliveryCartFields(farmers.size?Number(farmerSelect.value):null);
 await refreshCartQuote();
}
async function refreshCartQuote(){
 const request=++cartQuoteSerial, epoch=sessionEpoch;
 const host=el('cart-quote');
 host.textContent='';
 const farmer=Number(el('cart-farmer-select').value);
 const items=cartQuoteItems.filter(item=>item.farmer_id===farmer)
   .map(({product_id,quantity})=>({product_id,quantity}));
 if(!items.length)return;
 if(items.length>50){host.textContent='W jednej przesyłce może być najwyżej 50 pozycji.';return}
 const quoteMode=el('cart-mode').value;
 try{
   const quote=await api('/cart/quote','POST',{items,fulfillment:quoteMode});
   if(request!==cartQuoteSerial||epoch!==sessionEpoch||farmer!==Number(el('cart-farmer-select').value)||quoteMode!==el('cart-mode').value)return;
   host.textContent=`Wycena przesyłki: produkty ${money(quote.subtotal_grosze)} + dostawa ${money(quote.delivery_grosze)} = razem ${money(quote.total_grosze)}. Jedna opłata za przesyłkę. Wycena orientacyjna.`;
 }catch(error){
   if(request===cartQuoteSerial&&epoch===sessionEpoch&&error.message!=='SESSION_CHANGED')host.textContent='Nie można wycenić przesyłki: '+error.message;
 }
}
el('cart-farmer-select').addEventListener('change',()=>act(loadCart));
function cartModeChange(){const delivery=el('cart-mode').value==='dostawa';el('cart-address').hidden=!delivery;el('cart-pickup').hidden=delivery;act(refreshCartQuote)}
el('cart-mode').addEventListener('change',cartModeChange);
el('cart-refresh').onclick=()=>act(loadCart);
el('cart-checkout').onsubmit=e=>{e.preventDefault();if(hasUnresolvedCheckout()&&!pendingCartCheckout){showUnresolvedCheckout();return}act(()=>singleWrite('cart-checkout',el('cart-submit'),async()=>{
 const payload={fulfillment:el('cart-mode').value,farmer_id:Number(el('cart-farmer-select').value)};
 if(payload.fulfillment==='odbior'){if(!el('cart-point').value)throw Error('Wybierz punkt odbioru');payload.pickup_point_id=Number(el('cart-point').value)}
 else {payload.delivery_city=el('cart-city').value.trim();payload.delivery_street=el('cart-street').value.trim();payload.delivery_postal_code=el('cart-postal').value.trim();if(!payload.delivery_city||!payload.delivery_street||!/^[0-9]{2}-[0-9]{3}$/.test(payload.delivery_postal_code))throw Error('Podaj prawidłowy adres dostawy')}
 if(payload.fulfillment==='dostawa'&&typeof deliveryCartFields!=='undefined'&&deliveryCartFields)payload.address_delivery=deliveryCartFields.payload();
 // A failed network response does not prove that checkout failed on the server.
 // Reuse the *same* request and key until its result is known.
 const serialized=JSON.stringify(payload);
 if(pendingCartCheckout && pendingCartCheckout.serialized!==serialized){
   throw Error('Poprzedni zakup ma nieznany wynik. Przywróć poprzednie dane i ponów żądanie albo odśwież stronę i sprawdź historię zamówień.');
 }
 if(!pendingCartCheckout){
   if(!globalThis.crypto?.randomUUID)throw Error('Bezpieczny identyfikator zakupu jest niedostępny');
   pendingCartCheckout={serialized,key:crypto.randomUUID()};markUnresolvedCheckout();
 }
 const checkoutEpoch=sessionEpoch;
 const checkoutAttempt=pendingCartCheckout;
 const result=await api('/cart/checkout-test','POST',payload,{'Idempotency-Key':checkoutAttempt.key});
 // A logout or account switch can happen while checkout is in flight. Never
 // display another account's PIN or clear its pending operation.
 if(checkoutEpoch!==sessionEpoch || pendingCartCheckout!==checkoutAttempt)return;
 pendingCartCheckout=null;clearUnresolvedCheckout();
 el('cart-result').textContent='Przesyłka #'+result.shipment_id+' • '+checkoutPinLabel(result,'shipment_pin_test_only')+' • razem '+money(result.total_grosze)+' (dostawa '+money(result.delivery_grosze)+').';
 await loadCart();await loadProducts();await loadOrders();
 }))};

async function loadSaleUnits(){
 if(!el('product-units-fields'))return;
 try{const r=await fetch('/product-units',{cache:'no-store'});if(!r.ok)return;const data=await r.json();if(data.enabled!==true||!Array.isArray(data.units))return;
 const select=el('sale-unit');select.replaceChildren();for(const u of data.units){if(!Object.hasOwn(saleUnitLabels,u.code))continue;const o=node('option',saleUnitLabels[u.code]);o.value=u.code;select.append(o)}
 select.onchange=()=>{const packaged=data.units.find(u=>u.code===select.value)?.packaged===true;el('package-content-fields').hidden=!packaged;el('content-amount').required=packaged;el('content-amount').value=''};
 saleUnitsEnabled=true;select.onchange();el('product-units-fields').hidden=false;
 }catch(_e){/* Existing piece listings remain usable when discovery is unavailable. */}
}
loadSaleUnits();
