"use strict";
// Hash routes work on an ordinary static origin; no token/address is put in URLs.
const appRoutesReady=true;
const appViewGroups={
 products:['products-section'],nearby:['nearby-section'],favorites:['favorites-section'],cart:['cart-section'],
 orders:['orders-section','address-delivery-panel'],wallet:['wallet-section'],
 account:['account-section','password-reset-section','account-security','farmer-profile-section','seller-login-panel','seller-compliance','user-photo-panel'],
 listings:['farmer','seller-listings-section'],points:['farmer-details','point-location-panel'],
 dashboard:['dashboard','admin-seller-review','pickup-promotions-admin','wallet-admin-section','wallet-ads-admin'],
 notifications:['notifications-section'],contact:['contact-disclosure']
};
const appRouteAliases={'products-section':'products','nearby-section':'nearby','favorites-section':'favorites','cart-section':'cart','orders-section':'orders','address-delivery-panel':'orders','wallet-section':'wallet','account-section':'account','auth':'account','role':'account','account-security':'account','farmer':'listings','farmer-details':'points','point-form':'points','point-location-panel':'points','support-section':'contact','contact-section':'contact','contact-disclosure':'contact','seller-compliance':'account','user-photo-panel':'account','wallet-admin-section':'dashboard','wallet-ads-admin':'dashboard','pickup-promotions-admin':'dashboard','admin-seller-review':'dashboard','notifications-section':'notifications'};
let appCurrentView=null;
let pendingGuestProductId=null;
function loginForProduct(productId){
 if(!Number.isSafeInteger(productId)||productId<1)return;
 pendingGuestProductId=productId;
 navigateApp('account');
 const email=el('email');if(email)email.focus();
}
function appRouteName(){
 const raw=location.hash.slice(1).split('?')[0];
 if(raw.startsWith('reset-password')||raw.startsWith('verify-email'))return 'account';
 return appViewGroups[raw]?raw:appRouteAliases[raw]||'products';
}
function appViewAllowed(view){
 if(['products','nearby','account','contact'].includes(view))return true;
 if(['listings','points'].includes(view))return role==='rolnik';
 if(['favorites','wallet'].includes(view))return ['klient','rolnik'].includes(role);
 if(view==='cart')return role==='klient';
 if(view==='orders')return !!role&&role!=='dostawca';
 return !!role;
}
function navigateApp(view){
 if(view==='wallet'&&['klient','rolnik'].includes(role)&&typeof walletAdAccessGranted!=='undefined'&&!walletAdAccessGranted){void enterWalletWithAd();return;}
 if(appRouteName()===view){applyAppRoute(true);return}
 location.hash=view;applyAppRoute(false);
}
function applyAppRoute(focus=false){
 if(appRouteName()==='wallet'&&typeof walletAdAccessGranted!=='undefined'&&!walletAdAccessGranted&&['klient','rolnik'].includes(role)){
  history.replaceState(null,'','#account');
  void enterWalletWithAd();
  return;
 }
 const wanted=(el('reset-token').value||(typeof emailProofToken!=='undefined'&&emailProofToken))?'account':appRouteName(),view=appViewAllowed(wanted)?wanted:'account';
 if(view!=='wallet'&&typeof walletAdAccessGranted!=='undefined')walletAdAccessGranted=false;
 const visible=new Set(appViewGroups[view]);
 for(const id of new Set(Object.values(appViewGroups).flat())){
  const target=el(id);if(target)target.toggleAttribute('data-route-hidden',!visible.has(id));
 }
 // A login is required for private deep links, but the intended URL is preserved.
 const prompt=el('route-status');prompt.textContent=view!==wanted?'Zaloguj się na konto z dostępem do tego widoku.':'';
 for(const link of document.querySelectorAll('.quick-nav a')){
  const target=appRouteAliases[link.hash.slice(1)]||link.hash.slice(1);
  if(target===view)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
 }
 el('products-section').hidden=false;el('products-nav-link').hidden=false;
 el('nearby-section').hidden=false;el('nearby-nav-link').hidden=false;
 el('seller-listings-section').hidden=role!=='rolnik';
 el('points-nav-link').hidden=role!=='rolnik';
 el('seller-nav-link').textContent='Moje ogłoszenia';
 el('panel-nav-link').hidden=!role;
 // Account settings are shown only here; the profile form has a separate owner.
 el('farmer-profile-section').hidden=role!=='rolnik';
 if(view==='contact')el('contact-disclosure').hidden=false;
 const changed=appCurrentView!==view;appCurrentView=view;
 document.dispatchEvent(new Event('wiejskapaka:route-changed'));
 if(view==='listings'&&changed)act(loadSellerListings);
 if(view==='points'&&changed&&role==='rolnik')act(loadFarmer);
 if(focus){const heading=el('view-heading');heading.textContent=({products:'Produkty',nearby:'Blisko mnie',favorites:'Ulubione',cart:'Koszyk',orders:'Zamówienia',wallet:'Portfel',account:'Konto',listings:'Moje ogłoszenia',points:'Punkty odbioru',dashboard:'Panel',notifications:'Powiadomienia',contact:'Kontakt'})[view];heading.focus();}
 document.title=({'products':'Produkty','listings':'Moje ogłoszenia','points':'Punkty odbioru'}[view]||'Moje konto')+' — WiejskaPaka';
}
const appLogged=logged;
logged=function(user){if(typeof resetWalletAds==='function')resetWalletAds();const savedCatalog=catalogRouteSnapshot;appLogged(user);if(user&&role==='admin'&&typeof refreshWalletAdsAdmin==='function')act(refreshWalletAdsAdmin);if(!user)history.replaceState(null,'','#account');if(user&&appRouteName()==='account')history.replaceState(null,'','#products');appCurrentView=null;applyAppRoute(false);if(user&&appRouteName()==='products'&&savedCatalog){catalogRouteSnapshot=savedCatalog;act(restoreCatalogRoute)}if(user&&role==='klient'&&pendingGuestProductId!==null){const productId=pendingGuestProductId;pendingGuestProductId=null;expandedCatalogProducts.add(productId);navigateApp('products');act(async()=>{await loadProducts();const product=[...document.querySelectorAll('#products details.catalog-product')].find(card=>card.dataset.productId===String(productId));if(product)product.scrollIntoView({block:'nearest'});});}else if(user){pendingGuestProductId=null;}};
globalThis.addEventListener('hashchange',()=>applyAppRoute(document.activeElement?.id!=='point-name'));
document.addEventListener('click',event=>{
 const link=event.target.closest('a[href^="#"]');if(!link||event.defaultPrevented)return;
 const id=link.hash.slice(1),view=appRouteAliases[id]||id;
 if(appViewGroups[view]){event.preventDefault();navigateApp(view);}
});
// Keep existing GPS semantics, including a deliberate click and saved location.
el('nearby-nav-link').onclick=event=>{event.preventDefault();navigateApp('nearby');applyAppRoute(false);act(openNearby)};
el('catalog-use-location').onclick=()=>navigateApp('nearby');
applyAppRoute(false);
function renderCatalogPages(){
 if(typeof catalogRouteSnapshot!=='undefined')rememberCatalogRoute();
 const host=el('catalog-pages');host.replaceChildren();
 const total=Math.min(Math.ceil(catalogTotal/catalogPageSize),501),page=Math.floor(catalogOffset/catalogPageSize)+1;
 const pages=new Set([1,total,page-2,page-1,page,page+1,page+2].filter(n=>n>=1&&n<=total));
 let previous=0;
 for(const number of [...pages].sort((a,b)=>a-b)){
  if(previous&&number>previous+1)host.append(node('span','…'));
  const b=node('button',String(number));b.type='button';b.setAttribute('aria-label','Strona produktów '+number);
  if(number===page)b.setAttribute('aria-current','page');b.disabled=number===page;
  b.onclick=()=>{if(catalogLoading)return;catalogOffset=(number-1)*catalogPageSize;act(loadProducts)};host.append(b);previous=number;
 }
}
el('seller-listings-refresh').onclick=()=>act(loadSellerListings);
el('point-delete').onclick=()=>act(async()=>{
 const point=pointEditorItems.find(p=>String(p.id)===el('point-edit-select').value);if(!point||role!=='rolnik')return;
 if(!confirm('Usunąć punkt z aktywnych? Historia i wykorzystanie promocji pozostaną zapisane. Punkt z aktywnymi zamówieniami nie może zostać usunięty.'))return;
 const epoch=sessionEpoch;await api('/pickup-points/'+point.id,'DELETE');if(epoch!==sessionEpoch)return;
 msg('Punkt usunięty z aktywnych. Historia została zachowana.');await loadFarmer();
});
// Only public product filters enter history. Customer coordinates stay in memory/DB.
let catalogRouteSnapshot=null,catalogRouteRestoring=false;
function catalogRouteParams(){
 const p=new URLSearchParams();p.set('page',String(Math.floor(catalogOffset/catalogPageSize)+1));
 if(el('catalog-query').value.trim())p.set('q',el('catalog-query').value.trim());
 if(categorySelection)p.set('category',categorySelection);
 if(subcategorySelection)p.set('subcategory',subcategorySelection);
 if(el('catalog-available').checked)p.set('available','1');
 if(el('catalog-fulfillment').value!=='all')p.set('fulfillment',el('catalog-fulfillment').value);
 if(el('catalog-sort').value!=='newest')p.set('sort',el('catalog-sort').value);
 if(catalogSellerId!==null)p.set('seller',String(catalogSellerId));
 return p.toString();
}
function rememberCatalogRoute(){
 if(catalogRouteRestoring)return;
 catalogRouteSnapshot=catalogRouteParams();
 if(appCurrentView!=='products'||sellerSearchMode())return;
 const hash='#products?'+catalogRouteSnapshot;
 if(location.hash!==hash)history.pushState(null,'',hash);
}
async function restoreCatalogRoute(){
 if(appRouteName()!=='products')return;
 const query=location.hash.includes('?')?location.hash.split('?')[1]:catalogRouteSnapshot;
 if(!query)return;
 catalogRouteRestoring=true;
 try{
  await ensureProductTaxonomy();
  const p=new URLSearchParams(query),page=Number(p.get('page')||1);
  catalogOffset=Number.isInteger(page)&&page>=1&&page<=501?(page-1)*20:0;
  el('catalog-query').value=(p.get('q')||'').slice(0,120);
  categorySelection=productTaxonomy.some(c=>c.id===p.get('category'))?p.get('category'):null;
  subcategorySelection=productTaxonomy.find(c=>c.id===categorySelection)?.subcategories.some(s=>s.id===p.get('subcategory'))?p.get('subcategory'):null;
  renderCategorySelection();el('catalog-available').checked=p.get('available')==='1';
  el('catalog-fulfillment').value=['odbior','dostawa'].includes(p.get('fulfillment'))?p.get('fulfillment'):'all';
  el('catalog-sort').value=p.get('sort')==='nearest'?'nearest':'newest';
  const seller=Number(p.get('seller'));catalogSellerId=Number.isSafeInteger(seller)&&seller>0?seller:null;
  await loadProducts();
 }finally{catalogRouteSnapshot=catalogRouteParams();catalogRouteRestoring=false}
}
globalThis.addEventListener('hashchange',()=>act(restoreCatalogRoute));
act(restoreCatalogRoute);
// Optional modules may create their route root after an asynchronous config read.
const appRouteRoots=new Set(Object.values(appViewGroups).flat());
new MutationObserver(records=>{
 if(records.some(record=>[...record.addedNodes].some(n=>n.nodeType===1&&appRouteRoots.has(n.id))))applyAppRoute(false);
}).observe(document.body,{childList:true,subtree:true});


