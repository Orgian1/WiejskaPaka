// Device-local preferences, scoped to BOTH account id and email (demo ids can repeat).
let marketOwner = null, marketPreferences = {favorites: [], location: null}, favoritesSerial = 0;
function readMarketPreferences(key) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw || raw.length > 12000) return {favorites: [], location: null};
    const data = JSON.parse(raw);
    const favorites = Array.isArray(data.favorites) ? [...new Set(data.favorites.filter(id => Number.isSafeInteger(id) && id > 0))].slice(0, 200) : [];
    const p = data.location;
    const location = p && Number.isSafeInteger(p.lat) && Math.abs(p.lat) <= 90000000 &&
      Number.isSafeInteger(p.lon) && Math.abs(p.lon) <= 180000000 && [100,500,1000,5000].includes(p.radius) ?
      {lat:p.lat, lon:p.lon, radius:p.radius} : null;
    return {favorites, location};
  } catch { return {favorites: [], location: null}; }
}
function saveMarketPreferences() {
  if (!marketOwner) return;
  try { localStorage.setItem(marketOwner, JSON.stringify(marketPreferences)); }
  catch { msg('Przeglądarka blokuje zapis ustawień. Zmiany działają do wylogowania.'); }
}
function rememberNearbyLocation(payload) {
  if (!marketOwner) return;
  marketPreferences.location = {lat:payload.latitude_e6, lon:payload.longitude_e6, radius:payload.radius_m};
  saveMarketPreferences();
}
function forgetNearbyLocation() {
  marketPreferences.location = null; saveMarketPreferences();
}
function refreshMarketPreferences(user) {
  favoritesSerial++;
  marketOwner = user && Number.isSafeInteger(user.id) && typeof user.email === 'string' ?
    'wp-market-v1:' + user.id + ':' + encodeURIComponent(user.email) : null;
  marketPreferences = marketOwner ? readMarketPreferences(marketOwner) : {favorites: [], location:null};
  el('favorites-list').replaceChildren();
  el('favorites-status').textContent = marketOwner ? 'Zapisane na tym urządzeniu dla Twojego konta.' : 'Zaloguj się, aby zapisywać ulubione produkty.';
  const p = marketPreferences.location;
  if (p) {
    el('nearby-lat').value = coordinateText(p.lat); el('nearby-lon').value = coordinateText(p.lon);
    el('nearby-radius').value = String(p.radius);
    el('nearby-status').textContent = 'Przywrócono zapamiętaną lokalizację. Kliknij „Blisko mnie”, aby zobaczyć produkty.';
  }
  updateFavoriteHearts();
}
function updateFavoriteHearts() {
  for (const button of document.querySelectorAll('[data-favorite-id]')) {
    const chosen = !!marketOwner && marketPreferences.favorites.includes(Number(button.dataset.favoriteId));
    button.setAttribute('aria-pressed', String(chosen));
    button.textContent = chosen ? '♥ W ulubionych' : '♡ Dodaj do ulubionych';
  }
}
function favoriteControl(product) {
  const owner = marketOwner, epoch = sessionEpoch;
  const button = node('button', owner && marketPreferences.favorites.includes(product.id) ? '♥ W ulubionych' : '♡ Dodaj do ulubionych', 'favorite-button');
  button.type = 'button'; button.dataset.favoriteId = String(product.id);
  button.setAttribute('aria-label', 'Ulubione: ' + product.name);
  button.setAttribute('aria-pressed', String(!!owner && marketPreferences.favorites.includes(product.id)));
  button.onclick = () => {
    if (epoch !== sessionEpoch || owner !== marketOwner) return;
    if (!marketOwner) { msg('Zaloguj się, aby zapisać ulubione.'); return; }
    const ids = marketPreferences.favorites;
    if (ids.includes(product.id)) marketPreferences.favorites = ids.filter(id => id !== product.id);
    else { if (ids.length >= 200) { msg('Możesz zapisać do 200 ulubionych produktów.'); return; } ids.push(product.id); }
    saveMarketPreferences(); updateFavoriteHearts();
    if (location.hash === '#favorites-section') act(loadFavorites);
  };
  return button;
}
async function loadFavorites() {
  const serial = ++favoritesSerial, epoch = sessionEpoch, owner = marketOwner;
  const ids = [...marketPreferences.favorites];
  const current = () => serial === favoritesSerial && epoch === sessionEpoch && owner === marketOwner;
  el('favorites-list').replaceChildren();
  if (!owner || !ids.length) { el('favorites-status').textContent = owner ? 'Nie masz jeszcze ulubionych. Kliknij serduszko pod ofertą.' : 'Zaloguj się, aby zapisywać ulubione produkty.'; return; }
  el('favorites-status').textContent = 'Pobieranie ulubionych…';
  try {
    const data = await api('/catalog/favorites','POST',{ids}); if (!current()) return;
    if (!Array.isArray(data.items) || data.items.length > ids.length) throw Error('Nieprawidłowe ulubione');
    for (const id of ids) {
      const product = data.items.find(p => p.id === id);
      const card = node('article', '', 'card');
      const p = product || {id, name:'Produkt #' + id + ' — obecnie niedostępny'};
      card.append(node('h3',p.name));
      if (product) {
        card.append(node('p', money(p.price_grosze) + ' / ' + saleUnitLabel(p) + ' • Dostępne: ' + p.stock));
        if (role === 'klient') {
          const add = node('button', 'Dodaj 1 do koszyka'); add.type = 'button';
          add.onclick = () => act(() => singleWrite('favorite-cart:'+id, add, async () => {
            if (!current()) return; requireResolvedCheckout();
            await api('/cart/items','PUT',{product_id:id,quantity:1});
            if (current()) { msg('Produkt zapisany w koszyku.'); await loadCart(); }
          }));
          card.append(add);
        }
      }
      card.append(favoriteControl(p)); el('favorites-list').append(card);
    }
    el('favorites-status').textContent = 'Ulubione produkty: ' + ids.length + '. Dostępność i cena są sprawdzane przy zakupie.';
  } catch { if (current()) el('favorites-status').textContent = 'Nie udało się pobrać ulubionych. Spróbuj ponownie.'; }
}
el('favorites-nav-link').addEventListener('click', () => act(loadFavorites));
el('favorites-refresh').onclick = () => act(loadFavorites);
el('nearby-nav-link').addEventListener('click', () => {
  if (el('nearby-lat').value && el('nearby-lon').value) act(() => searchNearby());
  else el('nearby-status').textContent = 'Wybierz miejscowość lub kliknij „Użyj mojej lokalizacji”.';
});
