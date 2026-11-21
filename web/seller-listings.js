"use strict";
let sellerListingsRequest=0;
const loginGuides={
 rolnik:{
  title:'Jak zacząć sprzedawać w WiejskiejPace?',
  closeLabel:'Zamknij instrukcję sprzedawcy',
  steps:[
   ['Dodaj pierwszą ofertę.','W „Moje ogłoszenia” dodaj zdjęcie, wpisz cenę i podaj dostępną ilość produktu.'],
   ['Ustaw punkt odbioru.','W „Punktach odbioru” dodaj punkt na mapie, dni i godziny odbioru. Z kodem rabatowym pierwsze 3 punkty są darmowe przez 30 dni od aktywacji każdego punktu. Kod skopiujesz z okienka przy pierwszej ofercie.'],
   ['Sprawdzaj zamówienia.','W „Zamówieniach” zobaczysz, co przygotować na każdy punkt. Przy dostawie na adres potwierdź termin lub zaproponuj inny.'],
   ['Potwierdź przybycie i wydaj zamówienie.','Na miejscu kliknij „Jestem na miejscu” i zezwól na odczyt GPS. Klienci z zamówieniami na ten punkt dostaną powiadomienie. Przy wydaniu poproś klienta o PIN odbioru.'],
   ['Sprawdzaj środki w portfelu.','W „Portfelu” zobaczysz saldo. WiejskaPaka pobiera 5% od każdej wypłaty z portfela sprzedawcy. Przy wypłacie 100 zł otrzymasz 95 zł.']
  ]
 },
 klient:{
  title:'Jak kupować w WiejskiejPace?',
  closeLabel:'Zamknij instrukcję klienta',
  steps:[
   ['Znajdź produkty.','W „Produktach” wyszukaj to, czego potrzebujesz, a w „Blisko mnie” sprawdź oferty w okolicy. Serduszkiem zapiszesz produkt w „Ulubionych”.'],
   ['Złóż zamówienie.','Dodaj produkty do koszyka. Wybierz punkt odbioru lub dostawę na adres, jeśli sprzedawca ją oferuje. Przed złożeniem zamówienia sprawdź koszt i sposób odbioru.'],
   ['Sprawdź zamówienie.','W „Zamówieniach” zobaczysz jego status i dane odbioru. Przy dostawie sprawdź potwierdzony lub zaproponowany termin.'],
   ['Odbierz zamówienie.','Gdy sprzedawca potwierdzi przybycie do Twojego punktu odbioru, dostaniesz powiadomienie. Przy odbiorze podaj sprzedawcy PIN z zamówienia.'],
   ['Sprawdź środki w portfelu.','W „Portfelu” zobaczysz saldo i historię. WiejskaPaka nie pobiera prowizji od wypłaty z portfela klienta.']
  ]
 }
};
const guideLoginCounts=new Map();
const guideLoginLimit=5;
let loginGuide;
let loginGuideTimer;

function openLoginGuide({title,closeLabel,steps:instructions}){
 if(loginGuide?.open)return;
 const dialog=node('dialog','','same-package-dialog login-guide');
 dialog.id='login-guide';
 dialog.setAttribute('aria-labelledby','login-guide-title');
 const header=node('div','','wallet-ad-heading login-guide-heading');
 const heading=node('h2',title);
 heading.id='login-guide-title';
 heading.tabIndex=-1;
 heading.autofocus=true;
 const timer=node('span','5');
 timer.setAttribute('role','timer');
 timer.setAttribute('aria-label','Sekundy do odblokowania przycisku zamknięcia');
 const close=node('button','×');
 close.type='button';
 close.disabled=true;
 close.setAttribute('aria-label',closeLabel);
 header.append(heading,timer,close);

 const steps=node('ol');
 for(const [title,body] of instructions){
  const step=node('li');
  step.append(node('strong',title),' '+body);
  steps.append(step);
 }
 dialog.append(header,steps);
 const dismiss=()=>{
  if(close.disabled||!dialog.open)return;
  clearTimeout(loginGuideTimer);
  dialog.close();
  dialog.remove();
  loginGuide=null;
  el('panel-nav-link').focus();
 };
 close.onclick=dismiss;
 dialog.oncancel=event=>{event.preventDefault();dismiss();};
 document.body.append(dialog);
 loginGuide=dialog;
 dialog.showModal();
 const end=performance.now()+5000;
 const tick=()=>{
  const remaining=end-performance.now();
  timer.textContent=String(Math.max(0,Math.ceil(remaining/1000)));
  if(remaining<=0){close.disabled=false;timer.hidden=true;return;}
  loginGuideTimer=setTimeout(tick,remaining%1000||1000);
 };
 loginGuideTimer=setTimeout(tick,1000);
}

