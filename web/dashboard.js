"use strict";
// Panel nie przechowuje danych logowania; korzysta z tokenu tylko w pamięci.
function dashboardCard(title, lines) {
  const card=node('article','', 'card');card.append(node('h3',title));
  for(const line of lines)card.append(node('p',line));return card;
}
// Format authoritative integer-grosze totals without recalculating settlement rules.
function sellerPayoutSummaryLines(report){
  const amounts=['eligible_grosze','pending_grosze','paid_out_grosze','platform_commission_earned_grosze','platform_commission_paid_out_grosze'];
  const counters=['eligible_orders','paid_orders'];
  if(!report||![...amounts,...counters].every(key=>Number.isSafeInteger(report[key])&&report[key]>=0)||report.pending_grosze!==report.eligible_grosze||report.platform_commission_paid_out_grosze>report.platform_commission_earned_grosze)throw Error('Nieprawidłowy raport testowy.');
  const date=report.next_weekly_payout_date;
  if(typeof date!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(date)||Number.isNaN(Date.parse(date+'T00:00:00Z'))||new Date(date+'T00:00:00Z').toISOString().slice(0,10)!==date)throw Error('Nieprawidłowy termin podglądu.');
  const amount=value=>{const grosze=BigInt(value);return `${grosze/100n},${String(grosze%100n).padStart(2,'0')} zł`};
  const [year,month,day]=date.split('-');
  return [
    `Do testowej wypłaty: ${amount(report.eligible_grosze)} (pozycje zamówień: ${report.eligible_orders}).`,
    `Wypłacono w symulacji: ${amount(report.paid_out_grosze)} (pozycje zamówień: ${report.paid_orders}).`,
    `Prowizja naliczona od zakończonych pozycji: ${amount(report.platform_commission_earned_grosze)}.`,
    `Prowizja przypisana do testowych wypłat: ${amount(report.platform_commission_paid_out_grosze)}.`,
    `Kolejny termin podglądu tygodniowego: ${day}.${month}.${year}.`,
    'To wyłącznie symulacja. Nie wykonano przelewu ani nie uruchomiono automatycznych wypłat.'
  ];
}
function dashboardButton(label, action) {
  const b=node('button',label);b.type='button';b.onclick=()=>act(action);return b;
}
// Monthly totals come from the server; order counts here refer to product rows.
function adminFinanceSummaryLines(report,month){
  const keys=['eligible_order_count','products_grosze','delivery_grosze','gross_order_grosze','platform_commission_grosze','seller_due_grosze','payment_success_event_order_count','refund_event_order_count'];
  if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(month)||!report||report.month!==month||report.report_type!=='test_operational_snapshot_not_accounting'||!keys.every(key=>Number.isSafeInteger(report[key])&&report[key]>=0))throw Error('Nieprawidłowy raport miesięczny.');
  if(BigInt(report.products_grosze)+BigInt(report.delivery_grosze)!==BigInt(report.gross_order_grosze)||BigInt(report.platform_commission_grosze)+BigInt(report.seller_due_grosze)!==BigInt(report.gross_order_grosze))throw Error('Niespójne kwoty raportu miesięcznego.');
  const amount=value=>{const n=BigInt(value);return `${n/100n},${String(n%100n).padStart(2,'0')} zł`};
  return [
    `Miesiąc: ${month}. Zakończone pozycje zakwalifikowane do rozliczenia: ${report.eligible_order_count}.`,
    `Produkty: ${amount(report.products_grosze)}. Dostawa: ${amount(report.delivery_grosze)}. Razem: ${amount(report.gross_order_grosze)}.`,
    `Prowizja platformy: ${amount(report.platform_commission_grosze)}. Należności sprzedawców: ${amount(report.seller_due_grosze)}.`,
    `Pozycje z płatnością testową w miesiącu: ${report.payment_success_event_order_count}. Pozycje ze zwrotem testowym: ${report.refund_event_order_count}.`,
    'Raport operacyjny symulacji. Nie jest dokumentem księgowym ani potwierdzeniem przelewu. Zwroty i zmiana stanu mogą zmienić dane także po zakończeniu miesiąca.'
  ];
}
async function downloadAdminFinanceCsv(month,active){
  if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(month))throw Error('Wybierz prawidłowy miesiąc');
  const epoch=sessionEpoch;
  const current=()=>epoch===sessionEpoch&&role==='admin'&&!!token&&active();
  if(!current())return;
  try{
    const response=await fetch(`/test/admin/finance/monthly/${month}/export.csv`,{headers:{Authorization:`Bearer ${token}`},cache:'no-store'});
    if(!current())return;
    if(!response.ok)throw Error('Nie udało się pobrać testowego CSV. Spróbuj ponownie.');
    if(!(response.headers.get('Content-Type')||'').toLowerCase().startsWith('text/csv'))throw Error('Nieprawidłowy format raportu CSV.');
    const blob=await response.blob();
    if(!current())return;
    const url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download=`wiejskapaka-test-${month}.csv`;
    try{document.body.append(link);link.click()}finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),0)}
  }catch(error){if(!current())return;throw error}
}
// Explicit test-only settlement after receipt. Retry checks current persisted
// state before sending an event; an unknown response cannot create a second sale.
function farmerTestSettlementButton(orderId,active){
  const button=node('button','Przekaż pozycję do rozliczenia (TEST)');button.type='button';
  let eventId=null;
  button.onclick=()=>act(async()=>{
    if(button.disabled||!button.isConnected||!active()||role!=='rolnik')return;
    button.disabled=true;
    try{
      const current=await api(`/test/payments/${orderId}`);
      if(!active()||!button.isConnected||role!=='rolnik')return;
      if(current.state==='paid_test'){
        if(!eventId){if(!globalThis.crypto?.randomUUID)throw Error('Brak bezpiecznego identyfikatora operacji.');eventId=crypto.randomUUID()}
        await api(`/test/payments/${orderId}/events`,'POST',{event_id:eventId,event_type:'order_completed_test'});
      }else if(!['completed_test','paid_out_test'].includes(current.state))throw Error('Pozycja nie jest gotowa do testowego rozliczenia. Odśwież panel.');
      if(!active()||!button.isConnected||role!=='rolnik')return;
      msg('Pozycja uwzględniona w rozliczeniu testowym. Nie wykonano przelewu.');
      await loadDashboard();
    }finally{button.disabled=false}
  });
  return button;
}
// Szczegóły pobierane na żądanie, bez przechowywania danych przesyłki w przeglądarce.
function shipmentDetailsButton(shipmentId, card) {
  return dashboardButton('Pokaż szczegóły przesyłki', async()=>{
    const epoch=sessionEpoch,request=(card._shipmentDetailsRequest||0)+1;card._shipmentDetailsRequest=request;
    const details=await api(`/shipments/${encodeURIComponent(shipmentId)}/details`);
    if(epoch!==sessionEpoch||request!==card._shipmentDetailsRequest||!card.isConnected)return;
    const old=card.querySelector('[data-shipment-details]');if(old)old.remove();
    const area=node('section');area.dataset.shipmentDetails='true';
    area.append(node('h4','Produkty w przesyłce'));
    for(const item of details.items){
      area.append(dashboardCard(`Produkt #${item.product_id}`,[
        `Ilość: ${item.quantity}`,`Status: ${item.status}`,
        `Produkty: ${money(item.subtotal_grosze)}`,
        `Dostawa przypisana do pozycji: ${money(item.delivery_grosze)}`
      ]));
    }
    area.append(node('p',`Dostawa całej przesyłki: ${money(details.delivery_grosze)}; razem: ${money(details.total_grosze)}`));
    if(details.refund_test_grosze!==null && details.refund_test_grosze!==undefined){
      area.append(node('p',`Zarejestrowany zwrot testowy: ${money(details.refund_test_grosze)} (bez przelewu pieniędzy).`));
    }
    card.append(area);
  });
}
// Historia finansowa jest dostępna wyłącznie dla zalogowanego klienta.
// Każde otwarcie pobiera aktualne dane z API, bez trwałego zapisu tokenu i bez wstrzykiwania HTML.
function shipmentFinancialHistoryButton(shipmentId, card) {
  return dashboardButton('Historia płatności i zwrotów (TEST)', async()=>{
    const epoch=sessionEpoch,request=(card._financialHistoryRequest||0)+1;card._financialHistoryRequest=request;
    const data=await api(`/shipments/${encodeURIComponent(shipmentId)}/financial-history-test`);
    if(epoch!==sessionEpoch || role!=='klient')return;
    if(request!==card._financialHistoryRequest||!card.isConnected)return;
    const old=card.querySelector('[data-financial-history]');if(old)old.remove();
    const area=node('section');area.dataset.financialHistory='true';
    area.append(node('h4','Historia finansowa przesyłki (symulacja)'));
    area.append(node('p',`Produkty: ${money(data.products_grosze)}; dostawa całej przesyłki: ${money(data.delivery_grosze)}; razem: ${money(data.total_grosze)}.`));
    area.append(node('p',`Zwroty testowe: ${money(data.refund_grosze)}. Żadne pieniądze nie zostały przelane.`));
    if(!data.delivery_consistent)area.append(node('p','UWAGA: wykryto niezgodność kosztu dostawy. Skontaktuj się z obsługą.'));
    for(const entry of data.orders){
      const item=dashboardCard(`Pozycja zamówienia ${entry.order_id}`,[
        `Status: ${entry.status}`,`Płatność testowa: ${entry.payment_state_test}`,
        `Produkty: ${money(entry.products_grosze)}`,
        `Dostawa przypisana do pozycji: ${money(entry.delivery_grosze)}`,
        `Razem: ${money(entry.total_grosze)}`,
        `Zwrot testowy: ${money(entry.refund_grosze)}`]);
      if(entry.events && entry.events.length){
        const history=node('ul');
        for(const event of entry.events){
          const label=[event.created_at,event.event_type,event.previous_status,event.new_status].filter(Boolean).join(' — ');
          history.append(node('li',label));
        }
        item.append(history);
      }
      area.append(item);
    }
    card.append(area);
  });
}
let dashboardRequestId=0;
async function loadDashboard() {
  const requestId=++dashboardRequestId;
  const epoch=sessionEpoch;
  const active=()=>epoch===sessionEpoch && requestId===dashboardRequestId;
  const section=el('dashboard'), notifications=el('notifications-section');
  section.hidden=!role;notifications.hidden=!role;
  if(!role){clear('dashboard-content');clear('notifications-list');return;}
  const box=el('dashboard-content');box.replaceChildren();
  const titles={klient:'Panel klienta',rolnik:'Panel rolnika',dostawca:'Panel dostawcy',admin:'Panel administratora'};
  el('dashboard-title').textContent=titles[role]||'Mój panel';
  if(role==='klient'){
    const [orders, shipmentData]=await Promise.all([api('/orders/me'),api('/shipments/mine')]);
    if(!active())return;
    const shipments=shipmentData.shipments||[];
    box.append(dashboardCard('Moje przesyłki',[`Liczba przesyłek: ${shipments.length}`,'Koszt dostawy naliczany raz za przesyłkę.']));
    for(const shipment of shipments){const c=dashboardCard(`Przesyłka ${shipment.id}`,[`Produkty: ${shipment.item_count}`,`Realizacja: ${shipment.fulfillment}`,`Dostawa: ${money(shipment.delivery_grosze)}`,`Łącznie: ${money(shipment.total_grosze)}`]);c.append(shipmentDetailsButton(shipment.id,c));if(typeof purchaseRecordControls==='function')c.append(purchaseRecordControls('shipment',shipment.id,c));
      c.append(shipmentFinancialHistoryButton(shipment.id,c));
      if(typeof supportCreateButton==='function')c.append(supportCreateButton('shipment',shipment.id,c));
      if(typeof pinRecoveryControls==='function')c.append(pinRecoveryControls('shipment',shipment.id));
      // Dwie osobne ścieżki: bez płatności oraz z pełnym zwrotem testowym.
      // Nie uruchamiamy zwrotu automatycznie po błędzie zwykłego anulowania.
      c.append(dashboardButton('Anuluj nieopłaconą przesyłkę (test)',async()=>{
        if(!window.confirm('Anulować nieopłaconą przesyłkę i przywrócić produkty do sprzedaży?'))return;
        const result=await api(`/shipments/${encodeURIComponent(shipment.id)}/cancel-test`,'POST');
        if(!active())return;
        msg(`Anulowano ${result.cancelled_orders} pozycji. Nie wykonano zwrotu pieniędzy.`);
        await loadDashboard();
      }));
      c.append(dashboardButton('Anuluj opłaconą przesyłkę i zwróć kwotę (TEST)',async()=>{
        if(!window.confirm('UWAGA: to wyłącznie symulacja. Anulować CAŁĄ opłaconą przesyłkę i zarejestrować zwrot testowy?'))return;
        const result=await api(`/shipments/${encodeURIComponent(shipment.id)}/cancel-paid-test`,'POST');
        if(!active())return;
        const amount=money(result.refund_grosze);
        msg(result.already_processed
          ? `Przesyłka była już anulowana. Wcześniej zarejestrowany zwrot testowy: ${amount}.`
          : `Anulowano przesyłkę. Zarejestrowano zwrot testowy ${amount}. Nie przelano prawdziwych pieniędzy.`);
        await loadDashboard();
      }));
      box.append(c);}
    box.append(dashboardCard('Twoje zakupy',[`Liczba zamówień: ${orders.length}`,'Sprawdź towar przed przekazaniem PIN-u sprzedawcy lub dostawcy.']));
    for(const o of orders){const c=dashboardCard(`Zamówienie ${o.pickup_code}`,[`Status: ${o.status}`,`Razem: ${money(o.total_grosze)}`]);
      if(typeof supportCreateButton==='function')c.append(supportCreateButton('order',o.id,c));
      c.append(dashboardButton('Historia statusów',async()=>showOrderHistory(o.id,c)));
      if(role==='klient'&&typeof pinRecoveryControls==='function'&&!['odebrane','anulowane_testowo','nieudana_dostawa_testowo'].includes(o.status))c.append(pinRecoveryControls('order',o.id));
      if((role==='klient'||role==='rolnik')&&typeof purchaseRecordControls==='function')c.append(purchaseRecordControls('order',o.id,c));
      if(o.status==='oczekuje_na_platnosc_testowa'){
        c.append(dashboardButton('Anuluj opłacone zamówienie i zwróć kwotę (TEST)',async()=>{
          if(!window.confirm('To wyłącznie symulacja. Anulować opłacone zamówienie i zarejestrować pełny zwrot testowy?'))return;
          const result=await api(`/orders/${o.id}/cancel-paid-test`,'POST');
          if(!active())return;
          msg(`Zwrot wyłącznie testowy: ${money(result.refund_grosze)}. Nie przelano pieniędzy.`);
          await loadDashboard();await loadOrders();await loadProducts();
        }));
      }
      box.append(c);
    }
  }else if(role==='rolnik'){
    const farmerOrderCards=new Map();
    const [products,orders,shipmentData]=await Promise.all([api('/products/mine'),api('/orders/me'),api('/shipments/farmer/mine')]);
    if(!active())return;
    box.append(dashboardCard('Gospodarstwo',[`Produkty: ${products.length}`,`Zamówienia: ${orders.length}`]));
    for(const shipment of (shipmentData.shipments||[])){
      const c=dashboardCard(`Przesyłka ${shipment.id}`,[`Produkty: ${shipment.item_count}`,`Realizacja: ${shipment.fulfillment}`,`Dostawa: ${money(shipment.delivery_grosze)}`,`Łącznie: ${money(shipment.total_grosze)}`,`Status: ${shipment.status||'sprawdź zamówienia'}`]);
      if(shipment.fulfillment==='dostawa'){
        const courier=node('input');courier.type='number';courier.min='1';courier.placeholder='ID dostawcy';courier.setAttribute('aria-label','Identyfikator dostawcy przesyłki');
        c.append(courier,dashboardButton('Przypisz dostawcę całej przesyłce (test)',async()=>{
          const courier_id=Number(courier.value);if(!Number.isSafeInteger(courier_id)||courier_id<1)throw Error('Podaj prawidłowe ID dostawcy');
          await api(`/shipments/${encodeURIComponent(shipment.id)}/assign-courier-test`,'POST',{courier_id});if(!active())return;msg('Dostawca przypisany');await loadDashboard();
        }));
        c.append(dashboardButton('Wyślij całą przesyłkę (test)',async()=>{
          await api(`/shipments/${encodeURIComponent(shipment.id)}/dispatch-test`,'POST');if(!active())return;msg('Przesyłka w drodze');await loadDashboard();
        }));
        const reason=node('select');reason.setAttribute('aria-label','Przyczyna nieudanej dostawy');
        for(const [value,label] of [['dostawca_nie_przyjechal','Dostawca nie przyjechał'],['dostawca_nie_dostarczyl','Dostawca nie dostarczył']]){
          const option=node('option',label);option.value=value;reason.append(option);
        }
        c.append(reason,dashboardButton('Zgłoś nieudaną dostawę (zwrot testowy)',async()=>{
          if(!window.confirm('Potwierdzić nieudaną dostawę? Symulowany zwrot obejmie całą przesyłkę.'))return;
          const result=await api(`/shipments/${encodeURIComponent(shipment.id)}/courier-failure-test`,'POST',{reason:reason.value});
          if(!active())return;msg(`Zwrot wyłącznie testowy: ${money(result.refund_grosze)}. Nie przelano pieniędzy.`);await loadDashboard();
        }));
      }else{
        const pin=node('input');pin.type='text';pin.inputMode='numeric';pin.maxLength=6;pin.autocomplete='off';pin.placeholder='PIN klienta';
        const checked=node('input');checked.type='checkbox';const label=node('label','Klient sprawdził produkty');label.prepend(checked);
        c.append(pin,label,dashboardButton('Potwierdź odbiór przesyłki',async()=>{
          if(!/^\d{6}$/.test(pin.value)||!checked.checked)throw Error('Sprawdź PIN i potwierdzenie kontroli towaru');
          try{const result=await api(`/shipments/${encodeURIComponent(shipment.id)}/confirm`,'POST',{pin:pin.value,checked_goods:true});
            if(!active())return;if(result.confirmed){msg('Odebrano całą przesyłkę');await loadDashboard()}else msg(`Błędny PIN, pozostało prób: ${result.remaining_attempts}`);
          }finally{pin.value=''}
        }));
      }
      c.append(shipmentDetailsButton(shipment.id,c));if(typeof purchaseRecordControls==='function')c.append(purchaseRecordControls('shipment',shipment.id,c));
      box.append(c);
    }
    const inventory=node('section');inventory.setAttribute('aria-label','Stan produktów gospodarstwa');
    inventory.append(node('h3','Moje produkty i stany magazynowe'));
    if(!products.length)inventory.append(node('p','Nie dodano jeszcze produktów. Użyj formularza Dodaj produkt.'));
    for(const product of products){
      const stock=Number(product.stock);
      const availability=Number.isSafeInteger(stock)&&stock>=0?`${stock} ${saleUnitLabel(product)}`:'Stan niedostępny';
      inventory.append(dashboardCard(product.name,[`Dostępne: ${availability}`,`Cena: ${money(product.price_grosze)} / ${saleUnitLabel(product)}${packageLabel(product)}`,`Dostawa: ${money(product.delivery_grosze)}`]));
    }
    box.append(inventory);
    for(const o of orders){const c=dashboardCard(`Zamówienie ${o.pickup_code}`,[`Status: ${o.status}`,`Realizacja: ${o.fulfillment}`]);farmerOrderCards.set(o.id,{card:c,order:o});
      c.append(dashboardButton('Historia statusów',async()=>showOrderHistory(o.id,c)));
      if((role==='klient'||role==='rolnik')&&typeof purchaseRecordControls==='function')c.append(purchaseRecordControls('order',o.id,c));
      if(o.fulfillment==='dostawa' && o.status==='oczekuje_na_platnosc_testowa'){const dispatch=node('button','Oznacz jako wysłane (test)');dispatch.type='button';dispatch.onclick=()=>act(async()=>{if(dispatch.disabled)return;dispatch.disabled=true;try{await api(`/orders/${o.id}/dispatch-test`,'POST');if(!active())return;msg('Status zaktualizowany');await loadDashboard()}finally{dispatch.disabled=false}});c.append(dispatch)}
      if(o.fulfillment==='dostawa'){
        const id=node('input');id.type='number';id.min='1';id.placeholder='Identyfikator dostawcy';id.setAttribute('aria-label','Identyfikator dostawcy');
        const assign=node('button','Przypisz dostawcę (test)');assign.type='button';assign.onclick=()=>act(async()=>{if(assign.disabled)return;const courier_id=Number(id.value);if(!Number.isSafeInteger(courier_id)||courier_id<1)throw Error('Podaj prawidłowy identyfikator');assign.disabled=true;try{await api(`/orders/${o.id}/assign-courier-test`,'POST',{courier_id});if(!active())return;msg('Dostawca przypisany');await loadDashboard()}finally{assign.disabled=false}});c.append(id,assign);
      }
      box.append(c);
    }
    try{const report=await api('/test/farmers/me/payout-report');if(!active())return;box.append(dashboardCard('Rozliczenia testowe',sellerPayoutSummaryLines(report)));for(const row of (report.orders||[])){const entry=farmerOrderCards.get(row.order_id);if(entry&&entry.order.status==='odebrane'&&row.state==='paid_test')entry.card.append(farmerTestSettlementButton(row.order_id,active))}}catch(e){if(!active())return;box.append(node('p','Podgląd rozliczeń testowych jest niedostępny. Odśwież panel.','muted'))}
  }else if(role==='dostawca'){
    const [orders,shipmentData]=await Promise.all([api('/couriers/me/orders'),api('/couriers/me/shipments')]);
    if(!active())return;
    const shipments=shipmentData.shipments||[];
    box.append(dashboardCard('Moje dostawy',[`Przesyłki: ${shipments.length}`,`Zamówienia: ${orders.length}`]));
    for(const shipment of shipments){
      const c=dashboardCard(`Przesyłka ${shipment.shipment_id}`,[`Status: ${shipment.status}`,`Produkty: ${shipment.item_count}`,`Dostawa: ${money(shipment.delivery_grosze)}`,`Razem: ${money(shipment.total_grosze)}`]);
      if(shipment.status==='w_drodze_testowo'){
        const pin=node('input');pin.type='text';pin.inputMode='numeric';pin.autocomplete='off';pin.maxLength=6;pin.placeholder='PIN klienta';
        const checked=node('input');checked.type='checkbox';const label=node('label','Klient sprawdził wszystkie produkty');label.prepend(checked);
        const confirmButton=dashboardButton('Potwierdź całą przesyłkę PIN-em',async()=>{
          if(confirmButton.disabled)return;
          if(!/^\d{6}$/.test(pin.value))throw Error('PIN musi mieć 6 cyfr');
          if(!checked.checked)throw Error('Klient musi najpierw sprawdzić produkty');
          confirmButton.disabled=true;try{const result=await api(`/shipments/${encodeURIComponent(shipment.shipment_id)}/confirm`,'POST',{pin:pin.value,checked_goods:true});
            if(!active())return;if(result.confirmed){msg('Potwierdzono odbiór całej przesyłki');await loadDashboard()}
            else msg(`Błędny PIN; pozostało prób: ${result.remaining_attempts}`);
          }finally{pin.value='';confirmButton.disabled=false}
        });c.append(pin,label,confirmButton);
      }
      c.append(shipmentDetailsButton(shipment.shipment_id,c));
      box.append(c);
    }
    box.append(dashboardCard('Starsze zamówienia',['Zamówienia bez przesyłki obsługuj według dotychczasowego procesu.']));
    for(const o of orders){const c=dashboardCard(`Zamówienie ${o.pickup_code||o.id}`,[`Status: ${o.status}`]);
      c.append(dashboardButton('Historia statusów',async()=>showOrderHistory(o.id,c)));
      if((role==='klient'||role==='rolnik')&&typeof purchaseRecordControls==='function')c.append(purchaseRecordControls('order',o.id,c));box.append(c);
    }
  }else if(role==='admin'){
    box.append(dashboardCard('Administracja',['Operacje zbiorcze i raporty są dostępne wyłącznie w trybie testowym.']));
    // Rejestr administracyjny: filtrowanie, stronicowanie i kontrola sum bez danych osobowych.
    const register=node('section');register.setAttribute('aria-label','Rejestr przesyłek');
    const statusFilter=node('select');statusFilter.setAttribute('aria-label','Filtr statusu przesyłki');
    for(const [value,label] of [['','Wszystkie statusy'],['oczekuje_na_platnosc_testowa','Oczekujące'],['gotowe_do_odbioru_testowo','Gotowe do odbioru'],['w_drodze_testowo','W drodze'],['odebrane','Odebrane'],['anulowane_testowo','Anulowane'],['nieudana_dostawa_testowo','Nieudana dostawa']]){
      const option=node('option',label);option.value=value;statusFilter.append(option);
    }
    const pageSize=20;let offset=0;let registerRequestId=0;
    const results=node('div');
    const previous=dashboardButton('Poprzednia strona',async()=>{offset=Math.max(0,offset-pageSize);await loadRegister()});
    const next=dashboardButton('Następna strona',async()=>{offset+=pageSize;await loadRegister()});
    async function loadRegister(){
      const id=++registerRequestId;
      const params=new URLSearchParams({limit:String(pageSize),offset:String(offset)});
      if(statusFilter.value)params.set('status',statusFilter.value);
      const data=await api(`/admin/shipments/overview?${params.toString()}`);
      if(!active()||id!==registerRequestId||!register.isConnected)return;
      results.replaceChildren();
      results.append(node('p',`Przesyłki: ${data.total}; strona ${Math.floor(offset/pageSize)+1}`));
      if(!data.shipments.length)results.append(node('p','Brak przesyłek dla wybranego filtra.'));
      for(const shipment of data.shipments){
        results.append(dashboardCard(`Przesyłka ${shipment.shipment_id}`,[
          `Status: ${shipment.status}`,`Pozycji: ${shipment.order_count}`,
          `Produkty: ${money(shipment.products_grosze)}`,
          `Dostawa (jedna opłata): ${money(shipment.delivery_grosze)}`,
          `Razem: ${money(shipment.total_grosze)}`,
          `Zwrot symulowany: ${money(shipment.refund_test_grosze)}`]));
      }
      previous.disabled=offset===0;
      next.disabled=offset+pageSize>=data.total;
    }
    statusFilter.onchange=()=>act(async()=>{offset=0;await loadRegister()});
    register.append(node('h3','Rejestr przesyłek'),statusFilter,results,previous,next);
    box.append(register);
    await loadRegister();if(!active())return;
    // B/961: odczytowa kontrola spójności; bez automatycznego poprawiania danych.
    const reconciliation=node('section');reconciliation.setAttribute('aria-label','Kontrola spójności przesyłek');
    const reconciliationResults=node('div');
    const issuesOnly=node('input');issuesOnly.type='checkbox';issuesOnly.checked=true;
    const issuesLabel=node('label','Pokaż tylko wykryte problemy');issuesLabel.prepend(issuesOnly);
    const reconcilePageSize=30;let reconcileOffset=0;let reconcileRequestId=0;
    const reconcilePrevious=dashboardButton('Poprzednie wyniki',async()=>{reconcileOffset=Math.max(0,reconcileOffset-reconcilePageSize);await loadReconciliation()});
    const reconcileNext=dashboardButton('Następne wyniki',async()=>{reconcileOffset+=reconcilePageSize;await loadReconciliation()});
    async function loadReconciliation(){
      const id=++reconcileRequestId;
      const params=new URLSearchParams({limit:String(reconcilePageSize),offset:String(reconcileOffset),only_issues:String(issuesOnly.checked)});
      const data=await api(`/admin/shipments/reconciliation?${params}`);
      if(!active()||!reconciliation.isConnected||id!==reconcileRequestId)return;
      reconciliationResults.replaceChildren();
      reconciliationResults.append(node('p',`Znaleziono: ${data.total} przesyłek; raport tylko do odczytu.`));
      if(!data.shipments.length)reconciliationResults.append(node('p','Brak wyników na tej stronie.'));
      for(const shipment of data.shipments){
        const card=dashboardCard(`Kontrola przesyłki ${shipment.shipment_id}`,[
          `Pozycji: ${shipment.order_count}`,
          `Produkty: ${money(shipment.products_grosze)}`,
          `Dostawa: ${money(shipment.delivery_grosze)}`,
          `Razem: ${money(shipment.total_grosze)}`,
          `Zwroty testowe: ${money(shipment.refund_test_grosze)}`,
          `Problemy: ${shipment.issues.length?shipment.issues.join(', '):'brak'}`]);
        const auditResults=node('div');
        card.append(dashboardButton('Pokaż audyt i historię',async()=>{
          const auditId=(card._auditRequestId||0)+1;card._auditRequestId=auditId;
          const audit=await api(`/admin/shipments/${encodeURIComponent(shipment.shipment_id)}/audit`);
          if(!active()||!card.isConnected||card._auditRequestId!==auditId)return;
          auditResults.replaceChildren();
          auditResults.append(node('p',`Zgodność dostawy: ${audit.delivery_consistent?'tak':'NIE'}`));
          for(const item of audit.items){
            const itemBox=dashboardCard(`Zamówienie ${item.id}`,[
              `Status: ${item.status}`,`Kwota: ${money(item.total_grosze)}`,
              `Zwrot testowy: ${money(item.refund_test_grosze)}`]);
            for(const event of item.events)itemBox.append(node('p',`${event.created_at||''} — ${event.event_type||'zmiana'} (${event.previous_status||'—'} → ${event.new_status||'—'})`));
            auditResults.append(itemBox);
          }
        }),auditResults);
        reconciliationResults.append(card);
      }
      reconcilePrevious.disabled=reconcileOffset===0;
      reconcileNext.disabled=reconcileOffset+reconcilePageSize>=data.total;
    }
    issuesOnly.onchange=()=>act(async()=>{reconcileOffset=0;await loadReconciliation()});
    reconciliation.append(node('h3','Kontrola spójności i audyt'),issuesLabel,
      dashboardButton('Sprawdź przesyłki',async()=>{reconcileOffset=0;await loadReconciliation()}),
      reconciliationResults,reconcilePrevious,reconcileNext);
    box.append(reconciliation);
    await loadReconciliation();if(!active())return;
    const month=node('input');month.type='month';month.value=new Date().toISOString().slice(0,7);month.setAttribute('aria-label','Miesiąc raportu');
    let financeRequestId=0;
    month.onchange=()=>{financeRequestId++;box.querySelectorAll('[data-test-finance-report]').forEach(n=>n.remove())};
    box.append(month,dashboardButton('Pokaż raport finansowy (test)',async()=>{
      const selectedMonth=month.value;
      if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(selectedMonth))throw Error('Wybierz prawidłowy miesiąc');
      const financeId=++financeRequestId;
      const r=await api(`/test/admin/finance/monthly/${selectedMonth}`);
      if(!active()||!box.isConnected||financeId!==financeRequestId)return;
      if(month.value!==selectedMonth)return;
      const lines=adminFinanceSummaryLines(r,selectedMonth);
      box.querySelectorAll('[data-test-finance-report]').forEach(n=>n.remove());
      const report=dashboardCard('Raport testowy — dane symulacyjne',lines);
      report.dataset.testFinanceReport='true';
      const download=dashboardButton('Pobierz raport CSV (TEST)',async()=>{
        if(download.disabled)return;download.disabled=true;
        try{await downloadAdminFinanceCsv(selectedMonth,()=>active()&&box.isConnected&&report.isConnected&&financeId===financeRequestId&&month.value===selectedMonth)}finally{download.disabled=false}
      });
      report.append(download);
      box.append(report);
    }));
  }
  if(active())await loadNotifications();
}
// Każda karta przechowuje tylko najnowszą historię; starsze odpowiedzi są ignorowane.
async function showOrderHistory(id,container){
  const epoch=sessionEpoch;
  const requestId=(container._historyRequestId||0)+1;
  container._historyRequestId=requestId;
  const existing=container.querySelector('[data-order-history]');
  if(existing)existing.remove();
  const output=node('div');output.dataset.orderHistory='true';
  output.append(node('p','Wczytywanie historii…'));
  container.append(output);
  try{
    const events=await api(`/orders/${id}/events`);
    if(epoch!==sessionEpoch||!container.isConnected)return;
    if(container._historyRequestId!==requestId)return;
    output.replaceChildren();
    if(!events.length)output.append(node('p','Brak zapisanych zdarzeń'));
    for(const event of events)output.append(node('p',`${event.created_at||''} — ${event.event_type||event.status||'Zmiana'}`));
  }catch(error){
    if(epoch!==sessionEpoch||!container.isConnected)return;
    if(container._historyRequestId!==requestId)return;
    output.replaceChildren(node('p','Nie udało się pobrać historii. Spróbuj ponownie.'));
  }
}
let notificationsRequestId=0;
async function loadNotifications(){if(!role)return;const requestId=++notificationsRequestId;const epoch=sessionEpoch;const entries=await api('/notifications/me');if(epoch!==sessionEpoch||requestId!==notificationsRequestId)return;const box=el('notifications-list');box.replaceChildren();
  if(!entries.length)box.append(node('p','Brak powiadomień'));
  for(const n of entries){const c=dashboardCard(n.title,[n.body,n.created_at||'']);if(!n.read_at)c.append(dashboardButton('Oznacz jako przeczytane',async()=>{await api(`/notifications/${n.id}/read`,'POST');if(epoch!==sessionEpoch)return;await loadNotifications()}));box.append(c)}
}
el('dashboard-refresh').onclick=()=>act(loadDashboard);
el('notifications-refresh').onclick=()=>act(loadNotifications);
