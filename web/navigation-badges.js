"use strict";
function setNavigationCount(id,count,label){
  const badge=el(id);if(!badge)return;
  const value=Number.isSafeInteger(count)&&count>0?count:0;
  badge.textContent=value?String(value):'';badge.hidden=value===0;
  badge.setAttribute('aria-label',label+': '+value);
}
let navigationCountRequest=0,navigationCountTimer=null,navigationCountRefresh=null;
function invalidateNavigationCounts(){navigationCountRequest++}
function resetNavigationBadges(user){
  invalidateNavigationCounts();clearInterval(navigationCountTimer);clearTimeout(navigationCountRefresh);
  if(user&&['klient','rolnik'].includes(user.role)){navigationCountTimer=setInterval(scheduleNavigationCounts,30000);scheduleNavigationCounts();}
  setNavigationCount('favorites-count',0,'Ulubione produkty');
  setNavigationCount('cart-count',0,'Pozycje koszyka');
  setNavigationCount('orders-count',0,'Aktualne zamówienia');
}
function updateSellerOrderCount(orders){
  setNavigationCount('orders-count',role==='rolnik'?orders.filter(o=>['oczekuje_na_platnosc_testowa','gotowe_do_odbioru_testowo','w_drodze_testowo'].includes(o.status)).length:0,'Aktualne zamówienia');
}

function scheduleNavigationCounts(){
  clearTimeout(navigationCountRefresh);
  navigationCountRefresh=setTimeout(()=>{
    if(!token||!['klient','rolnik'].includes(role)||document.visibilityState==='hidden')return;
    const epoch=sessionEpoch,request=++navigationCountRequest;
    api('/account/navigation-counts').then(data=>{
      if(epoch!==sessionEpoch||request!==navigationCountRequest)return;
      if(!['favorites_count','cart_count','current_orders_count'].every(k=>Number.isSafeInteger(data[k])&&data[k]>=0))return;
      setNavigationCount('favorites-count',data.favorites_count,'Ulubione produkty');
      setNavigationCount('cart-count',role==='klient'?data.cart_count:0,'Pozycje koszyka');
      setNavigationCount('orders-count',role==='rolnik'?data.current_orders_count:0,'Aktualne zamówienia');
    }).catch(()=>{}); // Keep the last confirmed count during a connection failure.
  },150);
}
globalThis.addEventListener('focus',scheduleNavigationCounts);
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')scheduleNavigationCounts()});
