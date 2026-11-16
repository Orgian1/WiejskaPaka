'use strict';
const sellerRatingRequests=new Map(),buyerSavedRatings=new Map();
function resetSellerRatings(){sellerRatingRequests.clear();buyerSavedRatings.clear();}
function refreshSellerRatingSummaries(){sellerRatingRequests.clear();}
function sellerRatingSummary(farmerId){
 const box=node('p','Oceny sprzedawcy: ładowanie…','seller-rating-summary');box.dataset.ratingSeller=String(farmerId);
 const epoch=sessionEpoch;
 const key=epoch+':'+farmerId;
 if(!sellerRatingRequests.has(key))sellerRatingRequests.set(key,api('/farmers/'+encodeURIComponent(farmerId)+'/ratings').catch(error=>{sellerRatingRequests.delete(key);throw error;}));
 sellerRatingRequests.get(key).then(data=>{if(epoch!==sessionEpoch)return;if(!Number.isSafeInteger(data.count)||data.count<0||(data.count>0&&(!Number.isFinite(data.average)||data.average<1||data.average>5)))throw Error();box.textContent=data.count?'★ '+data.average.toLocaleString('pl-PL',{maximumFractionDigits:2})+'/5 · Liczba ocen: '+data.count:'Oceny sprzedawcy: brak ocen (0)';}).catch(()=>{if(epoch===sessionEpoch)box.textContent='Oceny sprzedawcy są chwilowo niedostępne.';});
 return box;
}
function showSavedSellerRating(host,stars){const summary=host.querySelector('.seller-rating-summary');host.replaceChildren(node('p','Twoja ocena: '+'★'.repeat(stars)+'☆'.repeat(5-stars)+' ('+stars+'/5)'));if(summary)host.append(summary);}
function sellerRatingControls(order){
 const host=node('div','','seller-rating-controls');host.dataset.ratingOrder=String(order.id);
 if(role!=='klient'||order.status!=='odebrane')return host;
 const epoch=sessionEpoch,bearer=token,owner=checkoutOwner;
 const current=()=>epoch===sessionEpoch&&bearer===token&&owner===checkoutOwner&&role==='klient'&&host.isConnected;
 api('/orders/'+encodeURIComponent(order.id)+'/seller-rating').then(data=>{
  if(!current())return;
  if(!Number.isSafeInteger(data.farmer_id)||data.farmer_id<1)throw Error('Nieprawidłowy sprzedawca');
  const farmerId=data.farmer_id,key=epoch+':'+owner+':'+order.id;
  if(buyerSavedRatings.has(key))data.stars=buyerSavedRatings.get(key);
  if(Number.isInteger(data.stars)&&data.stars>=1&&data.stars<=5)buyerSavedRatings.set(key,data.stars);
  host.append(sellerRatingSummary(farmerId));
  if(Number.isInteger(data.stars)&&data.stars>=1&&data.stars<=5){showSavedSellerRating(host,data.stars);return;}
  if(data.stars!==null)throw Error('Nieprawidłowa ocena');
  const title=node('p','Oceń sprzedawcę po odbiorze'),group=node('div','','seller-rating-stars'),save=node('button','Zapisz ocenę'),status=node('p');
  group.setAttribute('role','group');group.setAttribute('aria-label','Ocena sprzedawcy od 1 do 5 gwiazdek');status.setAttribute('role','status');
  save.type='button';save.disabled=true;let selected=0,busy=false;const buttons=[];
  for(let stars=1;stars<=5;stars++){
   const button=node('button','★');button.type='button';button.setAttribute('aria-label',stars+' z 5 gwiazdek');button.setAttribute('aria-pressed','false');
   button.onclick=()=>{if(!current()||busy)return;selected=stars;save.disabled=false;for(let i=0;i<5;i++){buttons[i].classList.toggle('selected',i<stars);buttons[i].setAttribute('aria-pressed',String(i+1===stars));}};buttons.push(button);group.append(button);
  }
  host.append(title,group,node('p','Jedna ocena na zakup. Po zapisaniu nie można jej zmienić.'),save,status);
  save.onclick=async()=>{
   if(!current()||busy||!selected)return;busy=true;save.disabled=true;buttons.forEach(b=>b.disabled=true);status.textContent='Zapisywanie…';
   try{
    const result=await api('/orders/'+encodeURIComponent(order.id)+'/seller-rating','POST',{stars:selected});if(!current())return;
    buyerSavedRatings.set(key,result.stars);
    for(const widget of document.querySelectorAll('[data-rating-order]'))if(widget.dataset.ratingOrder===String(order.id))showSavedSellerRating(widget,result.stars);
    sellerRatingRequests.delete(epoch+':'+farmerId);
    for(const box of document.querySelectorAll('[data-rating-seller]'))if(box.dataset.ratingSeller===String(farmerId))box.replaceWith(sellerRatingSummary(farmerId));
   }catch(error){if(!current())return;status.textContent=error.message;try{const saved=await api('/orders/'+encodeURIComponent(order.id)+'/seller-rating');if(current()&&Number.isInteger(saved.stars)&&saved.stars>=1&&saved.stars<=5){showSavedSellerRating(host,saved.stars);return;}}catch(_e){}if(current()){busy=false;save.disabled=false;buttons.forEach(b=>b.disabled=false);}}
  };
 }).catch(()=>{if(current())host.replaceChildren(node('p','Nie można pobrać oceny. Odśwież historię zakupów.'));});
 return host;
}
