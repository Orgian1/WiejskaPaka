"use strict";
let savedLocationSerial=0;
async function loadSavedLocation(){
  const serial=++savedLocationSerial,epoch=sessionEpoch;
  el('saved-location-controls').hidden=!['klient','rolnik'].includes(role);
  if(!['klient','rolnik'].includes(role))return;
  const data=await api('/account/location');
  if(serial!==savedLocationSerial||epoch!==sessionEpoch||!data.location)return;
  invalidateNearby();
  el('nearby-lat').value=coordinateText(data.location.latitude_e6);
  el('nearby-lon').value=coordinateText(data.location.longitude_e6);
  el('address-status').textContent='Używam lokalizacji zapisanej na Twoim koncie. Możesz wybrać inny adres lub GPS.';
  if(role==='klient')await searchNearby();
}
const locationControls=node('div');locationControls.id='saved-location-controls';locationControls.hidden=true;
locationControls.append(node('p','Zapisz wybrane miejsce na swoim koncie, aby używać go po kolejnym zalogowaniu. Zapis jest dobrowolny; możesz go usunąć.'));
const saveLocationButton=node('button','Zapamiętaj wybraną lokalizację na koncie');saveLocationButton.type='button';
saveLocationButton.onclick=()=>act(async()=>{
  if(saveLocationButton.disabled)return;
  if(!el('nearby-lat').value||!el('nearby-lon').value)throw Error('Najpierw wybierz adres lub lokalizację GPS.');
  const payload={latitude_e6:coordinateE6(el('nearby-lat').value,90),longitude_e6:coordinateE6(el('nearby-lon').value,180)};
  savedLocationSerial++;saveLocationButton.disabled=true;
  try{await api('/account/location','PUT',payload);msg('Lokalizacja zapisana na Twoim koncie.')}finally{saveLocationButton.disabled=false}
});
const removeLocationButton=node('button','Usuń zapamiętaną lokalizację');removeLocationButton.type='button';
removeLocationButton.onclick=()=>act(async()=>{
  if(removeLocationButton.disabled)return;
  savedLocationSerial++;removeLocationButton.disabled=true;
  try{await api('/account/location','DELETE');resetNearbySearch();msg('Usunięto lokalizację zapisaną na koncie.')}finally{removeLocationButton.disabled=false}
});
locationControls.append(saveLocationButton,removeLocationButton);el('nearby-form').before(locationControls);

for(const id of ['address-city','address-street','address-postcode','nearby-lat','nearby-lon'])el(id).addEventListener('input',()=>{savedLocationSerial++});
for(const id of ['nearby-geolocate','nearby-clear','address-find'])el(id).addEventListener('click',()=>{savedLocationSerial++},true);