async function showGuideOnLogin(user){
 clearTimeout(loginGuideTimer);
 if(loginGuide){loginGuide.close();loginGuide.remove();loginGuide=null;}
 const guide=loginGuides[user?.role];
 if(!guide)return;
 const key='wp-login-guide-v2:'+user.role+':'+user.id;
 let previous=guideLoginCounts.get(key)||0;
 try{
  const stored=Number(localStorage.getItem(key));
  if(Number.isInteger(stored)&&stored>=0)previous=Math.max(previous,stored);
  if(user.role==='rolnik'&&localStorage.getItem('wp-seller-guide-v1:'+user.id)==='dismissed')
   previous=Math.max(previous,1);
 }catch(_error){/* Use the in-page count when storage is unavailable. */}
 if(previous>=guideLoginLimit)return;
 if(user.role==='rolnik'&&appCurrentView==='products'){
  const epoch=sessionEpoch;
  let products;
  try{products=await api('/products/mine');}catch(_error){}
  if(epoch!==sessionEpoch)return;
  if(appCurrentView==='products'&&products?.length===0)navigateApp('dashboard');
 }
 openLoginGuide(guide);
 guideLoginCounts.set(key,previous+1);
 try{localStorage.setItem(key,String(previous+1));}catch(_error){}
}

let firstListingNoticeEpoch;
const firstListingNotice=node('dialog','','same-package-dialog');
firstListingNotice.id='first-listing-notice';
firstListingNotice.setAttribute('aria-labelledby','first-listing-heading');
document.body.append(firstListingNotice);
document.addEventListener('wiejskapaka:route-changed',()=>{
 if(firstListingNotice.open&&(role!=='rolnik'||appCurrentView!=='listings'||firstListingNoticeEpoch!==sessionEpoch))
  firstListingNotice.close();
 if(firstListingNoticeEpoch!==sessionEpoch&&firstListingNotice.hasChildNodes())
  firstListingNotice.replaceChildren();
});

async function showFirstListingNotice(epoch,current){
 if(appCurrentView!=='listings'||firstListingNoticeEpoch===epoch)return;
 let code;
 try{({code}=await api('/farmers/me/pickup-promotions/starter'));}
 catch(_error){/* The fee notice remains available if the promotion check fails. */}
 if(!current()||appCurrentView!=='listings'||firstListingNoticeEpoch===epoch)return;
 firstListingNoticeEpoch=epoch;
 const heading=node('h2','Dodajesz pierwszą ofertę');
 heading.id='first-listing-heading';
 const fee=node('p','WiejskaPaka pobiera 5% od każdej wypłaty z portfela sprzedawcy.');
 const promo=node('p','Z aktywnym kodem rabatowym pierwsze 3 punkty odbioru są darmowe przez 30 dni od aktywacji każdego punktu.');
 const close=node('button','Przejdź do dodawania oferty');
 close.type='button';
 close.autofocus=true;
 close.onclick=()=>{
  firstListingNotice.close();
  el('new-product').querySelector('select').focus();
 };
 firstListingNotice.replaceChildren(heading,fee,promo);
 if(code){
  const label=node('label','Kod rabatowy'),value=node('input');
  value.value=code;
  value.readOnly=true;
  label.append(value);
  const copy=node('button','Kopiuj kod'),use=node('button','Przejdź do realizacji kodu'),status=node('p');
  status.setAttribute('role','status');
  copy.type=use.type='button';
  copy.onclick=async()=>{
   try{
    await navigator.clipboard.writeText(code);
    status.textContent='Kod skopiowany.';
   }catch(_error){
    value.select();
    status.textContent='Kod zaznaczony. Skopiuj go ręcznie.';
   }
  };
  use.onclick=()=>{
   firstListingNotice.close();
   navigateApp('points');
   const input=el('pickup-promo-code');
   input.value=code;
   input.focus();
  };
  firstListingNotice.append(label,copy,use,status);
 }
 firstListingNotice.append(close);
 firstListingNotice.showModal();
}