// Seller ratings: attach compact controls only to completed client orders.
// Keep the owner-approved HTML, CSS and product layout untouched.
const loadOrdersBeforeSellerRatings=loadOrders;
loadOrders=async function(...args){
 const result=await loadOrdersBeforeSellerRatings.apply(this,args);
 if(role!=='klient')return result;
 const root=el('orders');
 if(!root)return result;
 const completed=[...root.querySelectorAll('[data-order-id]')].filter(card=>
   [...card.querySelectorAll('p')].some(p=>/•\s*odebrane(?:\s|$)/.test(p.textContent))&&!card.querySelector('[data-seller-rating]'));
 for(const card of completed){
  const orderId=Number(card.dataset.orderId);
  if(!Number.isSafeInteger(orderId)||orderId<=0)continue;
  const section=node('div','','seller-rating-control');
  section.dataset.sellerRating=String(orderId);
  const label=node('label','Oceń sprzedawcę: ');
  const select=node('select');
  select.setAttribute('aria-label','Ocena sprzedawcy w gwiazdkach');
  for(let stars=5;stars>=1;stars--){
   const option=node('option', '★'.repeat(stars)+'☆'.repeat(5-stars));
   option.value=String(stars);
   select.append(option);
  }
  const submit=node('button','Wystaw ocenę');
  submit.type='button';
  label.append(select);
  section.append(label,submit);
  card.append(section);
  // A previous rating is private to the buyer; do not offer a second one.
  const currentEpoch=sessionEpoch;
  // Wait for the server's prior-rating check before allowing a new submission.
  // A slow response must never overwrite a successful new rating.
  submit.disabled=true;
  let submitted=false;
  submit.onclick=()=>act(async()=>{
   if(submit.disabled)return;
   submit.disabled=true;
   try{
    const selectedStars=Number(select.value);
    await api('/seller-ratings','POST',{order_id:orderId,stars:selectedStars});
    submitted=true;
    if(currentEpoch!==sessionEpoch||!section.isConnected)return;
    section.replaceChildren(node('p','Twoja ocena: '+'★'.repeat(selectedStars)+'☆'.repeat(5-selectedStars)));
   }catch(error){
    if(String(error).includes('To zamówienie zostało już ocenione'))section.replaceChildren(node('p','To zamówienie zostało już ocenione.'));
    else{submit.disabled=false;throw error;}
   }
  });
  void api('/seller-ratings/orders/'+orderId).then(existing=>{
   if(currentEpoch!==sessionEpoch||!section.isConnected||submitted)return;
   if(existing&&Number.isInteger(existing.stars)&&existing.stars>=1&&existing.stars<=5){
    section.replaceChildren(node('p','Twoja ocena: '+'★'.repeat(existing.stars)+'☆'.repeat(5-existing.stars)));
   }else if(existing&&existing.order_id===orderId&&existing.stars===null){
    submit.disabled=false;
   }else{
    // An unexpected response is not proof that this order has no rating.
    submit.disabled=true;
    const notice=node('p','Nie udało się potwierdzić stanu oceny. Odśwież zamówienia.');
    notice.setAttribute('role','status');
    section.append(notice);
   }
  }).catch(()=>{
   // Fail closed: a failed lookup must not offer a duplicate rating.
   if(currentEpoch!==sessionEpoch||!section.isConnected||submitted)return;
   submit.disabled=true;
   const notice=node('p','Nie udało się sprawdzić poprzedniej oceny. Odśwież zamówienia i spróbuj ponownie.');
   notice.setAttribute('role','status');
   section.append(notice);
  });
 }
 return result;
};


