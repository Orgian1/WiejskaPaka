"use strict";
function sellerPointOrder(points){
  let saved=[];
  try{saved=JSON.parse(localStorage.getItem('wp-point-order:'+checkoutOwner)||'[]');if(!Array.isArray(saved))saved=[]}catch(_e){}
  const rank=new Map(saved.map((id,i)=>[id,i]));
  return [...points].sort((a,b)=>(rank.get(a.id)??saved.length)-(rank.get(b.id)??saved.length)||a.id-b.id);
}
function updateSellerNavigation(points){
  const menu=el('seller-point-menu');menu.replaceChildren();
  if(role!=='rolnik'){el('seller-point-nav').hidden=true;return}
  el('seller-point-nav').hidden=false;
  const ordered=sellerPointOrder(points.filter(p=>p.active));
  const add=node('a','Dodaj punkt');add.href='#point-form';add.onclick=event=>{event.preventDefault();if(typeof revealSellerSection==='function')revealSellerSection('farmer-details');el('point-form').scrollIntoView();el('point-name').focus()};menu.append(add);
  const list=node('ol');
  const epoch=sessionEpoch,owner=checkoutOwner;
  for(let index=0;index<ordered.length;index++){
    const point=ordered[index],item=node('li',`${point.name} — ${point.city}, ${point.street}`);
    for(const [delta,label] of [[-1,'Przesuń wyżej'],[1,'Przesuń niżej']]){
      const button=node('button',label);button.type='button';button.setAttribute('aria-label',label+': '+point.name);
      button.disabled=index+delta<0||index+delta>=ordered.length;
      button.onclick=()=>{
        if(epoch!==sessionEpoch||owner!==checkoutOwner)return;
        const next=[...ordered];[next[index],next[index+delta]]=[next[index+delta],next[index]];
        try{localStorage.setItem('wp-point-order:'+owner,JSON.stringify(next.map(p=>p.id)))}catch(_e){msg('Nie można zapisać kolejności punktów w tej przeglądarce.');return}
        updateSellerNavigation(points);
      };item.append(button);
    }
    list.append(item);
  }
  menu.append(list,node('p','Kolejność jest zapisywana dla tego konta w tej przeglądarce. Nawigacja otworzy Mapy Google i przekaże adresy wybranych punktów.'));
  // Google Maps supports up to three waypoints on mobile browsers. Split
  // longer routes without dropping points or inventing travel times.
  const address=p=>`${p.street}, ${p.city}, Polska`;
  for(let start=0;start<ordered.length;start+=4){
    const batch=ordered.slice(start,start+4),params=new URLSearchParams({api:'1',travelmode:'driving',destination:address(batch.at(-1))});
    if(start)params.set('origin',address(ordered[start-1]));
    if(batch.length>1)params.set('waypoints',batch.slice(0,-1).map(address).join('|'));
    const link=node('a',start===0?'Przejdź do nawigacji':`Nawigacja — kolejne punkty ${start+1}–${start+batch.length}`);
    link.href='https://www.google.com/maps/dir/?'+params.toString();link.target='_blank';link.rel='noopener noreferrer';menu.append(link);
  }
  if(!ordered.length)menu.append(node('p','Dodaj aktywny punkt, aby rozpocząć nawigację.'));
}
