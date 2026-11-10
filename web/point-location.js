// Seller chooses an address result or their current place; coordinates are an advanced option.
let pointLocationSerial = 0;
function pointLocationSnapshot() {
  return [pointEditorSerial, el('point-edit-select').value, el('point-edit-city').value, el('point-edit-street').value].join('|');
}
function setPointLocation(place) {
  el('point-edit-clear-coordinates').checked = false;
  el('point-edit-lat').disabled = false; el('point-edit-lon').disabled = false;
  el('point-edit-lat').value = coordinateText(place.latitude_e6);
  el('point-edit-lon').value = coordinateText(place.longitude_e6);
  el('point-edit-status').textContent = 'Wybrano miejsce punktu. Sprawdź adres i kliknij „Zapisz punkt”.';
}
el('point-find-address').onclick = () => act(async () => {
  const serial = ++pointLocationSerial, epoch = sessionEpoch, snapshot = pointLocationSnapshot();
  const current = () => serial === pointLocationSerial && epoch === sessionEpoch && role === 'rolnik' && snapshot === pointLocationSnapshot();
  const host = el('point-location-results'); host.replaceChildren();
  const city = el('point-edit-city').value.trim(), street = el('point-edit-street').value.trim();
  if (city.length < 2) { el('point-edit-status').textContent = 'Wpisz miejscowość i ulicę punktu.'; return; }
  el('point-edit-status').textContent = 'Szukam miejsca…';
  try {
    const cfg = await fetch('/address-search/config', {cache:'no-store'});
    const external = cfg.ok && (await cfg.json()).enabled === true;
    if (!current()) return;
    const response = await fetch(external ? '/address-search' : '/address-search/pickup-locations', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({city,street,postal_code:''}),cache:'no-store'});
    if (!response.ok) throw Error('Nie można wyszukać adresu');
    const data = await response.json(); if (!current()) return;
    for (const place of data.items) {
      const button = node('button', place.label); button.type = 'button';
      button.onclick = () => { if (current()) { setPointLocation(place); host.replaceChildren(); } };
      host.append(button);
    }
    el('point-edit-status').textContent = data.items.length ? 'Wybierz właściwe miejsce. Wynik może być orientacyjny.' :
      external ? 'Nie znaleziono adresu. Uzupełnij ulicę lub użyj bieżącej lokalizacji.' :
      'Brak zapisanego miejsca. Wyszukiwanie nowych adresów wymaga podłączonej usługi mapowej. Użyj bieżącej lokalizacji, gdy jesteś w punkcie.';
  } catch { if (current()) el('point-edit-status').textContent = 'Nie udało się wyszukać miejsca. Spróbuj ponownie lub użyj bieżącej lokalizacji.'; }
});
el('point-use-location').onclick = () => {
  const serial = ++pointLocationSerial, epoch = sessionEpoch, snapshot = pointLocationSnapshot();
  const current = () => serial === pointLocationSerial && epoch === sessionEpoch && role === 'rolnik' && snapshot === pointLocationSnapshot();
  el('point-edit-status').textContent = 'Oczekuję na lokalizację urządzenia. Pozwól przeglądarce na jej pobranie.';
  requestDeviceLocation(position => {
    if (!current()) return;
    setPointLocation({latitude_e6:Math.round(position.coords.latitude*1000000),longitude_e6:Math.round(position.coords.longitude*1000000)});
  }, message => { if (current()) el('point-edit-status').textContent = message; }, current);
};
for (const id of ['point-edit-city','point-edit-street']) el(id).addEventListener('input', () => {
  pointLocationSerial++; el('point-location-results').replaceChildren();
  el('point-edit-lat').value = ''; el('point-edit-lon').value = '';
  el('point-edit-status').textContent = 'Adres zmieniony. Wybierz lokalizację punktu ponownie.';
});
