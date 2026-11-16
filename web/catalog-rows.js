"use strict";
// Keep the actual form nodes (and their handlers) below the selected grid row.
// Native summary controls remain keyboard-operable, with one open offer at a time.
let catalogRowSelection=null,catalogRowWidth=0;
function resetCatalogRows(){catalogRowSelection=null;}
function catalogColumns(){
  const value=getComputedStyle(el('products')).gridTemplateColumns;
  return Math.max(1,value.split(/\s+/).filter(Boolean).length);
}
function positionCatalogDetails(){
  const card=catalogRowSelection;
  if(!card||!card.isConnected||!card.open){catalogRowSelection=null;return}
  const host=el('products'),body=card._catalogBody;
  const cards=[...host.children].filter(n=>n.classList.contains('catalog-product'));
  const index=cards.indexOf(card);if(index<0)return;
  const cols=catalogColumns(),last=Math.min(cards.length-1,Math.floor(index/cols)*cols+cols-1);
  // A spanning panel must follow the last product in the corresponding row.
  if(cards[last].nextElementSibling!==body)cards[last].after(body);
  body.hidden=false;
}
function prepareCatalogCard(card,product){
  const summary=card.querySelector('summary'),body=node('div','', 'catalog-row-details');
  body.id='catalog-details-'+product.id;body.hidden=true;body.dataset.productId=String(product.id);
  summary.id='catalog-summary-'+product.id;summary.setAttribute('aria-controls',body.id);
  body.setAttribute('role','region');body.setAttribute('aria-labelledby',summary.id);
  // Price/availability are useful before the buying controls are expanded.
  const preview=card.querySelector(':scope > p');if(preview)summary.append(preview);
  while(card.children.length>1)body.append(card.children[1]);
  card.append(body);card._catalogBody=body;
  card.addEventListener('toggle',()=>{
    summary.setAttribute('aria-expanded',String(card.open));
    if(!card.isConnected)return;
    if(card.open){
      const old=catalogRowSelection;
      if(old&&old!==card){old.open=false;expandedCatalogProducts.delete(Number(old.dataset.productId));old._catalogBody.hidden=true;old.append(old._catalogBody)}
      catalogRowSelection=card;expandedCatalogProducts.clear();expandedCatalogProducts.add(product.id);
      positionCatalogDetails();
    }else{
      expandedCatalogProducts.delete(product.id);body.hidden=true;card.append(body);
      if(catalogRowSelection===card)catalogRowSelection=null;
    }
  });
  card.dataset.productId=String(product.id);summary.setAttribute('aria-expanded',String(card.open));
}
function finishCatalogRows(){
  catalogRowSelection=null;
  for(const card of el('products').querySelectorAll(':scope > .catalog-product[open]')){
    if(catalogRowSelection){card.open=false;expandedCatalogProducts.delete(Number(card.dataset.productId))}
    else catalogRowSelection=card;
  }
  positionCatalogDetails();
}
if(typeof ResizeObserver!=='undefined')new ResizeObserver(entries=>{
  const width=entries[0].contentRect.width;if(Math.abs(width-catalogRowWidth)<1)return;
  catalogRowWidth=width;requestAnimationFrame(positionCatalogDetails);
}).observe(el('products'));
