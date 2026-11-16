'use strict';
let walletAdGeneration=0,walletAdPending=false,walletAdTimer=null,walletAdAbort=null;
function resetWalletAds(){walletAdGeneration++;walletAdPending=false;clearInterval(walletAdTimer);walletAdAbort?.abort();walletAdAbort=null;const dialog=el('wallet-ad-dialog');if(dialog){dialog.close();dialog.remove();}const admin=el('wallet-ads-admin');if(admin)admin.remove();const link=el('wallet-ads-admin-link');if(link)link.remove();}
async function enterWalletWithAd(event){
 event.preventDefault();if(walletAdPending||!token||!['klient','rolnik'].includes(role))return;
 walletAdPending=true;const generation=++walletAdGeneration,epoch=sessionEpoch,owner=checkoutOwner,bearer=token;
 const current=()=>generation===walletAdGeneration&&epoch===sessionEpoch&&owner===checkoutOwner&&bearer===token;
 const openWallet=()=>{if(!current())return;walletAdPending=false;clearInterval(walletAdTimer);const dialog=el('wallet-ad-dialog');if(dialog){dialog.close();dialog.remove();}const box=el('wallet-section');if(box){box.hidden=false;box.scrollIntoView({block:'start'});const title=box.querySelector('h2');if(title){title.tabIndex=-1;title.focus({preventScroll:true});}}history.replaceState(null,'','#wallet-section');act(refreshWallet);};
 const dialog=node('dialog');dialog.id='wallet-ad-dialog';dialog.className='wallet-ad-dialog';dialog.setAttribute('aria-label','Reklama przed otwarciem portfela');
 const label=node('p','Sprawdzanie reklamy…');label.setAttribute('role','status');dialog.append(label);dialog.addEventListener('cancel',e=>e.preventDefault());document.body.append(dialog);dialog.showModal();
 walletAdAbort=new AbortController();const timeout=setTimeout(()=>walletAdAbort?.abort(),2000);
 let ad;
 try{const response=await fetch('/wallet/ads/claim',{method:'POST',headers:{Authorization:'Bearer '+bearer,'Content-Type':'application/json'},body:JSON.stringify({request_key:crypto.randomUUID()}),signal:walletAdAbort.signal,cache:'no-store'});if(!response.ok)throw Error();ad=(await response.json()).ad;}catch(_e){openWallet();return;}finally{clearTimeout(timeout);}
 if(!current())return;
 if(!ad){openWallet();return;}
 // Server only returns sanitized same-response JPEG data, never third-party pixels.
 if(typeof ad.image!=='string'||!ad.image.startsWith('data:image/jpeg;base64,')||!/^https?:\/\//.test(ad.url)){openWallet();return;}
 dialog.replaceChildren();const heading=node('div','','wallet-ad-heading'),badge=node('strong','Reklama'),count=node('span','5'),close=node('button','×');
 count.setAttribute('role','timer');count.setAttribute('aria-live','polite');close.type='button';close.disabled=true;close.setAttribute('aria-label','Zamknij reklamę');heading.append(badge,count,close);
 const link=node('a');link.href=ad.url;link.target='_blank';link.rel='noopener noreferrer sponsored';link.referrerPolicy='no-referrer';link.setAttribute('aria-label','Strona reklamodawcy: '+ad.advertiser);
 const image=node('img');image.alt=ad.advertiser;image.src=ad.image;link.append(image);dialog.append(heading,link,node('p',ad.advertiser));
 image.onerror=openWallet;link.addEventListener('click',()=>{if(!current())return;fetch('/wallet/ads/impressions/'+encodeURIComponent(ad.impression_id)+'/click',{method:'POST',headers:{Authorization:'Bearer '+bearer},keepalive:true}).catch(()=>{});});
 const started=performance.now();close.onclick=()=>{if(performance.now()-started>=5000)openWallet();};
 clearInterval(walletAdTimer);walletAdTimer=setInterval(()=>{if(!current()){clearInterval(walletAdTimer);return;}const remaining=Math.max(0,Math.ceil((5000-(performance.now()-started))/1000));count.textContent=String(remaining);if(remaining===0){clearInterval(walletAdTimer);close.disabled=false;openWallet();}},50);
}
document.addEventListener('click',event=>{if(event.target.closest('#wallet-nav-link'))enterWalletWithAd(event);});
function walletAdInput(form,label,type,value=''){const holder=node('label',label),input=node('input');input.type=type;input.value=value;holder.append(input);form.append(holder);return input;}
async function refreshWalletAdsAdmin(offset=0){
 if(!token||role!=='admin')return;const epoch=sessionEpoch,bearer=token;let data;try{data=await api('/admin/wallet-ads?limit=10&offset='+offset);}catch(_e){return;}if(epoch!==sessionEpoch||bearer!==token||role!=='admin')return;
 let section=el('wallet-ads-admin');if(!section){section=node('section');section.id='wallet-ads-admin';section.className='wide-section';el('tresc').append(section);}section.replaceChildren(node('h2','Reklamy portfela'),node('p','Rotacja reklam według kolejności, osobno dla każdego konta. Maksymalnie jedna emisja na 30 minut. Statystyki nie zawierają danych użytkowników.'));
 if(!el('wallet-ads-admin-link')){const link=node('a','Reklamy portfela');link.id='wallet-ads-admin-link';link.href='#wallet-ads-admin';document.querySelector('.quick-nav').append(link);}
 const fresh=node('button','Dodaj reklamę');fresh.type='button';fresh.onclick=()=>edit({});section.append(fresh);
 function edit(ad){
 const existing=el('wallet-ad-editor');if(existing)existing.remove();const form=node('form');form.id='wallet-ad-editor';
 const name=walletAdInput(form,'Nazwa reklamodawcy','text',ad.advertiser||'');name.maxLength=120;name.required=true;
 const url=walletAdInput(form,'Link HTTP lub HTTPS','url',ad.url||'');url.required=true;url.maxLength=2048;
 const file=walletAdInput(form,'Zdjęcie JPEG, PNG lub WebP (maks. 1 MB)','file');file.accept='image/jpeg,image/png,image/webp';file.required=!ad.id;
 const local=value=>{const date=new Date(value*1000);return new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16);};
 const start=walletAdInput(form,'Początek emisji (czas lokalny)','datetime-local',local(ad.starts_at||Date.now()/1000));start.required=true;
 const end=walletAdInput(form,'Koniec emisji (czas lokalny)','datetime-local',local(ad.ends_at||Date.now()/1000+86400));end.required=true;
 const order=walletAdInput(form,'Kolejność rotacji','number',String(ad.sort_order||0));order.min=0;order.max=100000;order.required=true;
 const enabled=walletAdInput(form,'Włącz emisję','checkbox');enabled.checked=!!ad.enabled;
 const save=node('button','Zapisz reklamę'),cancel=node('button','Anuluj'),error=node('p');error.setAttribute('role','alert');save.type='submit';cancel.type='button';cancel.onclick=()=>form.remove();form.append(save,cancel,error);section.prepend(form);
 form.onsubmit=async event=>{event.preventDefault();save.disabled=true;try{let image;const selected=file.files[0];if(selected){if(selected.size>1000000)throw Error('Zdjęcie może mieć najwyżej 1 MB.');image=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(selected);});}if(epoch!==sessionEpoch||bearer!==token)return;await api('/admin/wallet-ads'+(ad.id?'/'+ad.id:''),ad.id?'PUT':'POST',{advertiser:name.value,url:url.value,image_base64:image,starts_at:new Date(start.value).toISOString(),ends_at:new Date(end.value).toISOString(),enabled:enabled.checked,sort_order:Number(order.value)});await refreshWalletAdsAdmin();}catch(e){if(epoch===sessionEpoch&&bearer===token)error.textContent=e.message||'Nie można zapisać reklamy.';}finally{save.disabled=false;}};
 }
 const pages=node('div','','row'),previous=node('button','Poprzednie reklamy'),next=node('button','Następne reklamy');previous.type=next.type='button';previous.disabled=offset===0;next.disabled=data.items.length<10||offset>=100000;previous.onclick=()=>act(()=>refreshWalletAdsAdmin(Math.max(0,offset-10)));next.onclick=()=>act(()=>refreshWalletAdsAdmin(offset+10));pages.append(previous,next);section.append(pages);
 for(const ad of data.items){const card=dashboardCard(ad.advertiser,['Emisje: '+ad.impressions,'Kliknięcia: '+ad.clicks,ad.enabled?'Włączona':'Wyłączona','Kolejność: '+ad.sort_order,new Date(ad.starts_at*1000).toLocaleString('pl-PL')+' – '+new Date(ad.ends_at*1000).toLocaleString('pl-PL')]);const image=node('img');image.className='wallet-ad-preview';image.src=ad.image;image.alt=ad.advertiser;const editButton=node('button','Edytuj'),remove=node('button','Usuń');editButton.type=remove.type='button';editButton.onclick=()=>edit(ad);remove.onclick=()=>act(async()=>{if(epoch!==sessionEpoch||bearer!==token)return;await api('/admin/wallet-ads/'+ad.id,'DELETE');await refreshWalletAdsAdmin();});card.append(image,editButton,remove);section.append(card);}
}
if(token&&role==='admin')act(refreshWalletAdsAdmin);
