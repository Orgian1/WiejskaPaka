// Recommendations are offered before checkout: completed purchases are immutable.
let packageOffer=null;
function resetPackageOffer(){
  if(!packageOffer)return;
  const offer=packageOffer;packageOffer=null;offer.finish(false);
}
async function offerSamePackage(product,quantity,direct=false){
  if(role!=='klient'||packageOffer)return false;
  const epoch=sessionEpoch;
  const dialog=document.createElement('dialog');dialog.className='same-package-dialog';
  dialog.setAttribute('aria-labelledby','same-package-title');
  const title=node('h2','Dobierz do jednej paczki od tego sprzedawcy');title.id='same-package-title';
  const info=node('p','Dobierz produkty przed zatwierdzeniem zamówienia. Wspólny koszyk obejmie produkty tego sprzedawcy — z jedną opłatą za przesyłkę.');
  const status=node('p','Pobieranie produktów…');status.setAttribute('role','status');
  const list=node('div');list.id='same-package-products';
  const previous=node('button','Poprzednie produkty'),next=node('button','Następne produkty');
  const done=node('button',direct?'Zamów bez dodatkowych produktów':'Przejdź do koszyka');done.id='same-package-done';
  const cancel=node('button','Wróć do produktów');cancel.id='same-package-cancel';
  for(const button of [previous,next,done,cancel])button.type='button';
  dialog.append(title,info,status,list,previous,next,done,cancel);
  let offset=0,serial=0,busy=false,baseQueued=!direct;
  const current=()=>epoch===sessionEpoch&&role==='klient'&&packageOffer?.dialog===dialog;
  return new Promise(resolve=>{
    const finish=result=>{if(dialog.open)dialog.close();dialog.remove();if(packageOffer?.dialog===dialog)packageOffer=null;resolve(result)};
    packageOffer={dialog,finish};
    const cart=()=>{finish(false);el('cart-section').scrollIntoView({block:'start'});};
    done.onclick=()=>{if(busy)return;if(direct&&!baseQueued)finish(true);else cart()};
    cancel.onclick=()=>{if(!busy)finish(false)};
    dialog.addEventListener('cancel',event=>{event.preventDefault();if(!busy)finish(false)});
    const page=async()=>{
      const request=++serial;previous.disabled=true;next.disabled=true;list.replaceChildren();
      try{
        const data=await api('/catalog/search?'+new URLSearchParams({farmer_id:String(product.farmer_id),q:'',limit:'24',offset:String(offset)}));
        if(!current()||request!==serial)return;
        if(!data||!Array.isArray(data.items)||data.items.length>24||!Number.isSafeInteger(data.total)||data.total<0||data.offset!==offset||data.limit!==24||!data.items.every(p=>p&&p.farmer_id===product.farmer_id&&Number.isSafeInteger(p.id)&&p.id>0&&typeof p.name==='string'&&Number.isSafeInteger(p.stock)&&p.stock>0&&Number.isSafeInteger(p.price_grosze)&&p.price_grosze>0))throw Error('Nieprawidłowe produkty');
        const products=data.items.filter(p=>p.id!==product.id);
        if(!products.length&&offset===0&&data.total<=24){finish(direct);return;}
        status.textContent='Produkty tego sprzedawcy. Strona '+(offset/24+1)+'.';
        for(const p of products){
          const row=node('article','','card');row.append(node('h3',p.name),node('p',money(p.price_grosze)+' / '+saleUnitLabel(p)+packageLabel(p)));
          const qty=node('input');qty.type='number';qty.min='1';qty.max=String(Math.min(1000,p.stock));qty.value='1';qty.setAttribute('aria-label','Dobierz ilość: '+p.name);
          const add=node('button','Dodaj do wspólnej paczki');add.type='button';
          add.onclick=()=>act(async()=>{
            if(!current()||busy)return;requireResolvedCheckout();
            const amount=Number(qty.value);if(!Number.isSafeInteger(amount)||amount<1||amount>Math.min(1000,p.stock))throw Error('Podaj prawidłową ilość');
            busy=true;for(const b of dialog.querySelectorAll('button'))b.disabled=true;
            try{
              const saved=await api('/cart/items');if(!current())return;
              const existing=id=>saved.items.find(item=>item.product_id===id)?.quantity||0;
              const additions=baseQueued?[[p,amount]]:[[product,quantity],[p,amount]];
              for(const [item,n] of additions){if(existing(item.id)+n>Math.min(1000,item.stock))throw Error('Za duża ilość w koszyku: '+item.name);}
              for(const [item,n] of additions){
                await api('/cart/items','PUT',{product_id:item.id,quantity:existing(item.id)+n});if(!current())return;
                if(item.id===product.id){baseQueued=true;done.textContent='Przejdź do koszyka';}
              }
              done.textContent='Przejdź do koszyka';status.textContent='Dodano: '+p.name+'. Zatwierdź całą paczkę w koszyku.';
              await loadCart();if(!current())return;el('cart-farmer-select').value=String(product.farmer_id);await loadCart();
            }catch(error){if(current()&&error.message!=='SESSION_CHANGED')status.textContent='Nie udało się dodać wszystkich produktów: '+error.message;}
            finally{busy=false;if(current()){for(const b of dialog.querySelectorAll('button'))b.disabled=false;previous.disabled=offset===0;next.disabled=offset+24>=data.total||offset+24>10000;}}
          });row.append(qty,add);list.append(row);
        }
        previous.disabled=offset===0;next.disabled=offset+24>=data.total||offset+24>10000;
      }catch{if(current()&&request===serial){status.textContent='Nie udało się pobrać propozycji. Możesz wrócić do produktów lub kontynuować.';}}
    };
    previous.onclick=()=>{if(!busy&&offset>0){offset-=24;page()}};
    next.onclick=()=>{if(!busy){offset+=24;page()}};
    document.body.append(dialog);dialog.showModal();page();
  });
}
