"use strict";
// Local Leaflet and Natural Earth overview work without third-party requests.
// Detailed OSM tiles are requested only after a separate, explicit click.
const pickupMaps=new Map();
let pickupWorld=null;
async function pickupWorldData(){
  if(!pickupWorld)pickupWorld=fetch('/assets/map-countries.geojson',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('Nie można wczytać mapy poglądowej.');return r.json()}).catch(e=>{pickupWorld=null;throw e});
  return pickupWorld;
}
function pickupPointCoordinates(){
  const lat=el('point-map-lat').value,lon=el('point-map-lon').value;
  return lat&&lon?{latitude_e6:coordinateE6(lat,90),longitude_e6:coordinateE6(lon,180)}:{};
}
function resetPickupMap(prefix){
  const widget=pickupMaps.get(prefix);if(!widget)return;
  widget.serial++;widget.results.replaceChildren();widget.status.textContent='';
  widget.search.disabled=false;widget.gps.disabled=false;
  if(widget.marker){widget.marker.remove();widget.marker=null}
  const lat=widget.lat.value,lon=widget.lon.value;
  if(lat&&lon&&widget.map){
    const location=[coordinateE6(lat,90)/1e6,coordinateE6(lon,180)/1e6];
    widget.marker=L.circleMarker(location,{radius:8,color:'#b11635',fillOpacity:1}).addTo(widget.map);
    widget.map.setView(location,15);
  }
}
function resetPickupMapViews(){
  for(const prefix of pickupMaps.keys()){
    if(prefix==='point'){el('point-map-lat').value='';el('point-map-lon').value=''}
    resetPickupMap(prefix);
  }
}
function createPickupMap(prefix,editing){
  const form=el(editing?'point-edit-form':'point-form');
  const fieldset=node('fieldset');fieldset.className='pickup-map-widget';
  fieldset.append(node('legend','Lokalizacja punktu — wybierz adres lub miejsce na mapie'));
  const status=node('p');status.id=prefix+'-map-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  const results=node('div');results.id=prefix+'-map-results';
  const canvas=node('div');canvas.id=prefix+'-map';canvas.className='pickup-map';canvas.hidden=true;canvas.setAttribute('aria-label','Mapa wyboru lokalizacji punktu odbioru');
  const lat=editing?el('point-edit-lat'):node('input'),lon=editing?el('point-edit-lon'):node('input');
  if(!editing){lat.type=lon.type='hidden';lat.id='point-map-lat';lon.id='point-map-lon';fieldset.append(lat,lon)}
  const search=node('button','Wyszukaj adres punktu');search.type='button';search.id=prefix+'-map-search';
  const open=node('button','Wybierz na mapie');open.type='button';open.id=prefix+'-map-open';
  const gps=node('button','Użyj GPS dla punktu');gps.type='button';gps.id=prefix+'-map-gps';
  const center=node('button','Wybierz środek mapy');center.type='button';center.hidden=true;
  const tiles=node('button','Włącz szczegółową mapę ulic (OpenStreetMap)');tiles.type='button';tiles.hidden=true;
  fieldset.append(node('p','Lokalizacja punktu jest publiczna. Mapa poglądowa nie wymaga usług zewnętrznych. Szczegółowa mapa przekaże wyświetlany obszar do OpenStreetMap dopiero po jej włączeniu.'),search,open,gps,results,canvas,center,tiles,status);
  form.querySelector('button[type=submit]').before(fieldset);
  const widget={serial:0,map:null,marker:null,status,results,lat,lon,search,gps};pickupMaps.set(prefix,widget);
  const current=(serial,epoch)=>serial===widget.serial&&epoch===sessionEpoch&&role==='rolnik';
  function select(latitude,longitude){
    longitude=((longitude+180)%360+360)%360-180;
    lat.value=coordinateText(Math.round(latitude*1e6));lon.value=coordinateText(Math.round(longitude*1e6));
    if(editing)el('point-edit-clear-coordinates').checked=false;
    if(widget.marker)widget.marker.remove();
    if(widget.map)widget.marker=L.circleMarker([latitude,longitude],{radius:8,color:'#b11635',fillOpacity:1}).addTo(widget.map);
    status.textContent='Wybrano miejsce punktu. Zapisz formularz, aby zachować lokalizację.';
  }
  async function initialize(){
    const epoch=sessionEpoch,serial=widget.serial;
    const world=await pickupWorldData();if(!current(serial,epoch))return false;
    canvas.hidden=false;center.hidden=tiles.hidden=false;
    if(!widget.map){
      widget.map=L.map(canvas,{minZoom:3,maxZoom:19}).setView([52,19],6);
      L.geoJSON(world,{style:{color:'#65836a',weight:1,fillColor:'#e4edda',fillOpacity:1}}).addTo(widget.map);
      widget.map.attributionControl.addAttribution('Natural Earth · mapa poglądowa');
      widget.map.on('click',event=>{if(role==='rolnik'){widget.serial++;search.disabled=gps.disabled=false;results.replaceChildren();select(event.latlng.lat,event.latlng.lng)}});
    }
    widget.map.invalidateSize();
    if(lat.value&&lon.value){select(coordinateE6(lat.value,90)/1e6,coordinateE6(lon.value,180)/1e6);widget.map.setView(widget.marker.getLatLng(),15)}
    return true;
  }
  open.onclick=()=>act(async()=>{if(await initialize())status.textContent='Kliknij miejsce na mapie albo przesuń mapę klawiszami strzałek i wybierz jej środek. Mapa poglądowa nie pokazuje ulic.'});
  center.onclick=()=>{widget.serial++;results.replaceChildren();const p=widget.map.getCenter();select(p.lat,p.lng)};
  tiles.onclick=()=>act(async()=>{
    if(!widget.map||tiles.disabled)return;
    tiles.disabled=true;
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,referrerPolicy:'origin',attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>'})
      .on('tileerror',()=>{status.textContent='Nie można wczytać mapy ulic. Mapa poglądowa i wybór GPS/adresu nadal działają.'}).addTo(widget.map);
    status.textContent='Włączono mapę ulic OpenStreetMap. Sprawdź położenie przed zapisaniem.';
  });
  gps.onclick=()=>{
    if(!navigator.geolocation){status.textContent='GPS jest niedostępny. Wybierz adres lub miejsce na mapie.';return}
    const serial=++widget.serial,epoch=sessionEpoch;gps.disabled=true;status.textContent='Oczekuję na zgodę na lokalizację urządzenia.';
    navigator.geolocation.getCurrentPosition(position=>act(async()=>{
      if(!current(serial,epoch))return;
      gps.disabled=false;
      const {latitude,longitude}=position.coords;
      if(!Number.isFinite(latitude)||!Number.isFinite(longitude)||Math.abs(latitude)>90||Math.abs(longitude)>180)throw Error('Nieprawidłowa lokalizacja GPS');
      select(latitude,longitude);if(await initialize())widget.map.setView([latitude,longitude],17);
    }),()=>{if(current(serial,epoch)){gps.disabled=false;status.textContent='Nie udostępniono lokalizacji. Wybierz adres lub miejsce na mapie.'}},{enableHighAccuracy:false,timeout:10000,maximumAge:60000});
  };
  search.onclick=()=>act(async()=>{
    const serial=++widget.serial,epoch=sessionEpoch;
    const city=el(editing?'point-edit-city':'point-city').value.trim(),street=el(editing?'point-edit-street':'point-street').value.trim();
    if(city.length<2)throw Error('Wpisz miejscowość punktu.');
    search.disabled=true;results.replaceChildren();status.textContent='Szukam adresu punktu…';
    try{
      const config=await fetch('/address-search/config',{cache:'no-store'}).then(r=>r.json());if(!current(serial,epoch))return;
      const response=await fetch(config.enabled?'/address-search':'/address-search/pickup-locations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({city,street,postal_code:''}),cache:'no-store'});
      const data=await response.json();if(!current(serial,epoch))return;
      if(!response.ok)throw Error('Wyszukiwanie adresu jest niedostępne. Użyj mapy lub GPS.');
      status.textContent=data.items.length?'Wybierz adres, a potem sprawdź miejsce na mapie.':config.enabled?'Brak wyników. Zmień adres lub użyj mapy/GPS.':'Brak zapisanego punktu pod tym adresem. Pełna wyszukiwarka wymaga konfiguracji geokodera; możesz użyć mapy lub GPS.';
      for(const place of data.items){
        const button=node('button',place.label);button.type='button';button.onclick=()=>act(async()=>{
          if(!current(serial,epoch))return;
          select(place.latitude_e6/1e6,place.longitude_e6/1e6);results.replaceChildren();if(await initialize())widget.map.setView(widget.marker.getLatLng(),17);
        });results.append(button);
      }
    }finally{if(current(serial,epoch))search.disabled=false}
  });
  for(const id of editing?['point-edit-city','point-edit-street']:['point-city','point-street'])el(id).addEventListener('input',()=>{
    widget.serial++;lat.value=lon.value='';if(widget.marker){widget.marker.remove();widget.marker=null}
    results.replaceChildren();search.disabled=gps.disabled=false;status.textContent='Adres zmieniony. Wybierz ponownie miejsce na mapie, GPS lub wynik wyszukiwania.';
  });
  form.addEventListener('reset',()=>{queueMicrotask(()=>resetPickupMap(prefix))});
}
createPickupMap('point',false);createPickupMap('point-edit',true);
