"use strict";
let sellerListingsRequest=0;
async function loadSellerListings(){
 const epoch=sessionEpoch,request=++sellerListingsRequest;
 const current=()=>epoch===sessionEpoch&&request===sellerListingsRequest&&role==='rolnik';
 const host=el('seller-listings');
 if(role!=='rolnik'){host.replaceChildren();return}
 el('seller-listings-status').textContent='Pobieranie ofert…';
 const products=await api('/products/mine');if(!current())return;
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
