// Private on-demand purchase records. No PIN, client address or account storage.
function purchaseRecordControls(kind,id,container){
  const controls=node('div');
  for(const [download,label] of [[false,'Pierwotne warunki zakupu (TEST)'],[true,'Pobierz zapis zakupu (JSON)']]){
    const button=node('button',label);button.type='button';
    button.onclick=()=>act(async()=>{
      if(button.disabled)return;
      button.disabled=true;
      try{await showPurchaseRecord(kind,id,container,download)}finally{button.disabled=false;}
    });
    controls.append(button);
  }
  return controls;
}
function appendOriginalTerms(host,original,{location=true}={}){
  host.append(node('p',`${original.product.name} • ${original.quantity} ${saleUnitLabel(original.product)} × ${money(original.product.unit_price_grosze)} / ${saleUnitLabel(original.product)}${packageLabel(original.product)}`),
    node('p',`Produkty: ${money(original.subtotal_grosze)}; dostawa przypisana do pozycji: ${money(original.delivery_grosze)}; razem: ${money(original.total_grosze)}.`),
    node('p',`Warunki z dnia: ${original.ordered_at}; termin rezerwacji bez płatności: ${original.reservation_expires_at}`));
  if(location&&original.pickup_point){const point=original.pickup_point;
    host.append(node('p',`Punkt przy zakupie: ${point.name} — ${point.city}, ${point.street}; ${point.opening_hours}`));
  }
}
async function showPurchaseRecord(kind,id,container,download=false){
  if(!['order','shipment'].includes(kind))throw Error('Nieprawidłowy rodzaj zapisu.');
  const epoch=sessionEpoch,actorRole=role;
  if(!['klient','rolnik'].includes(actorRole))return;
  const request=(container._purchaseRecordRequest||0)+1;container._purchaseRecordRequest=request;
  const active=()=>epoch===sessionEpoch&&actorRole===role&&request===container._purchaseRecordRequest&&container.isConnected;
  try{
    const data=await api(`/${kind==='order'?'orders':'shipments'}/${encodeURIComponent(id)}/purchase-record`);
    if(!active())return;
    if(download){
      const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
      const url=URL.createObjectURL(blob),link=document.createElement('a');
      link.href=url;link.download='WiejskaPaka_zapis_'+kind+'_'+String(id).replace(/[^A-Za-z0-9_-]/g,'_')+'.json';
      try{document.body.append(link);link.click();}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),0);}
      return;
    }
    const old=container.querySelector('[data-purchase-record]');if(old)old.remove();
    const area=node('section');area.dataset.purchaseRecord='true';
    area.append(node('h4','Pierwotne warunki zakupu — zapis testowy'),node('p',data.notice));
    if(kind==='order'){
      if(data.original_available)appendOriginalTerms(area,data.original);
      else area.append(node('p','Brak archiwalnego zapisu produktu i punktu. Bieżący katalog nie zastępuje danych pierwotnego zakupu.'));
      area.append(node('p',`Bieżący status: ${data.current.status}; płatność testowa: ${data.current.payment_state_test}; zwrot testowy: ${money(data.current.refund_grosze)}.`));
    }else{
      if(data.original_available)area.append(node('p',`Produkty całej przesyłki: ${money(data.original.products_grosze)}; jedna dostawa: ${money(data.original.delivery_grosze)}; razem: ${money(data.original.total_grosze)}.`));
      else area.append(node('p','Nie wszystkie pozycje mają zapis pierwotnych warunków. Nie odtwarzamy brakującej historii z katalogu.'));
      let locationShown=false;
      for(const entry of data.orders){
        const item=node('article','', 'card');item.append(node('h5',`Pozycja ${entry.pickup_code}`));
        if(entry.original_available){appendOriginalTerms(item,entry.original,{location:!locationShown});if(entry.original.pickup_point)locationShown=true;}
        else item.append(node('p','Brak zapisu pierwotnych warunków tej pozycji.'));
        item.append(node('p',`Bieżący status: ${entry.current.status}; zwrot testowy: ${money(entry.current.refund_grosze)}.`));area.append(item);
      }
    }
    container.append(area);
  }catch(error){
    if(!active()||error.message==='SESSION_CHANGED')return;
    const old=container.querySelector('[data-purchase-record]');if(old)old.remove();
    const area=node('p','Nie udało się pobrać zapisu zakupu. Spróbuj ponownie.');area.dataset.purchaseRecord='true';container.append(area);
  }
}