// Show public seller rating averages next to product offers without changing
// the owner-approved product card markup or layout styles.
const sellerRatingsByProduct=new Map();
const catalogPageBeforeSellerRatings=catalogPage;
catalogPage=async function(...args){
 const result=await catalogPageBeforeSellerRatings.apply(this,args);
 if(Array.isArray(result)){
  sellerRatingsByProduct.clear();
  for(const item of result){
   const productId=Number(item.id),sellerId=Number(item.farmer_id);
   if(Number.isSafeInteger(productId)&&Number.isSafeInteger(sellerId)&&sellerId>0)
    sellerRatingsByProduct.set(productId,sellerId);
  }
 }
 return result;
};
const loadProductsBeforeSellerRatings=loadProducts;
let sellerRatingRenderGeneration=0;
loadProducts=async function(...args){
 const generation=++sellerRatingRenderGeneration;
 const result=await loadProductsBeforeSellerRatings.apply(this,args);
 if(generation!==sellerRatingRenderGeneration)return result;
 const root=el('products');
 if(!root||!sellerRatingsByProduct.size)return result;
 const currentEpoch=sessionEpoch;
 const bySeller=new Map();
 for(const card of root.querySelectorAll('.catalog-product[data-product-id]')){
  const sellerId=sellerRatingsByProduct.get(Number(card.dataset.productId));
  if(!sellerId||card.querySelector('[data-seller-stars]'))continue;
  if(!bySeller.has(sellerId))bySeller.set(sellerId,[]);
  bySeller.get(sellerId).push(card);
 }
 for(const [sellerId,cards] of bySeller){
  void api('/sellers/'+sellerId+'/rating').then(rating=>{
   if(generation!==sellerRatingRenderGeneration||currentEpoch!==sessionEpoch||!rating||rating.seller_id!==sellerId||!Number.isSafeInteger(rating.count)||rating.count<0)return;
   const average=rating.count>0?Number(rating.average):null;
   if(rating.count>0&&(!Number.isFinite(average)||average<1||average>5))return;
   for(const card of cards){
    if(!card.isConnected||card.querySelector('[data-seller-stars]'))continue;
    const description=rating.count===0?' ☆☆☆☆☆ (0 ocen)':' ★ '+average.toLocaleString('pl-PL',{minimumFractionDigits:1,maximumFractionDigits:2})+'/5 ('+rating.count+' ocen)';
    const stars=node('span',description);
    stars.dataset.sellerStars=String(sellerId);
    stars.setAttribute('aria-label',rating.count===0?'Sprzedawca nie ma jeszcze ocen':'Ocena sprzedawcy '+average+' na 5, liczba ocen: '+rating.count);
    const summary=card.querySelector('summary');
    if(summary)summary.append(stars);
   }
  }).catch(()=>{/* Ratings are optional; never block product browsing. */});
 }
 return result;
};


