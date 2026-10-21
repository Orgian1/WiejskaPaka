// Public handles are independent of the private email used for authentication.
let sellerSearchEnabled=false,sellerSearchSerial=0,sellerOffset=0,sellerTotal=0,sellerEditorSerial=0;
function sellerSearchMode(){return sellerSearchEnabled&&el('catalog-search-mode').value==='seller'}
function resetSellerDirectory(){
  sellerSearchSerial++;sellerEditorSerial++;sellerOffset=0;sellerTotal=0;
  if(el('catalog-search-mode')){
    if(el('catalog-search-mode').value==='seller'||catalogSellerId!==null)el('catalog-query').value='';
    el('catalog-search-mode').value='product';updateSellerSearchLabels();
  }
  catalogSellerId=null;
  if(el('catalog-seller-filter'))el('catalog-seller-filter').hidden=true;
  if(el('seller-results'))el('seller-results').replaceChildren();
  if(el('seller-login-panel')){el('seller-login-panel').hidden=true;el('seller-login-form').reset();el('seller-login-status').textContent='';}
}
function updateSellerSearchLabels(){
  const seller=sellerSearchMode();el('catalog-title').textContent=seller?'Sprzedawcy':'Produkty';
  el('catalog-query-label').firstChild.textContent=seller?'Login lub nazwa gospodarstwa ':'Nazwa produktu ';
  el('catalog-query').placeholder=seller?'np. @warzywa_marka lub Zielone Gospodarstwo':'np. ziemniaki';
  el('catalog-search-submit').textContent=seller?'Szukaj sprzedawcy':'Szukaj produktów';
  el('products').hidden=seller;el('seller-results').hidden=!seller;el('seller-pagination').hidden=!seller;
  el('catalog-previous').hidden=seller;el('catalog-next').hidden=seller;
}
async function loadSellerDirectory(){
  if(!sellerSearchMode())return;
  const serial=++sellerSearchSerial,epoch=sessionEpoch,offset=sellerOffset,q=el('catalog-query').value.trim();
  const current=()=>serial===sellerSearchSerial&&epoch===sessionEpoch&&sellerSearchMode();
  el('seller-previous').disabled=true;el('seller-next').disabled=true;el('seller-results').replaceChildren();
  el('catalog-status').textContent='Pobieranie sprzedawców…';
  try{
    const data=await api('/sellers/search?'+new URLSearchParams({q,limit:'24',offset:String(offset)}));if(!current())return;
    if(!data||!Array.isArray(data.items)||data.items.length>24||!Number.isSafeInteger(data.total)||data.total<0||data.limit!==24||data.offset!==offset||!data.items.every(s=>s&&Number.isSafeInteger(s.farmer_id)&&s.farmer_id>0&&typeof s.login==='string'&&typeof s.farm_name==='string'&&typeof s.city==='string'))throw Error('Nieprawidłowe wyniki');
    sellerTotal=data.total;
    for(const seller of data.items){
      const card=node('article','','card');card.append(node('h3','@'+seller.login));
      if(seller.farm_name)card.append(node('p',seller.farm_name));if(seller.city)card.append(node('p',seller.city));
      const button=node('button','Zobacz produkty sprzedawcy @'+seller.login);button.type='button';
      button.onclick=()=>{
        if(!current())return;sellerSearchSerial++;productRequest++;catalogSellerId=seller.farmer_id;catalogOffset=0;
        el('catalog-search-mode').value='product';el('catalog-query').value='';el('products').replaceChildren();updateSellerSearchLabels();
        el('catalog-seller-label').textContent='Produkty sprzedawcy @'+seller.login+(seller.farm_name?' — '+seller.farm_name:'');
        el('catalog-seller-filter').hidden=false;el('seller-results').replaceChildren();act(loadProducts);
      };card.append(button);el('seller-results').append(card);
    }
    if(!data.items.length)el('seller-results').append(node('p','Nie znaleziono sprzedawcy. Wpisz jego publiczny login lub nazwę gospodarstwa.'));
    el('catalog-status').textContent=`Sprzedawcy: ${data.total}. Strona ${Math.floor(offset/24)+1}.`+(offset+24>10000&&offset+data.items.length<data.total?' Zawęź wyszukiwanie.':'');
    el('seller-previous').disabled=offset===0;el('seller-next').disabled=offset+data.items.length>=data.total||offset+24>10000;
  }catch{if(current())el('catalog-status').textContent='Nie udało się wyszukać sprzedawców. Spróbuj ponownie.';}
}
async function loadSellerLoginEditor(){
  const serial=++sellerEditorSerial,epoch=sessionEpoch;
  el('seller-login-panel').hidden=true;
  if(!sellerSearchEnabled||role!=='rolnik')return;
  const data=await api('/sellers/me/login');
  if(serial!==sellerEditorSerial||epoch!==sessionEpoch||role!=='rolnik')return;
  el('seller-login-panel').hidden=false;el('seller-public-login').value=data.login||'';el('seller-login-status').textContent=data.login?'Twój publiczny login: @'+data.login:'Ustaw login, aby klienci mogli znaleźć Cię w wyszukiwarce sprzedawców.';
}
async function initializeSellerDirectory(){
  try{const response=await fetch('/sellers/config',{cache:'no-store'});if(!response.ok||(await response.json()).enabled!==true)return;}catch{return;}
  sellerSearchEnabled=true;el('catalog-mode-control').hidden=false;updateSellerSearchLabels();
  el('catalog-search-mode').onchange=()=>{
    sellerSearchSerial++;productRequest++;catalogSellerId=null;sellerOffset=0;catalogOffset=0;
    el('catalog-query').value='';el('catalog-seller-filter').hidden=true;el('seller-results').replaceChildren();el('products').replaceChildren();updateSellerSearchLabels();
    act(loadProducts);
  };
  el('catalog-form').onsubmit=event=>{event.preventDefault();sellerOffset=0;catalogOffset=0;act(loadProducts)};
  el('refresh').onclick=()=>{sellerOffset=0;catalogOffset=0;act(loadProducts)};
  el('seller-previous').onclick=()=>{if(sellerOffset>0){sellerOffset=Math.max(0,sellerOffset-24);act(loadSellerDirectory)}};
  el('seller-next').onclick=()=>{if(sellerOffset+24<sellerTotal&&sellerOffset+24<=10000){sellerOffset+=24;act(loadSellerDirectory)}};
  el('catalog-clear-seller').onclick=()=>{catalogSellerId=null;catalogOffset=0;el('catalog-seller-filter').hidden=true;el('products').replaceChildren();act(loadProducts)};
  el('seller-login-form').onsubmit=event=>{event.preventDefault();act(()=>singleWrite('seller-login-form',el('seller-login-save'),async()=>{
    if(role!=='rolnik')return;const epoch=sessionEpoch;
    const data=await api('/sellers/me/login','PUT',{login:el('seller-public-login').value.trim()});
    if(epoch!==sessionEpoch||role!=='rolnik')return;
    el('seller-public-login').value=data.login;el('seller-login-status').textContent='Publiczny login zapisany: @'+data.login;
    if(sellerSearchMode()){sellerOffset=0;await loadSellerDirectory();}
  }))};
  act(loadSellerLoginEditor);
}
initializeSellerDirectory();
