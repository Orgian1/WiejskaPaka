// Addresses stay in this form; no browser storage, URL parameters or autocomplete.
let addressSerial=0,addressController=null,addressEnabled=false,addressLocal=true;
function clearAddressSelection(){
  addressSerial++;addressController?.abort();addressController=null;
  el('address-results').replaceChildren();el('address-status').textContent='';
  el('address-find').disabled=false;
  el('nearby-lat').value='';el('nearby-lon').value='';invalidateNearby();
}
async function findAddress(){
  clearAddressSelection();const serial=addressSerial,epoch=sessionEpoch;
  const payload={city:el('address-city').value.trim(),street:el('address-street').value.trim(),postal_code:el('address-postcode').value.trim()};
  if(payload.city.length<2){el('address-status').textContent='Wpisz miejscowość.';return;}
  if(payload.postal_code&&!/^\d{2}-\d{3}$/.test(payload.postal_code)){el('address-status').textContent='Kod pocztowy powinien mieć format 00-000.';return;}
  const controller=new AbortController();addressController=controller;
  el('address-find').disabled=true;el('address-status').textContent='Szukam adresu…';
  try{
    const response=await fetch(addressLocal?'/address-search/pickup-locations':'/address-search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),cache:'no-store',signal:controller.signal});
    const data=await response.json();
    if(serial!==addressSerial||epoch!==sessionEpoch)return;
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Wyszukiwanie adresów jest niedostępne.');
    el('address-status').textContent=data.items.length?'Wybierz właściwe miejsce. Punkt może być orientacyjny.':addressLocal?'Brak zapisanych punktów z lokalizacją w tej miejscowości. Spróbuj innej miejscowości lub użyj swojej lokalizacji.':'Nie znaleziono adresu. Uzupełnij ulicę lub kod pocztowy.';
    for(const place of data.items){
      const button=node('button',place.label);button.type='button';
      button.onclick=()=>{
        if(serial!==addressSerial||epoch!==sessionEpoch)return;
        invalidateNearby();el('nearby-lat').value=coordinateText(place.latitude_e6);el('nearby-lon').value=coordinateText(place.longitude_e6);
        el('address-status').textContent='Wybrane miejsce: '+place.label+'. '+place.notice;
        el('address-results').replaceChildren();
      };
      el('address-results').append(button);
    }
  }catch(error){
    if(serial===addressSerial&&epoch===sessionEpoch&&error.name!=='AbortError')el('address-status').textContent='Nie udało się wyszukać adresu. Spróbuj ponownie lub użyj lokalizacji urządzenia.';
  }finally{
    if(serial===addressSerial){addressController=null;el('address-find').disabled=false;}
  }
}
async function loadAddressSearch(){
  if(!el('address-fields'))return;
  addressEnabled=true;el('address-fields').hidden=false;el('nearby-manual-coordinates').hidden=true;
  el('nearby-lat').required=false;el('nearby-lon').required=false;
  el('address-find').disabled=true;
  try{
    const response=await fetch('/address-search/config',{cache:'no-store'});
    addressLocal=!response.ok||!(await response.json()).enabled;
  }catch{addressLocal=true;}
    el('address-postcode-field').hidden=addressLocal;
    el('address-provider-note').textContent=addressLocal?'Wpisz miejscowość i wybierz zapisany punkt odbioru jako początek wyszukiwania. Możesz też użyć swojej lokalizacji.':'Adres zostanie przekazany usłudze mapowej po kliknięciu przycisku. Bez ulicy możesz wskazać miejscowość.';
    el('address-attribution').hidden=addressLocal;
    el('address-find').disabled=false;
    for(const id of ['address-city','address-street','address-postcode'])el(id).addEventListener('input',clearAddressSelection);
    el('address-find').onclick=()=>act(findAddress);
    el('nearby-clear').addEventListener('click',clearAddressSelection);
    el('nearby-geolocate').addEventListener('click',()=>{
      // Run before locateNearby captures its request serial. A denied GPS request
      // must not leave the previous address active behind a different message.
      clearAddressSelection();el('address-status').textContent='Oczekuję na lokalizację urządzenia.';
    },true);
    el('nearby-form').addEventListener('submit',event=>{
      if(addressEnabled&&(!el('nearby-lat').value||!el('nearby-lon').value)){
        event.preventDefault();event.stopImmediatePropagation();el('address-status').textContent='Wyszukaj adres i wybierz miejsce lub użyj lokalizacji urządzenia.';
      }
    },true);
}
loadAddressSearch();