// Minimum 5 PLN applies to checkout, not to adding a low-priced item to cart.
// Intercept only direct-order clicks below the threshold; keep approved app.js untouched.
const checkoutProductPrices=new Map();
const catalogPageBeforeMinimumCart=catalogPage;
catalogPage=async function(...args){
 const result=await catalogPageBeforeMinimumCart.apply(this,args);
 if(Array.isArray(result)){
  checkoutProductPrices.clear();
  for(const product of result){
   if(Number.isSafeInteger(product.id)&&Number.isSafeInteger(product.price_grosze))
    checkoutProductPrices.set(product.id,product.price_grosze);
  }
 }
 return result;
};
document.addEventListener('click',event=>{
 const button=event.target.closest?.('button');
 if(!button||button.textContent.trim()!=='Zamów testowo'||role!=='klient')return;
 // Approved catalog layout moves expanded controls into a spanning sibling panel.
 const panel=button.closest('.catalog-row-details[data-product-id]');
 const card=button.closest('.catalog-product[data-product-id]');
 const container=panel||card;
 if(!container)return;
 const price=checkoutProductPrices.get(Number(container.dataset.productId));
 const quantity=Number(container.querySelector('input[aria-label^="Ilość w jednostce"]')?.value);
 if(!Number.isSafeInteger(price)||!Number.isSafeInteger(quantity)||quantity<1)return;
 if(price*quantity>=500)return;
 // The direct order would deterministically fail the minimum-value validation.
 // Reuse the existing cart handler instead, without issuing any order request.
 event.preventDefault();
 event.stopImmediatePropagation();
 const add=Array.from(container.querySelectorAll('button')).find(b=>b.textContent.trim()==='Dodaj do koszyka');
 if(!add||add.disabled)return;
 add.click();
 msg('Kwota poniżej 5,00 zł — produkt dodajemy do koszyka. Możesz dołożyć kolejne produkty.');
},true);


