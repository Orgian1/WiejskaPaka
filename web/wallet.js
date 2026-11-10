'use strict';
let walletVersion=0,walletBusy=false,walletReadSerial=0,walletAdminOffset=0,walletRecovering=false,walletActiveIntent=null;
function resetWalletView(){walletVersion++;walletReadSerial++;walletBusy=false;walletAdminOffset=0;walletRecovering=false;walletActiveIntent=null;const box=el('wallet-section');if(box){box.hidden=true;box.replaceChildren();}const link=el('wallet-nav-link');if(link)link.hidden=true;const admin=el('wallet-admin-section');if(admin){admin.hidden=true;admin.replaceChildren();}const adminLink=el('wallet-admin-nav-link');if(adminLink)adminLink.hidden=true;for(const id of ['wallet-dialog-topup','wallet-dialog-withdraw','wallet-dialog-pin']){const dialog=el(id);if(dialog){dialog.close();dialog.remove();}}}
function walletIntentKey(owner,kind){return 'wp-wallet-intent-v1:'+owner+':'+kind;}
function readWalletIntent(owner,kind){
 let raw;try{raw=sessionStorage.getItem(walletIntentKey(owner,kind));}catch(_e){throw Error('Nie można odczytać poprzedniej operacji. Włącz pamięć tej karty przeglądarki.');}
 if(raw===null)return null;
 let saved;try{saved=JSON.parse(raw);}catch(_e){throw Error('Nieprawidłowy zapis operacji. Sprawdź historię portfela.');}
 if(!saved||Array.isArray(saved)||!Number.isSafeInteger(saved.amount_grosze)||saved.amount_grosze<1||saved.amount_grosze>100000000||typeof saved.request_key!=='string'||!/^[A-Za-z0-9_-]{12,100}$/.test(saved.request_key))throw Error('Nieprawidłowy zapis operacji. Sprawdź historię portfela.');
 return {amount_grosze:saved.amount_grosze,request_key:saved.request_key};
}
function clearWalletIntent(owner,kind,requestKey){const saved=readWalletIntent(owner,kind);if(saved&&saved.request_key===requestKey)sessionStorage.removeItem(walletIntentKey(owner,kind));}
function walletIntent(owner,kind,amount){
 const previous=readWalletIntent(owner,kind);
 if(previous){if(previous.amount_grosze!==amount)throw Error('Najpierw sprawdź poprzednią operację przyciskiem poniżej.');return previous;}
 if(!crypto.randomUUID)throw Error('Przeglądarka nie obsługuje bezpiecznego identyfikatora operacji.');
 const intent={amount_grosze:amount,request_key:crypto.randomUUID()};
 try{sessionStorage.setItem(walletIntentKey(owner,kind),JSON.stringify(intent));}catch(_e){throw Error('Nie można bezpiecznie zapamiętać operacji. Włącz pamięć tej karty przeglądarki.');}return intent;
}
function renderWalletRecovery(box,owner,current){
 for(const kind of ['topup','withdraw']){
 let intent;try{intent=readWalletIntent(owner,kind);}catch(error){box.append(node('p',error.message));continue;}
 if(!intent)continue;
 const card=dashboardCard('Poprzednia operacja wymaga sprawdzenia',[kind==='topup'?'Doładowanie':'Wypłata',money(intent.amount_grosze),'Sprawdź zapis na serwerze. Niezapisane zgłoszenie zostanie wycofane, aby można było podać nową kwotę.']);
 card.setAttribute('data-wallet-recovery',kind);const button=node('button','Sprawdź poprzednią operację');button.type='button';button.onclick=()=>recoverWalletIntent(owner,kind,current,button,intent.request_key);card.append(button);box.append(card);
 }
}
async function recoverWalletIntent(owner,kind,current,button,expectedRequestKey=null){
 if(!current()||walletRecovering)return;
 let intent;try{intent=readWalletIntent(owner,kind);}catch(error){msg(error.message);return;}
 if(!intent){msg('Brak nierozstrzygniętej operacji.');return;}
 if(expectedRequestKey&&intent.request_key!==expectedRequestKey){msg('Zapis operacji zmienił się. Odświeżam widok.');try{await refreshWallet();}catch(_e){}return;}
 if(walletBusy&&(!walletActiveIntent||walletActiveIntent.owner!==owner||walletActiveIntent.kind!==kind||walletActiveIntent.request_key!==intent.request_key)){msg('Najpierw zakończ bieżącą operację.');return;}
 const epoch=sessionEpoch,sameAccount=()=>epoch===sessionEpoch&&owner===checkoutOwner&&!!token;
 walletRecovering=true;button.disabled=true;
 try{
 const result=await api('/wallet/operations/reconcile-test','POST',{...intent,kind:kind==='withdraw'?'withdrawal':'topup'});
 if(!current())return;
 if(!['committed','released'].includes(result.outcome))throw Error('Nie można potwierdzić stanu operacji. Spróbuj ponownie.');
 clearWalletIntent(owner,kind,intent.request_key);
 walletVersion++;walletBusy=false;walletActiveIntent=null;walletRecovering=false;
 for(const id of ['wallet-dialog-topup','wallet-dialog-withdraw','wallet-dialog-pin']){const dialog=el(id);if(dialog){dialog.close();dialog.remove();}}
 msg(result.outcome==='committed'?'Poprzednia operacja jest zapisana. Sprawdź historię portfela.':'Poprzednie zgłoszenie wycofano. Możesz podać nową kwotę.');
 await refreshWallet();
 }catch(error){if(sameAccount())msg(error.message);}
 finally{if(sameAccount()){walletRecovering=false;button.disabled=false;}}
}
function walletDialog(kind,title){const dialog=node('dialog');dialog.id='wallet-dialog-'+kind;const form=node('form');form.append(node('h2',title));const error=node('p');error.setAttribute('role','alert');const cancel=node('button','Anuluj');cancel.type='button';cancel.onclick=()=>dialog.close();const submit=node('button',kind==='pin'?'Zapisz PIN':kind==='topup'?'Doładuj':'Potwierdź wypłatę');submit.type='submit';const actions=node('div','','row');actions.append(cancel,submit);dialog.append(form);document.body.append(dialog);dialog.addEventListener('close',()=>{for(const input of form.querySelectorAll('input[type=password]'))input.value='';});return {dialog,form,error,actions,submit};}
function walletField(form,label,type='text'){const holder=node('label',label),input=node('input');input.type=type;input.required=true;input.autocomplete='off';holder.append(input);form.append(holder);return input;}
async function refreshWallet(){
 if(token&&role==='admin')return refreshWalletAdmin();
 const serial=++walletReadSerial,version=walletVersion,epoch=sessionEpoch,owner=checkoutOwner;const current=()=>version===walletVersion&&epoch===sessionEpoch&&owner===checkoutOwner&&!!token;
 if(!token||!['klient','rolnik'].includes(role))return;
 let data;try{data=await api('/wallet');}catch(_e){return;}if(!current()||serial!==walletReadSerial)return;
 if(!['available_grosze','reserved_grosze'].every(k=>Number.isSafeInteger(data[k])&&data[k]>=0)||!Array.isArray(data.entries))return;
 let box=el('wallet-section');if(!box){box=node('section');box.id='wallet-section';box.className='wide-section';el('tresc').append(box);}box.hidden=false;box.replaceChildren();
 let link=el('wallet-nav-link');if(!link){link=node('a','Portfel');link.id='wallet-nav-link';link.href='#wallet-section';document.querySelector('.quick-nav').append(link);}link.hidden=false;
 box.append(node('h2','Mój portfel'));const balances=node('div','','wallet-balances');balances.append(dashboardCard('Dostępne środki',[money(data.available_grosze)]),dashboardCard('Zarezerwowane środki',[money(data.reserved_grosze),'Środki oczekujące na wypłatę.']));box.append(balances);
 renderWalletRecovery(box,owner,current);
 const actions=node('div','','row');box.append(actions);
 const operation=(kind)=>{if(walletBusy||walletRecovering||!current())return;const old=el('wallet-dialog-'+kind);if(old){old.showModal();return;}const ui=walletDialog(kind,kind==='topup'?'Doładuj portfel':'Wypłać środki');try{ui.intentKey=readWalletIntent(owner,kind)?.request_key;}catch(_e){}
 const amount=walletField(ui.form,'Kwota (zł)');amount.inputMode='decimal';amount.maxLength=12;
 let quote=null;
 if(kind==='withdraw'){
 quote=node('p');quote.setAttribute('role','status');ui.form.append(quote);
 const updateQuote=()=>{try{const gross=parseGrosze(amount.value);if(!Number.isSafeInteger(gross)||gross<1||gross>100000000)throw Error();const rate=data.withdrawal_fee_basis_points;if(rate!==0&&rate!==500)throw Error();const fee=Math.floor((gross*rate+5000)/10000);quote.textContent='Rezerwacja: '+money(gross)+' · Prowizja '+(rate/100)+'%: '+money(fee)+' · Po potrąceniu: '+money(gross-fee)+'. Wniosek pozostaje oczekujący; przelew nie jest wykonywany.';}catch(_e){quote.textContent='Wpisz kwotę, aby zobaczyć prowizję i kwotę po potrąceniu.';}};
 amount.addEventListener('input',updateQuote);updateQuote();
 }
 let pin=null;if(kind==='withdraw'){pin=walletField(ui.form,'PIN portfela','password');pin.inputMode='numeric';pin.pattern='[0-9]{6}';pin.maxLength=6;}
 ui.form.append(ui.error,ui.actions);const recovery=node('button','Sprawdź poprzednią operację');recovery.type='button';recovery.onclick=()=>recoverWalletIntent(owner,kind,current,recovery,ui.intentKey);ui.form.append(recovery);ui.dialog.showModal();
 ui.form.onsubmit=e=>{e.preventDefault();if(walletBusy||walletRecovering||!current())return;act(async()=>{walletBusy=true;ui.submit.disabled=true;ui.error.textContent='';try{const value=parseGrosze(amount.value);if(!Number.isSafeInteger(value)||value<1||value>100000000)throw Error('Podaj kwotę od 0,01 zł do 1 000 000 zł.');const intent=walletIntent(owner,kind,value);ui.intentKey=intent.request_key;const payload={...intent};if(pin){payload.pin=pin.value;pin.value='';if(!/^[0-9]{6}$/.test(payload.pin))throw Error('Podaj 6-cyfrowy PIN portfela.');}walletActiveIntent={owner,kind,request_key:intent.request_key};const result=await api(kind==='topup'?'/wallet/topups':'/wallet/withdrawals','POST',payload);clearWalletIntent(owner,kind,intent.request_key);if(!current())return;ui.dialog.close();ui.dialog.remove();msg(kind==='topup'?'Portfel został doładowany.':result.state==='cancelled_test'?'Wniosek jest anulowany.':result.state==='completed_test'?'Symulacja wypłaty jest zakończona.':'Środki zostały zarezerwowane do wypłaty.');await refreshWallet();}catch(error){if(current())ui.error.textContent=error.message;}finally{if(current()){walletBusy=false;walletActiveIntent=null;ui.submit.disabled=false;}if(pin)pin.value='';}});};};
 const topup=node('button','Doładuj portfel'),withdraw=node('button','Wypłać środki'),pinButton=node('button',data.pin_configured?'Zmień PIN portfela':'Ustaw PIN portfela');topup.type=withdraw.type=pinButton.type='button';topup.onclick=()=>operation('topup');withdraw.onclick=()=>{if(!data.pin_configured){msg('Przed wypłatą ustaw PIN portfela.');pinButton.click();}else operation('withdraw');};
 pinButton.onclick=()=>{if(walletBusy||walletRecovering||!current())return;const old=el('wallet-dialog-pin');if(old){old.showModal();return;}const ui=walletDialog('pin','PIN portfela');ui.form.append(node('p','Wypłata wymaga osobnego PIN-u portfela. Doładowanie nie wymaga PIN-u.'));const password=walletField(ui.form,'Hasło konta','password'),pin=walletField(ui.form,'Nowy PIN portfela (6 cyfr)','password'),repeat=walletField(ui.form,'Powtórz PIN','password');password.autocomplete='current-password';for(const input of [pin,repeat]){input.inputMode='numeric';input.pattern='[0-9]{6}';input.maxLength=6;}ui.form.append(ui.error,ui.actions);ui.dialog.showModal();ui.form.onsubmit=e=>{e.preventDefault();if(walletBusy||walletRecovering||!current())return;act(async()=>{walletBusy=true;ui.submit.disabled=true;try{if(!/^[0-9]{6}$/.test(pin.value)||pin.value!==repeat.value)throw Error('Wpisz dwa identyczne PIN-y składające się z 6 cyfr.');const payload={password:password.value,pin:pin.value};password.value=pin.value=repeat.value='';await api('/wallet/pin','PUT',payload);if(!current())return;ui.dialog.close();ui.dialog.remove();msg('PIN portfela zapisany.');await refreshWallet();}catch(error){if(current())ui.error.textContent=error.message;}finally{password.value=pin.value=repeat.value='';if(current()){walletBusy=false;walletActiveIntent=null;ui.submit.disabled=false;}}});};};
 actions.append(topup,withdraw,pinButton);box.append(node('h3','Historia operacji'));if(!data.entries.length)box.append(node('p','Nie masz jeszcze żadnych operacji.'));for(const entry of data.entries){const details=entry.state==='cancelled_test'?['Anulowano bez pobrania prowizji.']:entry.withdrawal_preview?['Prowizja: '+money(entry.withdrawal_preview.fee_grosze),'Po potrąceniu: '+money(entry.withdrawal_preview.net_grosze)]:[];const status={pending:'Oczekuje na wypłatę',credited:'Zaksięgowano',cancelled_test:'Anulowano — środki ponownie dostępne',completed_test:'Symulacja wypłaty zakończona — bez przelewu'}[entry.state]||'Stan wymaga sprawdzenia';const card=dashboardCard(entry.kind==='topup'?'Doładowanie portfela':'Wypłata środków',[money(entry.amount_grosze),...details,status,new Date(entry.created_at*1000).toLocaleString('pl-PL')]);
 if(entry.kind==='withdrawal'&&entry.state==='pending'){
 const cancel=node('button','Anuluj wniosek wypłaty');cancel.type='button';cancel.onclick=()=>walletMutation('/wallet/withdrawals/'+encodeURIComponent(entry.id)+'/cancel-test',cancel,current,'Wniosek anulowany. Środki są ponownie dostępne.');card.append(cancel);
 }
 box.append(card);}
}
async function walletMutation(path,button,current,notice){
 if(walletBusy||walletRecovering||!current())return;walletBusy=true;button.disabled=true;
 try{await api(path,'POST',{});if(!current())return;msg(notice);await refreshWallet();}
 catch(error){if(current())msg(error.message);}
 finally{if(current()){walletBusy=false;button.disabled=false;}}
}
async function refreshWalletAdmin(){
 const serial=++walletReadSerial,version=walletVersion,epoch=sessionEpoch,owner=checkoutOwner;
 const current=()=>version===walletVersion&&epoch===sessionEpoch&&owner===checkoutOwner&&!!token&&role==='admin';
 let data;try{data=await api('/admin/wallet/withdrawals-test?limit=50&offset='+walletAdminOffset);}catch(_e){return;}
 if(!current()||serial!==walletReadSerial||!Array.isArray(data.items))return;
 let box=el('wallet-admin-section');if(!box){box=node('section');box.id='wallet-admin-section';box.className='wide-section';el('tresc').append(box);}box.hidden=false;box.replaceChildren();
 let link=el('wallet-admin-nav-link');if(!link){link=node('a','Wypłaty');link.id='wallet-admin-nav-link';link.href='#wallet-admin-section';document.querySelector('.quick-nav').append(link);}link.hidden=false;
 box.append(node('h2','Oczekujące wnioski wypłat'),node('p','Zakończenie symulacji rozlicza rezerwację. Nie wykonuje przelewu ani połączenia z bankiem.'));
 const refresh=node('button','Odśwież wnioski');refresh.type='button';refresh.onclick=()=>act(refreshWalletAdmin);box.append(refresh);
 if(!data.items.length)box.append(node('p','Brak oczekujących wniosków na tej stronie.'));
 for(const entry of data.items){
 const card=dashboardCard('Wniosek konta '+entry.user_id,[entry.owner_role==='rolnik'?'Sprzedawca':'Klient','Kwota rezerwacji: '+money(entry.gross_grosze),'Prowizja: '+money(entry.fee_grosze),'Po potrąceniu: '+money(entry.net_grosze)]);
 const complete=node('button','Zakończ symulację wypłaty (TEST)');complete.type='button';complete.onclick=()=>walletMutation('/admin/wallet/withdrawals/'+encodeURIComponent(entry.id)+'/complete-test',complete,current,'Symulacja wypłaty zakończona. Nie wykonano przelewu.');card.append(complete);box.append(card);
 }
 const pagination=node('div','','row'),previous=node('button','Poprzednia strona'),next=node('button','Następna strona');previous.type=next.type='button';previous.disabled=walletAdminOffset===0;next.disabled=data.items.length<50||walletAdminOffset>=10000;
 previous.onclick=()=>{walletAdminOffset=Math.max(0,walletAdminOffset-50);act(refreshWalletAdmin);};next.onclick=()=>{walletAdminOffset=Math.min(10000,walletAdminOffset+50);act(refreshWalletAdmin);};pagination.append(previous,next);box.append(pagination);
}
if(token)act(refreshWallet);
