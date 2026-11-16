'use strict';
let contactDemoEnabled=false,contactDemoVersion=0,contactDemoAbort=null,contactAdminRequest=0;
function resetContactDemo(){
 contactDemoVersion++;contactAdminRequest++;contactDemoAbort?.abort();contactDemoAbort=null;
 const form=document.getElementById('contact-form');if(form)form.reset();
 for(const id of ['contact-demo-admin','contact-demo-admin-link'])document.getElementById(id)?.remove();
 const status=document.getElementById('contact-status');if(status&&contactDemoEnabled)status.textContent='Tryb demo: wiadomość trafi do testowej skrzynki administratora. E-mail nie jest wysyłany.';
}
async function refreshContactDemoAdmin(offset=0){
 if(!contactDemoEnabled||typeof role==='undefined'||role!=='admin'||!token)return;
 const epoch=sessionEpoch,request=++contactAdminRequest;
 let data;try{data=await api('/test/admin/contact/messages?offset='+offset+'&limit=20');if(data.mode!=='local_test'||!Array.isArray(data.items)||data.items.length>20||!Number.isSafeInteger(data.total)||typeof data.has_more!=='boolean')throw Error('Nieprawidłowa odpowiedź skrzynki testowej.');}catch(error){if(epoch===sessionEpoch&&request===contactAdminRequest&&error.message!=='SESSION_CHANGED')msg(error.message);return;}
 if(epoch!==sessionEpoch||request!==contactAdminRequest||role!=='admin')return;
 let box=el('contact-demo-admin');if(!box){box=node('section');box.id='contact-demo-admin';box.className='wide-section';el('tresc').append(box);}
 box.replaceChildren(node('h2','Kontakt — skrzynka testowa'),node('p','Wiadomości z formularza Kontakt / Zgłoś problem. Tryb demo, bez wysyłania e-maili.'),node('p','Liczba wiadomości: '+data.total));
 if(!el('contact-demo-admin-link')){const link=node('a','Kontakt (TEST)');link.id='contact-demo-admin-link';link.href='#contact-demo-admin';document.querySelector('.quick-nav').append(link);}
 const refresh=node('button','Odśwież skrzynkę testową');refresh.type='button';refresh.onclick=()=>refreshContactDemoAdmin(offset);box.append(refresh);
 for(const item of data.items){const card=node('article','','card');card.append(node('h3',item.subject),node('p',item.topic==='problem'?'Zgłoś problem':'Kontakt'),node('p',item.email),node('p',item.created_at),node('p',item.message),node('p','Numer: '+item.id));box.append(card);}
 if(!data.items.length)box.append(node('p','Skrzynka testowa jest pusta.'));
 const pages=node('div','','row'),previous=node('button','Poprzednie wiadomości'),next=node('button','Następne wiadomości');previous.type=next.type='button';previous.disabled=offset===0;next.disabled=!data.has_more;previous.onclick=()=>refreshContactDemoAdmin(Math.max(0,offset-20));next.onclick=()=>refreshContactDemoAdmin(offset+20);pages.append(previous,next);box.append(pages);
}
(() => {
 const form=document.getElementById('contact-form'),topic=document.getElementById('contact-topic'),status=document.getElementById('contact-status'),button=document.getElementById('contact-submit');
 if(!form||!topic||!status)return;
 let key='',signature='',busy=false;
 form.addEventListener('reset',()=>{key='';signature='';});
 for(const link of document.querySelectorAll('[data-contact-topic]'))link.addEventListener('click',()=>{topic.value=link.dataset.contactTopic==='problem'?'problem':'contact';document.getElementById('contact-heading').focus({preventScroll:true});});
 form.addEventListener('submit',async event=>{
  event.preventDefault();
  if(!contactDemoEnabled||!button){status.textContent='Wysyłka wiadomości nie jest jeszcze uruchomiona. Wiadomość nie została wysłana.';return;}
  if(busy)return;
  const fields={topic:topic.value,email:document.getElementById('contact-email').value.trim(),subject:document.getElementById('contact-subject').value.trim(),message:document.getElementById('contact-message').value.trim()};
  const fresh=JSON.stringify(fields);if(fresh!==signature||!key){signature=fresh;key=crypto.randomUUID();}
  const version=contactDemoVersion,controls=[...form.querySelectorAll('input,select,textarea,button')];busy=true;controls.forEach(control=>control.disabled=true);status.textContent='Zapisywanie wiadomości testowej…';
  contactDemoAbort=new AbortController();const abort=contactDemoAbort,timer=setTimeout(()=>abort.abort(),8000);
  try{
   const response=await fetch('/test/contact/messages',{method:'POST',headers:{'Content-Type':'application/json'},cache:'no-store',body:JSON.stringify({...fields,request_key:key}),signal:abort.signal});
   const data=await response.json();if(version!==contactDemoVersion)return;
   if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Sprawdź adres e-mail, temat (3–160 znaków) i wiadomość (10–4000 znaków).');
   if(data.mode!=='local_test'||data.stored!==true||typeof data.id!=='string')throw Error('Nieprawidłowe potwierdzenie zapisu.');
   form.reset();topic.value=fields.topic;key='';signature='';status.textContent='Wiadomość zapisana w skrzynce testowej administratora. Numer: '+data.id;
  }catch(error){if(version===contactDemoVersion)status.textContent=(error.name==='AbortError'?'Nie otrzymano potwierdzenia. Ponów wysłanie, aby sprawdzić zapis tej samej wiadomości.':error.message)+' E-mail nie został wysłany.';}
  finally{clearTimeout(timer);if(contactDemoAbort===abort)contactDemoAbort=null;busy=false;controls.forEach(control=>control.disabled=false);button.disabled=!contactDemoEnabled;}
 });
 if(button)(async()=>{try{
  const response=await fetch('/test/contact/options',{cache:'no-store'});if(!response.ok)return;const config=await response.json();contactDemoEnabled=config.enabled===true&&config.mode==='local_test';button.disabled=!contactDemoEnabled;
  if(contactDemoEnabled){button.textContent='Wyślij wiadomość (TEST)';status.textContent='Tryb demo: wiadomość trafi do testowej skrzynki administratora. E-mail nie jest wysyłany.';document.getElementById('contact-subject').minLength=3;document.getElementById('contact-message').minLength=10;void refreshContactDemoAdmin();}
 }catch(_e){/* Keep the form disabled when the optional demo mailbox is unavailable. */}})();
})();