// Badge represents the total number of product units, not distinct cart lines.
// Keep the server-side navigation-count endpoint in sync with this calculation.
const loadCartBeforeUnitBadge=loadCart;
loadCart=async function(...args){
 const result=await loadCartBeforeUnitBadge.apply(this,args);
 if(role==='klient'&&Array.isArray(cartQuoteItems)){
  const count=cartQuoteItems.reduce((total,item)=>total+item.quantity,0);
  if(Number.isSafeInteger(count)&&count>=0)setNavigationCount('cart-count',count,'Sztuki produktów w koszyku');
 }
 return result;
};


// Show the human-readable reference without changing immutable shipment IDs.
// Keep the mapping local to this page; never store the PIN or mapping in storage.
const displayShipmentRefs=new Map();
const apiBeforeDisplayShipment=api;
api=async function(path,...args){
 const result=await apiBeforeDisplayShipment.call(this,path,...args);
 if(path==='/cart/checkout-test'&&result&&typeof result.shipment_id==='string'&&
    /^[A-Z][0-9]{3,}-[0-9]{3}$/.test(result.display_shipment_number||'')){
  displayShipmentRefs.set(result.shipment_id,result.display_shipment_number);
 }
 return result;
};
const cartResultForShipment=el('cart-result');
if(cartResultForShipment){
 const updateShipmentLabel=()=>{
  const current=cartResultForShipment.textContent||'';
  if(!current.includes('WPS-'))return;
  for(const [technical,visible] of displayShipmentRefs){
   if(current.includes(technical)){
    cartResultForShipment.textContent=current.replace(technical,visible);
    break;
   }
  }
 };
 new MutationObserver(updateShipmentLabel).observe(cartResultForShipment,{childList:true,characterData:true,subtree:true});
}