async function loadSellerListings(){
 const epoch=sessionEpoch,request=++sellerListingsRequest;
 const current=()=>epoch===sessionEpoch&&request===sellerListingsRequest&&role==='rolnik';
 const host=el('seller-listings');
 if(role!=='rolnik'){host.replaceChildren();return}
 el('seller-listings-status').textContent='Pobieranie ofert…';
 const products=await api('/products/mine');if(!current())return;
 if(!products.length)await showFirstListingNotice(epoch,current);
 if(!current())return;
 host.replaceChildren();
 for(const product of products){
  const card=node('article','','card');card.dataset.sellerListing=String(product.id);
  if(typeof userPhotosEnabled!=='undefined'&&userPhotosEnabled)card.append(photoImage('product',product.id));
  card.append(node('h3',product.name),node('p',`${money(product.price_grosze)} / ${saleUnitLabel(product)} • dostępny stan: ${product.stock} • ${product.listing_active===false?'Wycofana':product.stock?'Dostępna':'Brak towaru'}`));
  const quick=node('form');quick.className='listing-quick-edit';
  const price=node('input');price.value=(product.price_grosze/100).toFixed(2);price.inputMode='decimal';price.required=true;price.setAttribute('aria-label','Cena oferty w zł');
  const stock=node('input');stock.type='number';stock.value=product.stock;stock.min=0;stock.max=1000000;stock.required=true;stock.setAttribute('aria-label','Dostępny stan oferty');
  const priceLabel=node('label','Cena (zł)'),stockLabel=node('label','Dostępne do nowych zamówień');priceLabel.append(price);stockLabel.append(stock);
  const save=node('button','Zapisz cenę i stan');save.type='submit';const status=node('p');status.setAttribute('role','status');
  quick.append(priceLabel,stockLabel,save,status);card.append(quick);
  quick.onsubmit=event=>{event.preventDefault();act(()=>singleWrite('listing:'+product.id,save,async()=>{
   if(!current()||!quick.isConnected)return;
   const price_grosze=parseGrosze(price.value),quantity=Number(stock.value);
   if(price_grosze<1||!Number.isSafeInteger(quantity)||quantity<0||quantity>1000000)throw Error('Podaj poprawną cenę i dostępny stan.');
   status.textContent='Zapisywanie…';
   try{await api('/products/mine/'+product.id,'PATCH',{price_grosze,stock:quantity,expected_stock:product.stock});}
   catch(error){if(current())status.textContent=error.message;throw error}
   if(!current())return;msg('Cena i dostępny stan zapisane. Rezerwacje i wcześniejsze zamówienia pozostają bez zmian.');
   await loadSellerListings();await loadProducts();
  }))};
  const editor=await productEditor(product,current);if(!current())return;card.append(editor);
  const availability=node('button',product.listing_active===false?'Wznów ofertę':'Wycofaj ofertę');availability.type='button';
  availability.onclick=()=>act(()=>singleWrite('listing-active:'+product.id,availability,async()=>{
   if(!current()||!card.isConnected)return;
   if(product.listing_active!==false&&!confirm('Wycofać ofertę z nowych zakupów? Dotychczasowe zamówienia, zdjęcia i towar pozostają zapisane.'))return;
   await api('/products/mine/'+product.id,'PATCH',{listing_active:product.listing_active===false});
   if(current()){msg('Dostępność oferty zapisana.');await loadSellerListings();await loadProducts();}
  }));card.append(availability);host.append(card);
 }
 if(current())el('seller-listings-status').textContent=products.length?'Oferty: '+products.length+'. Stan oznacza wolny towar, bez ilości już zarezerwowanej.':'Nie masz jeszcze ofert. Dodaj pierwszy produkt powyżej.';
}
