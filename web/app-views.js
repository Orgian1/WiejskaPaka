"use strict";
// Hash routes work on an ordinary static origin; no token/address is put in URLs.
const appRoutesReady=true;
const appViewGroups={
 products:['products-section'],nearby:['nearby-section'],favorites:['favorites-section'],cart:['cart-section'],
 orders:['orders-section','address-delivery-panel','dashboard'],wallet:['wallet-section'],
 account:['account-section','password-reset-section','account-security','farmer-profile-section','seller-login-panel','seller-compliance','user-photo-panel'],
 listings:['farmer','seller-listings-section'],points:['farmer-details','point-location-panel'],
 dashboard:['dashboard','admin-seller-review','pickup-promotions-admin','wallet-admin-section'],
 notifications:['notifications-section'],contact:['contact-disclosure']
};
const appRouteAliases={'products-section':'products','nearby-section':'nearby','favorites-section':'favorites','cart-section':'cart','orders-section':'orders','address-delivery-panel':'orders','wallet-section':'wallet','account-section':'account','auth':'account','role':'account','account-security':'account','farmer':'listings','farmer-details':'points','point-form':'points','point-location-panel':'points','support-section':'contact','contact-section':'contact','contact-disclosure':'contact','seller-compliance':'account','user-photo-panel':'account','wallet-admin-section':'dashboard','pickup-promotions-admin':'dashboard','admin-seller-review':'dashboard','notifications-section':'notifications'};
let appCurrentView=null;
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
 if(appRouteName()===view){applyAppRoute(true);return}
 location.hash=view;applyAppRoute(false);
}
function applyAppRoute(focus=false){
 const wanted=(el('reset-token').value||(typeof emailProofToken!=='undefined'&&emailProofToken))?'account':appRouteName(),view=appViewAllowed(wanted)?wanted:'account';
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
 if(view==='listings'&&changed)act(loadSellerListings);
 if(view==='points'&&changed&&role==='rolnik')act(loadFarmer);
 if(focus){const heading=el('view-heading');heading.textContent=({products:'Produkty',nearby:'Blisko mnie',favorites:'Ulubione',cart:'Koszyk',orders:'Zamówienia',wallet:'Portfel',account:'Konto',listings:'Moje ogłoszenia',points:'Punkty odbioru',dashboard:'Panel',notifications:'Powiadomienia',contact:'Kontakt'})[view];heading.focus();}
 document.title=({'products':'Produkty','listings':'Moje ogłoszenia','points':'Punkty odbioru'}[view]||'Moje konto')+' — WiejskaPaka';
}
const appLogged=logged;
logged=function(user){appLogged(user);if(!user)history.replaceState(null,'','#account');if(user&&appRouteName()==='account')history.replaceState(null,'','#products');appCurrentView=null;applyAppRoute(false)};
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
 }finally{catalogRouteRestoring=false}
}
globalThis.addEventListener('hashchange',()=>act(restoreCatalogRoute));
act(restoreCatalogRoute);
// Optional modules may create their route root after an asynchronous config read.
const appRouteRoots=new Set(Object.values(appViewGroups).flat());
new MutationObserver(records=>{
 if(records.some(record=>[...record.addedNodes].some(n=>n.nodeType===1&&appRouteRoots.has(n.id))))applyAppRoute(false);
}).observe(document.body,{childList:true,subtree:true});