// Show the same persisted public shipment reference in buyer and seller orders.
// The technical shipment_id stays available for PIN recovery and API calls.
const orderShipmentPublicRefs=new Map();
const apiBeforeOrderPublicRefs=api;
api=async function(path,...args){
 const result=await apiBeforeOrderPublicRefs.call(this,path,...args);
 if(path==='/orders/me'&&Array.isArray(result)){
  orderShipmentPublicRefs.clear();
  for(const order of result){
   if(order?.id&&/^[A-Z][0-9]{3,}-[0-9]{3}$/.test(order.display_shipment_number||'')){
    orderShipmentPublicRefs.set(String(order.id),order.display_shipment_number);
   }
  }
 }
 return result;
};
const loadOrdersBeforePublicRefs=loadOrders;
loadOrders=async function(...args){
 const result=await loadOrdersBeforePublicRefs.apply(this,args);
 const host=el('orders');
 if(host){
  for(const card of host.querySelectorAll('[data-order-id]')){
   const publicNumber=orderShipmentPublicRefs.get(card.dataset.orderId);
   if(!publicNumber||card.querySelector('[data-shipment-public-ref]'))continue;
   const label=node('p','Przesyłka '+publicNumber);
   label.dataset.shipmentPublicRef='true';
   const summary=card.querySelector(':scope > summary');
   if(summary)summary.after(label);
   else card.prepend(label);
  }
 }
 return result;
};

// Inform sellers of the renewal price without initiating an unimplemented charge.
const loadFarmerBeforeRenewalInfo=loadFarmer;
loadFarmer=async function(...args){
  const result=await loadFarmerBeforeRenewalInfo.apply(this,args);
  if(role!=='rolnik')return result;
  const host=el('my-points');if(!host)return result;
  try{
    const points=await api('/farmers/me/pickup-points');
    if(role!=='rolnik')return result;
    const note=node('p',`Odnowienie: 10,00 zł za każdy punkt na 30 dni. Płatności za punkty nie są jeszcze uruchomione w demo.`);
    note.dataset.pointRenewalInfo='true';
    if(!host.querySelector('[data-point-renewal-info]'))host.prepend(note);
    for(const pt of points){
      const p=node('p',`${pt.name}: ${pt.promotion_active?'promocja aktywna do '+pt.promotion.free_until:pt.promotion?'promocja wygasła':'bez aktywnej promocji'} · odnowienie 10,00 zł / 30 dni`);
      p.dataset.pointRenewalInfo='true';host.append(p);
    }
  }catch(_e){}
  return result;
};


