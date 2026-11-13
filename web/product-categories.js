"use strict";
let productTaxonomy=null,productTaxonomyLoading=null,categorySelection=null,subcategorySelection=null;
async function ensureProductTaxonomy(){
  if(productTaxonomy)return;
  if(!productTaxonomyLoading)productTaxonomyLoading=(async()=>{
    const response=await fetch('/product-categories',{cache:'no-store'});if(!response.ok)throw Error('Nie można pobrać kategorii. Odśwież stronę.');
    const data=await response.json();if(!Array.isArray(data.categories)||data.categories.length!==16)throw Error('Nieprawidłowy katalog kategorii');
    productTaxonomy=data.categories;
    const bar=el('catalog-category-bar');bar.replaceChildren();
    for(const category of [{id:'',label:'Wszystkie'},...productTaxonomy]){
      const button=node('button',category.label);button.type='button';button.dataset.categoryId=category.id;
      button.onclick=()=>{categorySelection=category.id||null;subcategorySelection=null;renderCategorySelection();catalogOffset=0;act(loadProducts)};bar.append(button);
    }
    configureCategorySelects(el('product-category'),el('product-subcategory'),'other','other-other');
    renderCategorySelection();
    el('new-product').addEventListener('reset',()=>queueMicrotask(()=>configureCategorySelects(el('product-category'),el('product-subcategory'),'other','other-other')));
    el('catalog-subcategory').onchange=()=>{subcategorySelection=el('catalog-subcategory').value||null;catalogOffset=0;act(loadProducts)};
    for(const id of ['catalog-available','catalog-fulfillment','catalog-sort'])el(id).onchange=()=>{catalogOffset=0;act(loadProducts)};
    el('catalog-use-location').onclick=()=>{el('nearby-section').scrollIntoView();el('nearby-geolocate').focus()};
    el('catalog-use-gps').onclick=()=>el('nearby-geolocate').click();
  })().catch(error=>{productTaxonomyLoading=null;throw error});
  return productTaxonomyLoading;
}
function configureCategorySelects(main,sub,selected,selectedSub){
  main.replaceChildren();for(const c of productTaxonomy){const option=node('option',c.label);option.value=c.id;option.defaultSelected=c.id===(selected||'other');main.append(option)}main.value=selected||'other';
  const fill=value=>{sub.replaceChildren();for(const s of productTaxonomy.find(c=>c.id===main.value).subcategories){const option=node('option',s.label);option.value=s.id;option.defaultSelected=s.id===(value||main.value+'-other');sub.append(option)}sub.value=value||main.value+'-other'};
  fill(selectedSub);main.onchange=()=>fill(null);
}
function renderCategorySelection(){
  if(!productTaxonomy)return;
  for(const button of el('catalog-category-bar').children){const active=(button.dataset.categoryId||null)===categorySelection;button.setAttribute('aria-pressed',String(active));button.classList.toggle('active',active)}
  const field=el('catalog-subcategory-field');field.hidden=!categorySelection;
  const select=el('catalog-subcategory');select.replaceChildren();const all=node('option','Wszystkie podkategorie');all.value='';select.append(all);
  if(categorySelection)for(const s of productTaxonomy.find(c=>c.id===categorySelection).subcategories){const option=node('option',s.label);option.value=s.id;select.append(option)}
  select.value=subcategorySelection||'';
}
function resetProductCategoryFilters(){
  categorySelection=subcategorySelection=null;
  if(el('catalog-available')){el('catalog-available').checked=false;el('catalog-fulfillment').value='all';el('catalog-sort').value='newest';el('catalog-location-prompt').hidden=true}
  renderCategorySelection();
}
function catalogFilterPayload(q,limit,offset){
  const payload={q,limit,offset,category_id:categorySelection,subcategory_id:subcategorySelection,available_now:el('catalog-available').checked,fulfillment:el('catalog-fulfillment').value,sort:el('catalog-sort').value};
  if(catalogSellerId!==null)payload.farmer_id=catalogSellerId;
  const missing=payload.sort==='nearest'&&(!el('nearby-lat').value||!el('nearby-lon').value);el('catalog-location-prompt').hidden=!missing;
  if(missing)return null;
  if(payload.sort==='nearest'){payload.latitude_e6=coordinateE6(el('nearby-lat').value,90);payload.longitude_e6=coordinateE6(el('nearby-lon').value,180)}
  return payload;
}
function refreshCatalogLocation(){if(el('catalog-sort')?.value==='nearest'){catalogOffset=0;act(loadProducts)}}
async function productEditor(product,active){
  await ensureProductTaxonomy();if(!active())return node('div');
  const details=node('details'),form=node('form');details.dataset.productEditor=String(product.id);details.append(node('summary','Edytuj produkt'));
  function field(label,tag,value){const control=node(tag);control.value=value??'';control.setAttribute('aria-label',label);const wrap=node('label',label);wrap.append(control);form.append(wrap);return control}
  const name=field('Nazwa produktu','input',product.name);name.required=true;name.maxLength=120;
  const category=field('Kategoria produktu','select'),sub=field('Podkategoria produktu','select');configureCategorySelects(category,sub,product.category_id,product.subcategory_id);
  const description=field('Opis produktu','textarea',product.description);description.maxLength=2000;
  const price=field('Cena produktu w zł','input',(product.price_grosze/100).toFixed(2));price.inputMode='decimal';
  const delivery=field('Opłata dostawy w zł','input',(product.delivery_grosze/100).toFixed(2));delivery.inputMode='decimal';
  const stock=field('Stan magazynowy','input',product.stock);stock.type='number';stock.min='0';stock.max='1000000';stock.required=true;
  form.append(node('p','Jednostka sprzedaży: '+saleUnitLabel(product)+'. Zachowujemy jednostkę używaną w koszykach i zamówieniach. Zdjęcie zmienisz w panelu zdjęć.'));
  const photos=node('a','Zmień zdjęcia produktu');photos.href='#user-photo-panel';form.append(photos);const save=node('button','Zapisz produkt');save.type='submit';form.append(save);details.append(form);
  form.onsubmit=event=>{event.preventDefault();act(()=>singleWrite('edit-product:'+product.id,save,async()=>{
    if(!active()||!form.isConnected||role!=='rolnik')return;
    const values={name:name.value,category_id:category.value,subcategory_id:sub.value,description:description.value,price_grosze:parseGrosze(price.value),delivery_grosze:parseGrosze(delivery.value),stock:Number(stock.value)};
    const changes={};for(const [key,value] of Object.entries(values))if(value!==(product[key]??''))changes[key]=value;
    if(!Object.keys(changes).length){msg('Nie zmieniono danych produktu.');return}
    if('stock' in changes)changes.expected_stock=product.stock;await api('/products/mine/'+product.id,'PATCH',changes);
    if(!active())return;msg('Produkt zapisany');if(typeof loadSellerListings==='function')await loadSellerListings();await loadProducts();await loadDashboard();
  }))};return details;
}
