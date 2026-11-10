// A server-side campaign entitlement. The browser never decides its expiry or limit.
let pickupPromotionGeneration = 0, pickupPromotionRequest = 0;
function resetPickupPromotion() {
  pickupPromotionGeneration++; pickupPromotionRequest++;
  el('pickup-promotion').hidden = true;
  el('pickup-promo-form').reset(); el('pickup-promo-form').hidden = true;
  el('pickup-promo-submit').disabled = false;
  el('pickup-promo-status').textContent = '';
  el('pickup-promo-points').replaceChildren();
}
async function loadPickupPromotion(points, parentCurrent = () => true) {
  if (role !== 'rolnik') return;
  const request = ++pickupPromotionRequest, epoch = sessionEpoch, generation = pickupPromotionGeneration;
  const current = () => request === pickupPromotionRequest && epoch === sessionEpoch &&
    generation === pickupPromotionGeneration && role === 'rolnik' && parentCurrent();
  try {
    const data = await api('/farmers/me/pickup-promotion');
    if (!current()) return;
    el('pickup-promotion').hidden = data.enabled !== true;
    el('pickup-promo-points').replaceChildren();
    if (data.enabled !== true) return;
    el('pickup-promo-form').hidden = data.redeemed || data.expired;
    el('pickup-promo-status').textContent = data.active ?
      'Promocja aktywna do końca 31 grudnia 2026 r. Bezpłatne punkty: ' + data.covered_point_ids.length + '/3. Wolne miejsca: ' + data.remaining + '.' :
      data.expired ? 'Promocja zakończyła się 31 grudnia 2026 r. Nie pobrano opłaty ani nie wyłączono punktów.' :
      'Wpisz kod, aby otrzymać do trzech bezpłatnych punktów odbioru do końca grudnia 2026 r.';
    for (const point of points) {
      if (!data.covered_point_ids.includes(point.id)) continue;
      el('pickup-promo-points').append(node('li', point.name + ' — bezpłatny w promocji do 31.12.2026'));
    }
  } catch (error) {
    if (!current() || error.message === 'SESSION_CHANGED') return;
    el('pickup-promotion').hidden = false;
    el('pickup-promo-form').hidden = true;
    el('pickup-promo-status').textContent = 'Nie udało się sprawdzić promocji. Odśwież profil sprzedawcy.';
  }
}
el('pickup-promo-form').onsubmit = event => {
  event.preventDefault();
  if (role !== 'rolnik' || el('pickup-promo-submit').disabled) return;
  const epoch = sessionEpoch, generation = pickupPromotionGeneration;
  const current = () => epoch === sessionEpoch && generation === pickupPromotionGeneration && role === 'rolnik';
  el('pickup-promo-submit').disabled = true;
  const code = el('pickup-promo-code').value;
  act(async () => {
    try {
      await api('/farmers/me/pickup-promotion', 'POST', {code});
      if (!current()) return;
      el('pickup-promo-code').value = '';
      await loadFarmer();
    } catch (error) {
      if (current() && error.message !== 'SESSION_CHANGED') el('pickup-promo-status').textContent = error.message;
    } finally {
      if (current()) el('pickup-promo-submit').disabled = false;
    }
  });
};