// Optional advertisement slots in unused space. Never alter the approved
// forms, their widths, or the five-second wallet advertisement overlay.
// A missing campaign is a compact placeholder, not a fabricated coupon.
(function installMarketplaceAdSlots(){
 const style=document.createElement('style');
 style.textContent=`
 .wp-ad-slot{box-sizing:border-box;min-width:0;margin:14px 0;padding:14px 18px;border:1px solid #d9e3d9;border-radius:12px;background:#f8faf7;color:#263c2b;display:grid;gap:7px;align-content:center}
 .wp-ad-slot .wp-ad-label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#637369}
 .wp-ad-slot strong{font-size:17px}
 .wp-ad-slot p{margin:0;line-height:1.5}
 .wp-ad-slot a{color:#236a38;text-decoration:underline}
 .wp-ad-slot[hidden]{display:none!important}
 @media(min-width:950px){.wp-ad-slot[data-layout="side"]{min-height:175px}}
 @media(max-width:600px){.wp-ad-slot{padding:12px;min-height:0}}
 `;
 document.head.append(style);
 const defaultCampaigns={
  login:{title:'Promocja dla sprzedawców',body:'3 punkty odbioru bez opłaty przez 30 dni każdy. Kod promocyjny podasz po zalogowaniu na konto sprzedawcy.'},
  buyer:{title:'Miejsce na reklamę',body:'Tutaj pojawią się oferty i reklamy dla kupujących.'},
  seller:{title:'Miejsce na reklamę',body:'Tutaj pojawią się reklamy dla sprzedawców.'}
 };
 const slots=[
  {id:'login',after:'#account-section',roles:['guest']},
  {id:'buyer',after:'#nearby-section',roles:['klient']},
  {id:'seller',after:'#seller-listings-section',roles:['rolnik']}
 ];
 // Future admin-managed campaigns can replace these safe text defaults.
 // Campaign content is always inserted with textContent, never innerHTML.
 function setCampaign(slotId,campaign){
  if(!Object.prototype.hasOwnProperty.call(defaultCampaigns,slotId))return false;
  if(!campaign||typeof campaign.title!=='string'||typeof campaign.body!=='string'
    ||!campaign.title.trim()||!campaign.body.trim()
    ||campaign.title.length>100||campaign.body.length>500)return false;
  const host=document.querySelector('[data-ad-slot="'+slotId+'"]');
  if(!host)return false;
  host.querySelector('strong').textContent=campaign.title;
  host.querySelector('p').textContent=campaign.body;
  return true;
 }
 window.WiejskaPakaAdSlots=Object.freeze({setCampaign});
 for(const config of slots){
  const target=document.querySelector(config.after);if(!target)continue;
  const host=document.createElement('aside');
  host.className='wp-ad-slot';host.dataset.adSlot=config.id;
  host.setAttribute('aria-label','Reklama');host.hidden=true;
  const label=document.createElement('span');label.className='wp-ad-label';label.textContent='Reklama';
  const title=document.createElement('strong');title.textContent=defaultCampaigns[config.id].title;
  const body=document.createElement('p');body.textContent=defaultCampaigns[config.id].body;
  host.append(label,title,body);
  // Ads belong to routed sections; never nest them inside login/product forms.
  target.append(host);
 }
 function refresh(){
  const current=typeof role==='string'&&role?role:'guest';
  const route=typeof appRouteName==='function'?appRouteName():'account';
  for(const config of slots){
   const host=document.querySelector('[data-ad-slot="'+config.id+'"]');
   if(!host)continue;
   const allowed=config.roles.includes(current) &&
     (config.id==='login'?route==='account':config.id==='buyer'?route==='nearby':route==='listings') &&
     !host.closest('[data-route-hidden]') && !host.closest('[hidden]');
   host.hidden=!allowed;
  }
 }
 refresh();
 // Public campaigns are refreshed after administrator changes or login.
 // Reset to safe fallback when a campaign has expired or was disabled.
 async function reloadCampaigns(){
  await Promise.all(slots.map(async config=>{
   try{
    const response=await fetch('/ads/slots/'+config.id,{credentials:'same-origin',cache:'no-store'});
    if(!response.ok)return;
    const data=await response.json();
    setCampaign(config.id,data?.campaign||defaultCampaigns[config.id]);
   }catch(_error){/* Keep last safe text when offline. */}
  }));
 }
 window.addEventListener('wiejskapaka:ads-updated',()=>{void reloadCampaigns();});
 void reloadCampaigns();
 // Session and panel routing are dynamic; reflect them without polling.
 const identity=document.getElementById('identity');
 if(identity)new MutationObserver(()=>{refresh();void reloadCampaigns();}).observe(identity,{childList:true,subtree:true,characterData:true});
 document.addEventListener('click',()=>queueMicrotask(refresh),true);
 window.addEventListener('hashchange',refresh);
 document.addEventListener('wiejskapaka:route-changed',refresh);
})();


