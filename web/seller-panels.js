"use strict";
const sellerPanelIds=['farmer','farmer-details','point-location-panel','seller-compliance','user-photo-panel','address-delivery-panel','notifications-section','support-section'];
function resetSellerPanels(){
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
    }
    disclosure.open=id==='farmer';
  }
}
function revealSellerSection(id){
  const section=el(id);if(!section)return;
  const disclosure=section.querySelector(':scope > details[data-seller-panel]');if(disclosure)disclosure.open=true;
}
