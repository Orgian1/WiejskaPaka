"use strict";
let sellerListingsRequest=0;
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
