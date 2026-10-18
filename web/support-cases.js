"use strict";
let supportGeneration=0,supportListRequest=0,supportDetailRequest=0,supportOffset=0,supportMore=false;
const supportStates={new:'Nowe',in_review:'W obsłudze',closed_test:'Zamknięte testowo'};
const supportCategories={product:'Produkt',pickup:'Odbiór w punkcie',delivery:'Dostawa',other:'Inny problem'};
function eraseSupportNode(host){
  for(const n of host.querySelectorAll('*')){if('value' in n)n.value='';n.textContent=''}
  host.replaceChildren();
}
function resetSupportView(user){
  supportGeneration++;supportListRequest++;supportDetailRequest++;supportOffset=0;supportMore=false;
  for(const host of document.querySelectorAll('[data-support-private]'))eraseSupportNode(host);
  el('support-status').textContent='';el('support-filter').value='';
  el('support-section').hidden=!['klient','rolnik','admin'].includes(user?.role);
  el('support-previous').disabled=true;el('support-next').disabled=true;
}
function supportActive(epoch,generation){return epoch===sessionEpoch&&generation===supportGeneration&&!!token&&['klient','rolnik','admin'].includes(role)}
function supportButton(label,action){const button=node('button',label);button.type='button';button.onclick=()=>act(action);return button}
function checkSupportData(data){
  if(data?.mode!=='test'||!data.case||!Object.hasOwn(supportStates,data.case.status)||!Number.isSafeInteger(data.case.revision)||data.case.revision<1||!Array.isArray(data.events)||data.events.length>20||typeof data.has_older_events!=='boolean')throw Error('Nieprawidłowa odpowiedź zgłoszenia.');
}
function supportRequestId(){if(!globalThis.crypto?.randomUUID)throw Error('Brak bezpiecznego identyfikatora zgłoszenia.');return crypto.randomUUID()}
function supportCreateButton(kind,id,card){
  return supportButton('Zgłoś problem z zakupem (TEST)',async()=>{
    if(role!=='klient'||!card.isConnected)return;
    const epoch=sessionEpoch,generation=supportGeneration;
    const old=card.querySelector('[data-support-private]');if(old){eraseSupportNode(old);old.remove()}
    const form=node('div');form.dataset.supportPrivate='true';
    const category=node('select');category.setAttribute('aria-label','Rodzaj problemu testowego');
    for(const [value,label] of Object.entries(supportCategories)){const option=node('option',label);option.value=value;category.append(option)}
    const text=node('textarea');text.minLength=10;text.maxLength=2000;text.setAttribute('aria-label','Opis problemu testowego');
    const status=node('p');status.setAttribute('role','status');
    let requestId=null,payloadSignature=null;
    const submit=supportButton('Wyślij zgłoszenie testowe',async()=>{
      if(submit.disabled||!form.isConnected||!supportActive(epoch,generation)||role!=='klient')return;
      const description=text.value.trim();if(description.length<10||description.length>2000){status.textContent='Wpisz od 10 do 2000 znaków.';return}
      const signature=JSON.stringify([category.value,description]);
      if(signature!==payloadSignature){requestId=supportRequestId();payloadSignature=signature}
      submit.disabled=true;category.disabled=true;text.disabled=true;
      try{
        const data=await api('/test/support/cases','POST',{kind,target_id:String(id),category:category.value,description,request_id:requestId});
        if(!supportActive(epoch,generation)||!form.isConnected)return;
        checkSupportData(data);text.value='';eraseSupportNode(form);
        form.append(node('p','Zgłoszenie testowe zapisane. Odpowiedzi znajdziesz w sekcji „Zgłoszenia problemów — TEST”. Nie wykonano zwrotu.'));
        supportOffset=0;
        await loadSupportCases();
      }catch(error){if(supportActive(epoch,generation)&&form.isConnected&&error.message!=='SESSION_CHANGED')status.textContent=error.message+' Po utracie odpowiedzi ponów bez zmieniania treści, aby uniknąć drugiego zgłoszenia.'}
      finally{submit.disabled=false;category.disabled=false;text.disabled=false}
    });
    form.append(node('p','Używaj fikcyjnych danych. Nie wpisuj PIN-u, hasła, telefonu ani danych dokumentów. Zgłoszenie nie anuluje zakupu i nie uruchamia zwrotu. Dla produktu w przesyłce sprawa dotyczy całej przesyłki.'),category,text,submit,status);card.append(form);text.focus();
  });
}
async function loadSupportCases(){
  const epoch=sessionEpoch,generation=supportGeneration,request=++supportListRequest,offset=supportOffset;
  if(!supportActive(epoch,generation))return;
  eraseSupportNode(el('support-list'));el('support-status').textContent='Pobieranie zgłoszeń…';
  el('support-previous').disabled=true;el('support-next').disabled=true;
  try{
    const query=new URLSearchParams({limit:'20',offset:String(offset)});if(el('support-filter').value)query.set('status',el('support-filter').value);
    const data=await api('/test/support/cases?'+query);
    if(!supportActive(epoch,generation)||request!==supportListRequest)return;
    if(data.mode!=='test'||!Array.isArray(data.cases)||data.cases.length>20||data.offset!==offset||data.limit!==20||typeof data.has_more!=='boolean')throw Error('Nieprawidłowa lista zgłoszeń.');
    supportMore=data.has_more;
    for(const item of data.cases){
      if(!Object.hasOwn(supportStates,item.status)||!Object.hasOwn(supportCategories,item.category)||typeof item.id!=='string'||!/^[a-f0-9]{32}$/.test(item.id))throw Error('Nieprawidłowe zgłoszenie.');
      const card=node('article','','card');card.append(node('h3',supportCategories[item.category]+' — '+supportStates[item.status]),node('p',(item.kind==='shipment'?'Przesyłka ':'Zamówienie ')+item.target_id),node('p','Aktualizacja: '+item.updated_at),supportButton('Otwórz zgłoszenie testowe',()=>loadSupportCase(item.id)));el('support-list').append(card);
    }
    el('support-status').textContent=data.cases.length?'Strona '+(Math.floor(offset/20)+1)+'. Zgłoszenia nie zmieniają rozliczeń.':'Brak zgłoszeń dla wybranego filtra.';
    el('support-previous').disabled=offset===0;el('support-next').disabled=!supportMore||offset+20>10000;
  }catch(error){if(supportActive(epoch,generation)&&request===supportListRequest&&error.message!=='SESSION_CHANGED'){eraseSupportNode(el('support-list'));el('support-status').textContent=error.message}}
}
function supportEventNode(event){
  const item=node('article','','card');
  item.append(node('p',`Wpis ${event.revision} — ${event.actor_role} — ${event.created_at}`),node('p',event.message||'Utworzono zgłoszenie testowe.'),node('p','Stan po wpisie: '+(supportStates[event.status_after]||'Nieznany')));return item;
}
async function loadSupportCase(id){
  const epoch=sessionEpoch,generation=supportGeneration,request=++supportDetailRequest;
  if(!supportActive(epoch,generation))return;
  const host=el('support-detail');eraseSupportNode(host);
  try{
    const data=await api('/test/support/cases/'+encodeURIComponent(id));
    if(!supportActive(epoch,generation)||request!==supportDetailRequest)return;
    checkSupportData(data);const item=data.case;
    host.append(node('h3','Szczegóły zgłoszenia — '+supportStates[item.status]),node('p',item.description),node('p',data.notice));
    const events=node('div');events.dataset.supportEvents='true';for(const event of data.events)events.append(supportEventNode(event));host.append(events);
    let before=data.events[0]?.revision;
    const older=supportButton('Pokaż wcześniejsze wpisy',async()=>{
      if(older.disabled||!before)return;older.disabled=true;
      try{
        const page=await api('/test/support/cases/'+encodeURIComponent(id)+'?before_revision='+before);
        if(!supportActive(epoch,generation)||request!==supportDetailRequest||!host.isConnected)return;
        checkSupportData(page);const nodes=page.events.map(supportEventNode);events.prepend(...nodes);before=page.events[0]?.revision;older.hidden=!page.has_older_events;
      }finally{older.disabled=false}
    });older.hidden=!data.has_older_events;host.append(older);
    const message=node('textarea');message.maxLength=2000;message.setAttribute('aria-label','Odpowiedź testowa do zgłoszenia');
    const state=node('select');state.setAttribute('aria-label','Nowy stan zgłoszenia testowego');
    for(const [value,label] of [['','Bez zmiany stanu'],['in_review','W obsłudze / otwórz ponownie'],['closed_test','Zamknij testowo']]){const option=node('option',label);option.value=value;state.append(option)}
    state.hidden=role!=='admin';const feedback=node('p');feedback.setAttribute('role','status');
    let replyId=null,signature=null;
    const save=supportButton('Zapisz odpowiedź testową',async()=>{
      if(save.disabled||!supportActive(epoch,generation)||request!==supportDetailRequest||!host.isConnected)return;
      const text=message.value.trim();if(!text||text.length>2000){feedback.textContent='Wpisz odpowiedź od 1 do 2000 znaków.';return}
      const body={message:text,expected_revision:item.revision};if(role==='admin'&&state.value)body.status=state.value;
      const currentSignature=JSON.stringify(body);if(currentSignature!==signature){replyId=supportRequestId();signature=currentSignature}body.request_id=replyId;
      save.disabled=true;message.disabled=true;state.disabled=true;
      try{
        await api('/test/support/cases/'+encodeURIComponent(id)+'/replies','POST',body);
        if(!supportActive(epoch,generation)||request!==supportDetailRequest)return;
        message.value='';await loadSupportCase(id);await loadSupportCases();
      }catch(error){if(supportActive(epoch,generation)&&request===supportDetailRequest&&error.message!=='SESSION_CHANGED')feedback.textContent=error.message+' Odśwież historię, jeśli zgłoszenie zmieniło się. Po utracie odpowiedzi ponów bez zmiany treści.'}
      finally{save.disabled=false;message.disabled=false;state.disabled=false}
    });
    host.append(supportButton('Odśwież historię zgłoszenia',()=>loadSupportCase(id)));
    if(item.status!=='closed_test'||role==='admin')host.append(node('p','Odpowiedź widzą kupujący, sprzedawca i administrator. Nie wpisuj danych wrażliwych.'),message,state,save,feedback);
  }catch(error){if(supportActive(epoch,generation)&&request===supportDetailRequest&&error.message!=='SESSION_CHANGED'){eraseSupportNode(host);host.append(node('p',error.message))}}
}
el('support-refresh').onclick=()=>act(loadSupportCases);
el('support-filter').onchange=()=>{supportOffset=0;return act(loadSupportCases)};
el('support-previous').onclick=()=>{supportOffset=Math.max(0,supportOffset-20);return act(loadSupportCases)};
el('support-next').onclick=()=>{if(!supportMore||supportOffset+20>10000)return;supportOffset+=20;return act(loadSupportCases)};
resetSupportView(role&&token?{role}:null);
