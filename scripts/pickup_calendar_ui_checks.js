const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function element(){return {children:[],attrs:{},hidden:true,disabled:false,textContent:'',append(...items){this.children.push(...items)},replaceChildren(){this.children=[]},setAttribute(k,v){this.attrs[k]=v}};}
const fields=new Map(),el=id=>{if(!fields.has(id))fields.set(id,element());return fields.get(id)},messages=[];
const c=vm.createContext({el,node:(tag,text)=>Object.assign(element(),{tag,textContent:text}),role:'klient',Date,msg:text=>messages.push(text),fetch:async()=>({ok:true,json:async()=>({enabled:true})})});
vm.runInContext(fs.readFileSync('web/pickup-calendar.js','utf8'),c);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 await tick();assert.equal(el('point-calendar-fields').hidden,false);
 const today=c.calendarDate(c.calendarToday()),host=el('point-calendar');
 const grid=()=>host.children.find(n=>n.attrs['aria-label']==='Wybierz daty obecności');
 const button=()=>grid().children.find(n=>n.attrs['aria-label']===today);
 assert.equal(button().attrs['aria-pressed'],'false');
 assert.throws(()=>c.pickupDatesPayload(),/przynajmniej/);
 button().onclick();assert.equal(button().attrs['aria-pressed'],'true');
 assert.equal(c.pickupDatesPayload().attendance_dates.join(','),today);
 c.editPickupCalendar({attendance_dates:[today]});
 assert.equal(c.pickupDatesPayload(true).attendance_dates.join(','),today);
 button().onclick();assert.equal(button().attrs['aria-pressed'],'false');
 assert.equal(c.pickupDatesPayload(true).attendance_dates.join(','),today); // Separate point calendars.
 c.resetPickupCalendars();assert.equal(el('point-edit-calendar').children.length,0);
 assert.throws(()=>c.pickupDatesPayload(),/przynajmniej/);
 const controls=host.children[0];assert.equal(controls.children[0].disabled,true);
 controls.children[2].onclick();assert.notEqual(host.children[0].children[1].textContent,controls.children[1].textContent);
 console.log('Calendar selection, point separation, payload and logout cleanup: PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