// Admin editor for marketplace text campaigns. Kept separate from the
// existing wallet interstitial editor and from the approved HTML layout.
(function installMarketplaceAdAdmin(){
 const dashboard=document.getElementById('dashboard');if(!dashboard)return;
 const section=document.createElement('section');section.id='marketplace-ads-admin';
 section.className='wide-section';section.hidden=true;
 const heading=document.createElement('h2');heading.textContent='Reklamy w panelach i przy logowaniu';
 const intro=document.createElement('p');intro.textContent='Reklamy tekstowe dla klientów, sprzedawców i gości. Włączona kampania pojawi się tylko w wyznaczonym terminie. Reklamy portfela są zarządzane osobno.';
 const form=document.createElement('form');form.className='card';
 const fields=[
  ['slot','Miejsce reklamy','select'],
  ['title','Nagłówek','text'],
  ['body','Treść','textarea'],
  ['starts_at','Początek','datetime-local'],
  ['ends_at','Koniec','datetime-local'],
  ['enabled','Aktywna','checkbox']
 ];
 const controls={};
 for(const [name,labelText,type] of fields){
  const label=document.createElement('label');label.textContent=labelText+' ';
  let input;
  if(type==='select'){
   input=document.createElement('select');
   for(const [value,caption] of [['login','Logowanie'],['buyer','Klient'],['seller','Sprzedawca']]){
    const option=document.createElement('option');option.value=value;option.textContent=caption;input.append(option);
   }
  }else input=document.createElement(type==='textarea'?'textarea':'input');
  if(type!=='textarea'&&type!=='select')input.type=type;
  input.name=name;if(type!=='checkbox')input.required=true;
  if(name==='title')input.maxLength=100;
  if(name==='body')input.maxLength=500;
  label.append(input);form.append(label);controls[name]=input;
 }
 const save=document.createElement('button');save.type='submit';save.textContent='Zapisz kampanię';
 const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Nowa kampania';
 form.append(save,cancel);
 const status=document.createElement('p');status.setAttribute('role','status');
 const list=document.createElement('div');list.setAttribute('aria-label','Zapisane kampanie');
 section.append(heading,intro,form,status,list);dashboard.after(section);
 appViewGroups.dashboard.push(section.id);
 let editing=null;
 function reset(){editing=null;form.reset();save.textContent='Dodaj kampanię';const start=new Date();const end=new Date(start.getTime()+30*86400000);controls.starts_at.value=dateLocal(Math.floor(start.getTime()/1000));controls.ends_at.value=dateLocal(Math.floor(end.getTime()/1000));}
 const dateLocal=value=>{const d=new Date(value*1000);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);};
 reset();
 cancel.addEventListener('click',reset);
 function payload(){
  return {slot:controls.slot.value,title:controls.title.value.trim(),body:controls.body.value.trim(),
   enabled:controls.enabled.checked,
   starts_at:Math.floor(new Date(controls.starts_at.value).getTime()/1000),
   ends_at:Math.floor(new Date(controls.ends_at.value).getTime()/1000)};
 }
 async function refresh(){
  if(role!=='admin'){section.hidden=true;return;}
  section.hidden=false;
  section.toggleAttribute('data-route-hidden',appRouteName()!=='dashboard');
  try{
   const data=await api('/admin/ads/slots');
   if(role!=='admin')return;
   if(!data||!Array.isArray(data.items))throw new Error('Niepoprawna odpowiedź serwera');
   list.replaceChildren();
   if(!data.items.length){const empty=document.createElement('p');empty.textContent='Brak kampanii. Dodaj pierwszą reklamę.';list.append(empty);}
   for(const item of data.items){
    const card=document.createElement('div');card.className='card';
    const text=document.createElement('p');
    text.textContent=(item.enabled?'Aktywna':'Wyłączona')+' · '+item.slot+' · '+item.title+' · '+new Date(item.starts_at*1000).toLocaleDateString('pl-PL')+' – '+new Date(item.ends_at*1000).toLocaleDateString('pl-PL');
    const edit=document.createElement('button');edit.type='button';edit.textContent='Edytuj';
    edit.onclick=()=>{editing=item.id;controls.slot.value=item.slot;controls.title.value=item.title;controls.body.value=item.body;
      controls.starts_at.value=dateLocal(item.starts_at);controls.ends_at.value=dateLocal(item.ends_at);
      controls.enabled.checked=Boolean(item.enabled);save.textContent='Zapisz zmiany';form.scrollIntoView({block:'nearest'});};
    const disable=document.createElement('button');disable.type='button';disable.textContent='Wyłącz';
    disable.disabled=!item.enabled;
    disable.onclick=()=>act(async()=>{disable.disabled=true;try{await api('/admin/ads/slots/'+encodeURIComponent(item.id),'DELETE');await refresh();window.dispatchEvent(new Event('wiejskapaka:ads-updated'));}catch(e){status.textContent=String(e.message||e);disable.disabled=false;}});
    card.append(text,edit,disable);list.append(card);
   }
  }catch(e){status.textContent='Nie udało się pobrać reklam: '+String(e.message||e);}
 }
 form.addEventListener('submit',event=>{
  event.preventDefault();
  act(async()=>{
   const data=payload();
   if(!Number.isSafeInteger(data.starts_at)||!Number.isSafeInteger(data.ends_at)||data.ends_at<=data.starts_at){
    status.textContent='Wprowadź poprawny termin rozpoczęcia i zakończenia.';return;
   }
   save.disabled=true;
   try{
    await api(editing?'/admin/ads/slots/'+encodeURIComponent(editing):'/admin/ads/slots',editing?'PUT':'POST',data);
    status.textContent='Kampania zapisana.';reset();await refresh();window.dispatchEvent(new Event('wiejskapaka:ads-updated'));
   }catch(e){status.textContent='Nie zapisano: '+String(e.message||e);}
   finally{save.disabled=false;}
  });
 });
 const previousLogged=logged;
 logged=function(...args){const result=previousLogged.apply(this,args);if(role==='admin')act(refresh);else section.hidden=true;return result;};
 document.addEventListener('wiejskapaka:route-changed',()=>{
  if(role==='admin')section.toggleAttribute('data-route-hidden',appRouteName()!=='dashboard');
 });
 if(role==='admin')act(refresh);
})();
