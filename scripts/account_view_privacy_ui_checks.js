const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function main(name){
 class Element{
  constructor(){this.children=[];this.value='';this.text='';this.hidden=false;this.checked=false;this.resets=0}
  append(...nodes){this.children.push(...nodes)}
  querySelectorAll(){return this.children.flatMap(n=>[n,...n.querySelectorAll('*')])}
  replaceChildren(){this.children=[];this.text=''}
  set textContent(value){this.text=String(value);this.children=[]}
  get textContent(){return this.text+this.children.map(n=>n.textContent).join('')}
  reset(){this.resets++}
 }
 const elements=new Map(),el=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id)},requests=[];
 const c=vm.createContext({el,console,role:'klient',pendingCartCheckout:{private:'draft'},checkoutOwner:1,cartQuoteSerial:0,cartQuoteItems:[{private:'quote'}],productRequest:0,orderRequest:0,farmerRequest:0,cartRefreshSerial:0,
   act:fn=>requests.push(fn.name),loadCart:()=>{},loadProducts:()=>{},loadOrders:()=>{},hasUnresolvedCheckout:()=>false,
   loadFarmer:()=>{},loadDashboard:()=>{},resetPinRecoveryViews:()=>{},resetPasswordChangeView:()=>{},resetSessionSecurityView:()=>{},
   localStorage:{setItem(){throw Error('Forbidden storage')}},sessionStorage:{setItem(){throw Error('Forbidden storage')}}});
 const source=fs.readFileSync('web/app.js','utf8');
 const helper=source.split('function clearPrivateAccountViews(){',2)[1].split('function logged(user){',1)[0];
 vm.runInContext('function clearPrivateAccountViews(){'+helper+'\n'+source.split('\n').find(line=>line.startsWith('function logged(user){')),c);
 const fields=['cart-city','cart-street','cart-postal','email','password'];
 for(const id of fields)el(id).value='PRIVATE-OLD-'+id;
 const detached=[];
 for(const id of ['products','orders','my-points','dashboard-content','notifications-list','cart-items']){
   const row=new Element(),text=new Element(),input=new Element();text.textContent='PRIVATE-ADDRESS-PIN';input.value='PRIVATE-INPUT';input.checked=true;
   row.append(text,input);el(id).append(row);detached.push(text,input);
 }
 el('cart-point').append(new Element());el('cart-farmer-select').append(new Element());el('cart-total').textContent='PRIVATE-TOTAL';
 const user=name.startsWith('switch_')?{id:2,email:'new@example.invalid',role:{client:'klient',farmer:'rolnik',courier:'dostawca',admin:'admin'}[name.slice(7)]}:null;
 el('role').value=user?.role==='rolnik'?'klient':'rolnik'; // Registration choice cannot change the authenticated role.
 // No refresh is allowed to complete: cleanup must happen before any network result.
 c.logged(user);if(name==='repeat_reset')c.logged(null);
 for(const id of fields)assert.equal(el(id).value,'',id);
 for(const item of detached){assert.equal(item.value,'');assert.equal(item.textContent,'');assert.equal(item.checked,false)}
 for(const id of ['products','orders','my-points','dashboard-content','notifications-list','cart-items','cart-point','cart-farmer-select'])assert.equal(el(id).children.length,0,id);
 for(const id of ['cart-checkout','profile-form','point-form','new-product'])assert(el(id).resets>=1,id);
 assert.equal(el('cart-total').textContent,'');assert.equal(el('cart-address').hidden,true);assert.equal(el('cart-pickup').hidden,false);
 assert.equal(c.pendingCartCheckout,null);assert.equal(c.checkoutOwner,user?.id??null);
 assert.equal(c.cartQuoteItems.length,0);assert.equal(c.role,user?.role??null);
 if(user){assert.match(el('identity').textContent,/new@example.invalid/)}else assert.equal(el('identity').textContent,'Nie zalogowano');
 assert.equal(el('auth').hidden,Boolean(user));
 assert.equal(el('cart-section').hidden,user?.role!=='klient');
 assert.equal(el('farmer').hidden,user?.role!=='rolnik');
 assert.equal(el('seller-nav-link').hidden,user?.role!=='rolnik');
 assert.equal(el('cart-nav-link').hidden,user?.role!=='klient');
 assert.equal(el('account-security').open,false);
 if(user)assert.equal(el('account-section').className,'account-compact');
 assert(requests.includes('loadProducts'));
}
try{main(process.argv[2]);process.stdout.write('PASS\n')}catch(error){console.error(error);process.exitCode=1}
