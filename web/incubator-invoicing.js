'use strict';

function incubatorInvoicingTab(active) {
  const path = '/admin/incubator-invoicing';
  const panel = node('details', '', 'wide-section');
  panel.dataset.testid = 'incubator-invoicing';
  panel.hidden = true;
  panel.append(node('summary', 'Fakturowanie – Twój StartUp'));
  const epoch = sessionEpoch;
  const current = () => epoch === sessionEpoch && role === 'admin' && panel.isConnected && active();
  const labels = {withdrawal_fee: 'Prowizje od wypłat', pickup_point: 'Punkty odbioru', advertising: 'Reklamy', refund: 'Zwroty i korekty'};
  const statuses = {pending: 'Do wystawienia', issued: 'Wystawione', closed: 'Zamknięte bez faktury'};
  const localDate = new Intl.DateTimeFormat('sv-SE', {timeZone: 'Europe/Warsaw'}).format(new Date());
  const formatGrosze = (value) => {
    const n = BigInt(value);
    const amount = n < 0n ? -n : n;
    return `${n < 0n ? '-' : ''}${amount / 100n},${String(amount % 100n).padStart(2, '0')} zł`;
  };
  const field = (parent, title, name, type = 'text', required = true) => {
    const label = node('label', title);
    const input = node('input');
    Object.assign(input, {name, type, required, autocomplete: 'off'});
    if (type === 'text' || type === 'search') input.maxLength = 240;
    if (type === 'number') Object.assign(input, {step: '1', min: '1', max: '9000000000000'});
    label.append(input);
    parent.append(label);
    return input;
  };
  const select = (parent, title, name, options) => {
    const label = node('label', title);
    const input = node('select');
    input.name = name;
    input.setAttribute('aria-label', title);
    for (const [value, text] of options) {
      const option = node('option', text);
      option.value = value;
      input.append(option);
    }
    label.append(input);
    parent.append(label);
    return input;
  };
  const submit = (form, title, handler) => {
    const button = node('button', title);
    button.type = 'submit';
    form.append(button);
    form.onsubmit = (event) => {
      event.preventDefault();
      if (!current() || button.disabled) return;
      button.disabled = true;
      void act(async () => {
        try { await handler(new FormData(form)); }
        finally { button.disabled = false; }
      });
    };
  };

  panel.append(node('p', 'Faktury wystawiaj w CRM Twój StartUp. Tutaj zapisujesz potwierdzone wpływy na subkonto i numery wystawionych dokumentów.'));
  const filters = node('form');
  const month = field(filters, 'Miesiąc (puste pole pokazuje wszystkie pozycje)', 'month', 'month', false);
  month.value = localDate.slice(0, 7);
  const status = select(filters, 'Status', 'status', [...Object.entries(statuses), ['', 'Wszystkie']]);
  const kind = select(filters, 'Rodzaj usługi', 'kind', [['', 'Wszystkie'], ...Object.entries(labels)]);
  const search = field(filters, 'Szukaj po nabywcy, fakturze lub identyfikatorze', 'search', 'search', false);
  const mode = select(filters, 'Dane', 'mode', [['test', 'Symulacja']]);
  const report = node('p');
  report.setAttribute('role', 'status');
  const rows = node('div');
  let offset = 0;
  let generation = 0;

  function params() {
    return new URLSearchParams(Object.entries({
      month: month.value, status: status.value, kind: kind.value, search: search.value, mode: mode.value
    }).filter(([,value]) => value));
  }

  function paymentFields(form, refund) {
    field(form, refund ? 'Numer zwrotu' : 'Numer transakcji', 'transaction_id');
    field(form, 'Identyfikator rozliczenia operatora', 'operator_settlement_id');
    field(form, refund ? 'Data zwrotu' : 'Data transakcji', 'transaction_on', 'date').max = localDate;
    const settled = field(form, refund ? 'Data rozliczenia zwrotu' : 'Data wpływu na subkonto', 'settled_on', 'date');
    settled.value = localDate;
    settled.max = localDate;
    field(form, refund ? 'Kwota zwrotu (w groszach)' : 'Kwota dla platformy (w groszach)', 'amount_grosze', 'number');
    field(form, 'Potwierdzam dane rozliczenia', 'confirmed', 'checkbox');
  }

  function paymentPayload(data) {
    return {
      mode: mode.value, transaction_id: data.get('transaction_id'),
      operator_settlement_id: data.get('operator_settlement_id'), transaction_on: data.get('transaction_on'),
      settled_on: data.get('settled_on'), amount_grosze: Number(data.get('amount_grosze')),
      confirmed: data.has('confirmed')
    };
  }

  const recording = node('details');
  recording.append(node('summary', 'Zapisz wpływ dla platformy'));
  const credit = node('form');
  const service = select(credit, 'Rodzaj usługi', 'kind', Object.entries(labels).filter(([key]) => key !== 'refund'));
  field(credit, 'Nabywca', 'buyer_name');
  field(credit, 'Adres nabywcy', 'buyer_address');
  const nip = field(credit, 'NIP (gdy wymagany)', 'buyer_nip', 'text', false);
  Object.assign(nip, {inputMode: 'numeric', pattern: '[0-9]{10}', maxLength: 10});
  const seller = field(credit, 'ID konta sprzedawcy (do zestawienia)', 'seller_id', 'number', false);
  seller.max = '9007199254740991';
  paymentFields(credit, false);
  const gross = field(credit, 'Cała kwota wypłaty sprzedawcy (w groszach)', 'withdrawal_gross_grosze', 'number', false);
  const updateCreditFields = () => {
    gross.required = mode.value === 'verified' && service.value === 'withdrawal_fee';
    gross.parentElement.hidden = !gross.required;
    gross.disabled = !gross.required;
    seller.required = gross.required;
  };
  service.onchange = updateCreditFields;
  submit(credit, 'Zapisz wpływ', async (data) => {
    const payload = paymentPayload(data);
    Object.assign(payload, {kind: data.get('kind'), buyer_name: data.get('buyer_name'),
      buyer_address: data.get('buyer_address'), buyer_nip: data.get('buyer_nip') || null});
    if (data.get('seller_id')) payload.seller_id = Number(data.get('seller_id'));
    if (data.get('withdrawal_gross_grosze')) payload.withdrawal_gross_grosze = Number(data.get('withdrawal_gross_grosze'));
    await api(path, 'POST', payload);
    if (!current()) return;
    credit.reset();
    credit.elements.settled_on.value = localDate;
    updateCreditFields();
    await load();
  });
  recording.append(credit);

  function render(item) {
    const lines = [
      statuses[item.status],
      `Nabywca: ${item.buyer_name} • ${item.buyer_address}${item.buyer_nip ? ' • NIP ' + item.buyer_nip : ''}`,
      `Transakcja ${item.transaction_id} • ${item.transaction_on}`,
      `Rozliczenie ${item.operator_settlement_id} • ${item.settled_on}`,
      `Kwota do faktury: ${formatGrosze(item.invoice_grosze)}`
    ];
    if (item.seller_id) lines.push(`ID sprzedawcy: ${item.seller_id}`);
    if (item.original_invoice_number) lines.push(`Faktura korygowana: ${item.original_invoice_number}`);
    if (item.invoice_number) lines.push(`Wystawiono: ${item.invoice_number} • ${item.issued_on}`);
    const card = dashboardCard(item.service, lines);
    if (item.status === 'pending') {
      card.append(dashboardButton('Kopiuj dane do CRM', async () => {
        if (!current()) return;
        const text = [item.mode === 'test' ? 'SYMULACJA' : '', item.service, ...lines.slice(1)].filter(Boolean).join('\n');
        if (navigator.clipboard) {
          try { await navigator.clipboard.writeText(text); if (current()) msg('Skopiowano dane.'); return; }
          catch { if (!current()) return; }
        }
        const label = node('label', 'Dane do skopiowania');
        const copy = node('textarea');
        copy.readOnly = true;
        copy.value = text;
        label.append(copy);
        card.append(label);
        copy.select();
      }));
      const issue = node('form');
      field(issue, 'Numer wystawionej faktury', 'invoice_number');
      const issued = field(issue, 'Data wystawienia', 'issued_on', 'date');
      issued.value = localDate;
      issued.max = localDate;
      submit(issue, 'Oznacz jako wystawioną', async (data) => {
        await api(`${path}/${item.id}/issue`, 'POST', {invoice_number: data.get('invoice_number'),
          issued_on: data.get('issued_on'), expected_grosze: item.invoice_grosze});
        if (current()) await load();
      });
      card.append(issue);
    }
    if (item.kind !== 'refund' && item.refunded_grosze < item.amount_grosze) {
      const refund = node('details');
      refund.append(node('summary', 'Zapisz zwrot lub anulowanie rozliczonego wpływu'));
      const form = node('form');
      paymentFields(form, true);
      submit(form, 'Zapisz zwrot', async (data) => {
        await api(`${path}/${item.id}/refund`, 'POST', {...paymentPayload(data), mode: item.mode});
        if (current()) await load();
      });
      refund.append(form);
      card.append(refund);
    }
    return card;
  }

  async function load() {
    const id = ++generation;
    const query = params();
    query.set('offset', offset);
    const data = await api(`${path}?${query}`);
    if (!current() || id !== generation) return;
    const totals = data.summary;
    report.textContent = `${month.value || localDate.slice(0, 7)} • wpływy po zwrotach: ${formatGrosze(totals.revenue_grosze)} • prowizje po zwrotach: ${formatGrosze(totals.commission_grosze)} • faktury: ${totals.issued} • pozostały darmowy limit: ${totals.free_remaining} • szacowany koszt: ${formatGrosze(totals.extra_cost_grosze)}`;
    rows.replaceChildren(...data.items.map(render));
    if (!data.items.length) rows.append(node('p', 'Brak pozycji dla wybranego filtra.'));
    previous.disabled = offset === 0;
    next.disabled = !data.more;
  }

  const previous = dashboardButton('Poprzednie wyniki', async () => { offset = Math.max(0, offset - 50); await load(); });
  const next = dashboardButton('Następne wyniki', async () => { offset += 50; await load(); });
  previous.disabled = next.disabled = true;
  const sellerRows = node('div');
  submit(filters, 'Szukaj', async () => { offset = 0; sellerRows.replaceChildren(); await load(); });
  mode.onchange = () => {
    updateCreditFields();
    rows.replaceChildren();
    sellerRows.replaceChildren();
    offset = 0;
    void act(load);
  };
  const exportButton = dashboardButton('Eksportuj CSV', async () => {
    const response = await fetch(`${path}/export.csv?${params()}`, {
      headers: {Authorization: `Bearer ${token}`}, cache: 'no-store'
    });
    if (!current()) return;
    if (!response.ok) throw Error('Eksport nie powiódł się. Sprawdź filtry.');
    const blob = await response.blob();
    if (!current()) return;
    const link = node('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = 'wiejskapaka-twoj-startup.csv';
    try { document.body.append(link); link.click(); }
    finally { link.remove(); setTimeout(() => URL.revokeObjectURL(url), 0); }
  });
  const sellerSummary = dashboardButton('Pokaż miesięczne zestawienie sprzedawców', async () => {
    const period = month.value || localDate.slice(0, 7);
    const selectedMode = mode.value;
    const result = await api(`${path}/seller-summary?${new URLSearchParams({month: period, mode: selectedMode})}`);
    if (!current() || selectedMode !== mode.value || period !== (month.value || localDate.slice(0, 7))) return;
    sellerRows.replaceChildren(node('h3', `Zestawienie sprzedawców • ${period}`));
    for (const item of result.items) sellerRows.append(node('p',
      `Sprzedawca ${item.seller_id} • ${labels[item.kind === 'seller_withdrawal_fee' ? 'withdrawal_fee' : item.kind]} • ${formatGrosze(item.amount_grosze)} • pozycje: ${item.transactions}`));
    if (!result.items.length) sellerRows.append(node('p', 'Brak wpływów powiązanych z kontami sprzedawców.'));
  });
  panel.append(recording, filters, exportButton, report, rows, previous, next, sellerSummary, sellerRows);
  panel.ontoggle = () => { if (panel.open && current()) void act(load); };
  updateCreditFields();
  void api(path + '/config').then((config) => {
    if (!current() || !config.enabled) return;
    if (config.verified_enabled) {
      const option = node('option', 'Potwierdzone wpływy na subkonto');
      option.value = 'verified';
      mode.append(option);
    }
    panel.hidden = false;
  }).catch(() => {});
  return panel;
}
