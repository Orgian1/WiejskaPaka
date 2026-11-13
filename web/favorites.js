"use strict";
let favoriteIds=new Set(),favoritesSerial=0;
function resetFavorites(){
  favoritesSerial++;favoriteIds.clear();
  el('favorites-results').replaceChildren();el('favorites-status').textContent='';
  el('favorites-section').hidden=!['klient','rolnik'].includes(role);
}
async function loadFavorites(){
  if(!['klient','rolnik'].includes(role))return;
  const serial=++favoritesSerial,epoch=sessionEpoch;
  // Fetch every bounded page so hearts stay correct beyond the first 100 saved offers.
  const products=[];let offset=0;
  for(;;){
    const data=await api(`/favorites?limit=100&offset=${offset}`);
    if(serial!==favoritesSerial||epoch!==sessionEpoch)return;
    products.push(...data.items);
    if(!data.has_more)break;
    offset+=100;if(offset>10000)throw Error('Lista ulubionych przekracza limit.');
  }
  favoriteIds=new Set(products.map(p=>p.id));
  if(typeof setNavigationCount==='function')setNavigationCount('favorites-count',favoriteIds.size,'Ulubione produkty');
  el('favorites-results').replaceChildren();
  for(const product of products){
    const card=node('article','', 'card');
    card.append(node('h3',product.name),node('p',`${money(product.price_grosze)} • Dostępne: ${product.stock}`));
    const media=node('div','', 'favorite-media');
    if(typeof userPhotosEnabled!=='undefined'&&userPhotosEnabled)media.append(photoImage('product',product.id));
    media.append(favoriteButton(product));card.append(media);
    const find=node('button','Pokaż w katalogu');find.type='button';find.onclick=()=>act(async()=>{
      resetCatalogView();
      el('catalog-query').value=product.name;catalogOffset=0;await loadProducts();
      el('products-section').scrollIntoView();
    });card.append(find);el('favorites-results').append(card);
  }
  el('favorites-status').textContent=products.length?`Zapisane oferty: ${products.length}`:'Nie masz jeszcze ulubionych ofert.';
  for(const button of document.querySelectorAll('[data-favorite-product]'))updateFavoriteButton(button);
}
function updateFavoriteButton(button){
  const active=favoriteIds.has(Number(button.dataset.favoriteProduct));
  button.textContent=active?'♥':'♡';button.setAttribute('aria-pressed',String(active));
  button.setAttribute('aria-label',(active?'Usuń z ulubionych: ':'Dodaj do ulubionych: ')+button.dataset.productName);
}
function favoriteButton(product){
  const button=node('button','', 'favorite-button');button.type='button';
  button.dataset.favoriteProduct=String(product.id);button.dataset.productName=product.name;
  updateFavoriteButton(button);
  button.onclick=event=>{event.preventDefault();event.stopPropagation();act(async()=>{
    if(button.disabled)return;
    const epoch=sessionEpoch;button.disabled=true;
    try{
      await api('/favorites/'+product.id,favoriteIds.has(product.id)?'DELETE':'PUT');
      if(epoch!==sessionEpoch)return;
      await loadFavorites();
    }finally{button.disabled=false}
  })};return button;
}
