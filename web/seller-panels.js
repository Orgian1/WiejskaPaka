"use strict";
const sellerPanelIds=['farmer','farmer-details','point-location-panel','seller-compliance','user-photo-panel','address-delivery-panel','notifications-section','dashboard','wallet-section','favorites-section'];
let sellerPanelState=new Map();
function ensureSellerPanels(reset=false){
  if(typeof appRoutesReady!=='undefined'&&appRoutesReady)return;
  for(const id of sellerPanelIds){
    const section=el(id);if(!section)continue;
    let disclosure=section.querySelector(':scope > details[data-seller-panel]');
    if(role!=='rolnik'){
      if(disclosure){const heading=disclosure.querySelector('summary').firstElementChild;section.prepend(heading);while(disclosure.children.length>1)section.append(disclosure.children[1]);disclosure.remove()}
      continue;
    }
    if(!disclosure){
      const heading=section.querySelector(':scope > h2');if(!heading)continue;
      disclosure=node('details');disclosure.dataset.sellerPanel=id;
      const summary=node('summary');summary.append(heading);disclosure.append(summary);
      while(section.firstChild)disclosure.append(section.firstChild);
      section.append(disclosure);
      disclosure.open=sellerPanelState.get(id)??(id==='farmer');
      disclosure.addEventListener('toggle',()=>{if(disclosure.isConnected&&role==='rolnik')sellerPanelState.set(id,disclosure.open)});
    }
    if(reset)disclosure.open=id==='farmer';
  }
}
function resetSellerPanels(){sellerPanelState=new Map();ensureSellerPanels(true);}
function revealSellerSection(id){
  const section=el(id);if(!section)return;
  if(typeof navigateApp==='function'){const route=appRouteAliases[id];if(route)navigateApp(route)}const disclosure=section.querySelector(':scope > details[data-seller-panel]');if(disclosure)disclosure.open=true;
}
document.addEventListener('click',event=>{
  if(event.defaultPrevented)return;
  const link=event.target.closest('a[href^="#"]');if(link)revealSellerSection(link.getAttribute('href').slice(1));
});
