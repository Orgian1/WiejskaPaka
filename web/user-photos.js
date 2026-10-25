// All upload kinds use the same authenticated raw-body endpoint and server sanitizer.
let userPhotosEnabled=false,photoViewSerial=0;
async function newProductPhotoPayload(){
  if(!userPhotosEnabled)return null;
  const file=el('product-photo-file').files?.[0];
  if(!file||!file.size||file.size>20000000)throw Error('Wybierz jedno zdjęcie produktu JPEG, PNG lub WebP do 20 MB. Zmniejszymy je do 500 KB.');
  return new Promise((resolve,reject)=>{
    const reader=new FileReader();
    reader.onload=()=>resolve(String(reader.result).split(',')[1]);
    reader.onerror=()=>reject(Error('Nie udało się odczytać zdjęcia. Wybierz je ponownie.'));
    reader.readAsDataURL(file);
  });
}
function photoImage(kind,id,digest=''){
  const image=node('img');image.alt=kind==='product'?'Zdjęcie produktu':kind==='farm'?'Zdjęcie gospodarstwa':'Zdjęcie profilowe';
  image.loading='lazy';image.width=240;image.height=240;image.className='user-photo';image.src=`/user-photos/${kind}/${id}${digest?'?v='+digest:''}`;
  image.onerror=()=>image.remove();return image;
}
function resetUserPhotoViews(){photoViewSerial++;const host=el('user-photo-editors');if(host)host.replaceChildren();if(el('user-photo-panel'))el('user-photo-panel').hidden=true;if(el('product-photo-file'))el('product-photo-file').value='';}
async function loadUserPhotoViews(){
  resetUserPhotoViews();if(!userPhotosEnabled||!role)return;
  const epoch=sessionEpoch,serial=photoViewSerial,actorToken=token;
  const current=()=>epoch===sessionEpoch&&serial===photoViewSerial&&token===actorToken;
  const me=await api('/auth/me');if(!current())return;
  const saved=await api('/user-photos/mine');if(!current())return;
  const targets=[{kind:'profile',id:me.id,label:'Zdjęcie profilowe'}];
  if(role==='rolnik'){
    targets.push({kind:'farm',id:me.id,label:'Zdjęcie gospodarstwa'});
    const products=await api('/products/mine');if(!current())return;
    for(const p of products)targets.push({kind:'product',id:p.id,label:'Produkt: '+p.name});
  }
  el('user-photo-panel').hidden=false;
  for(const target of targets){
    const card=node('article','','card');card.append(node('h3',target.label));
    const old=saved.items.find(p=>p.kind===target.kind&&p.subject_id===target.id);
    if(old)card.append(photoImage(target.kind,target.id,old.digest));
    const file=node('input');file.type='file';file.accept='image/jpeg,image/png,image/webp';file.setAttribute('aria-label','Wybierz zdjęcie: '+target.label);
    const upload=node('button','Zapisz zdjęcie'),remove=node('button','Usuń zdjęcie'),status=node('p');
    upload.type=remove.type='button';remove.disabled=!old;status.setAttribute('role','status');
    const change=async(method)=>{
      if(!current()||upload.disabled)return;
      const selected=file.files?.[0];
      if(method==='PUT'&&(!selected||selected.size===0||selected.size>20000000)){status.textContent='Wybierz zdjęcie JPEG, PNG lub WebP do 20 MB.';return;}
      upload.disabled=remove.disabled=true;status.textContent='Przetwarzanie zdjęcia…';
      try{
        const response=await fetch(`/user-photos/${target.kind}/${target.id}`,{method,headers:{Authorization:'Bearer '+actorToken,'Content-Type':'application/octet-stream'},body:method==='PUT'?selected:undefined,cache:'no-store'});
        if(!current())return;
        if(!response.ok){status.textContent=response.status===401?'Sesja wygasła. Zaloguj się ponownie.':'Nie zapisano zmiany. Wybierz poprawny JPEG, PNG lub WebP (do 20 MB, do 50 mln pikseli).';return;}
        await loadUserPhotoViews();if(epoch===sessionEpoch){await loadProducts();}
      }catch{if(current())status.textContent='Nie udało się potwierdzić zmiany. Odśwież zdjęcia przed ponowną próbą.';}
      finally{if(current()){upload.disabled=false;remove.disabled=!old;}}
    };
    upload.onclick=()=>change('PUT');remove.onclick=()=>change('DELETE');
    card.append(file,upload,remove,status);el('user-photo-editors').append(card);
  }
}
async function initializeUserPhotos(){
  try{const response=await fetch('/user-photos/config',{cache:'no-store'});if(!response.ok||(await response.json()).enabled!==true)return;}catch{return;}
  userPhotosEnabled=true;el('user-photo-refresh').onclick=()=>act(loadUserPhotoViews);
  el('product-photo-field').hidden=false;el('product-photo-file').required=true;
  el('product-photo-help').textContent='Jedno zdjęcie JPEG, PNG lub WebP do 20 MB. Automatycznie zmniejszymy je do maksymalnie 500 KB.';
  if(role)act(loadUserPhotoViews);act(loadProducts);
}
initializeUserPhotos();
