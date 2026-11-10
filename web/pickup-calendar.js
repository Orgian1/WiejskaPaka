// Attendance dates are calendar days in Poland; no GPS or browser storage.
let pickupDatesEnabled=false,pickupCreateCalendar=null,pickupEditCalendar=null;
function calendarDate(value){return `${value.getFullYear()}-${String(value.getMonth()+1).padStart(2,'0')}-${String(value.getDate()).padStart(2,'0')}`;}
function calendarToday(){const parts=new Intl.DateTimeFormat('en',{timeZone:'Europe/Warsaw',year:'numeric',month:'numeric',day:'numeric'}).formatToParts(new Date());const value=type=>Number(parts.find(p=>p.type===type).value);return new Date(value('year'),value('month')-1,value('day'));}
function createPickupCalendar(host,initial=[]){
  const current=calendarToday(),minimum=calendarDate(current),maximumDate=new Date(current.getFullYear(),current.getMonth(),current.getDate()+365),maximum=calendarDate(maximumDate);
  let month=new Date(current.getFullYear(),current.getMonth(),1),selected=new Set(initial.filter(value=>value>=minimum&&value<=maximum));
  function draw(){
    host.replaceChildren();const controls=node('div','','calendar-controls'),previous=node('button','Poprzedni miesiąc'),next=node('button','Następny miesiąc');previous.type=next.type='button';
    previous.disabled=month.getFullYear()===current.getFullYear()&&month.getMonth()===current.getMonth();
    next.disabled=month.getFullYear()===maximumDate.getFullYear()&&month.getMonth()===maximumDate.getMonth();
    previous.onclick=()=>{month=new Date(month.getFullYear(),month.getMonth()-1,1);draw();};next.onclick=()=>{month=new Date(month.getFullYear(),month.getMonth()+1,1);draw();};
    const heading=node('strong',month.toLocaleDateString('pl-PL',{month:'long',year:'numeric'}));heading.setAttribute('aria-live','polite');controls.append(previous,heading,next);host.append(controls);
    const grid=node('div','','pickup-calendar-grid');grid.setAttribute('aria-label','Wybierz daty obecności');
    for(const day of ['Pn','Wt','Śr','Cz','Pt','So','Nd'])grid.append(node('span',day));
    for(let i=0;i<(month.getDay()+6)%7;i++)grid.append(node('span',''));
    const count=new Date(month.getFullYear(),month.getMonth()+1,0).getDate();
    for(let day=1;day<=count;day++){
      const value=calendarDate(new Date(month.getFullYear(),month.getMonth(),day)),button=node('button',String(day));button.type='button';button.disabled=value<minimum||value>maximum;
      button.setAttribute('aria-label',value);button.setAttribute('aria-pressed',String(selected.has(value)));
      button.onclick=()=>{if(selected.has(value))selected.delete(value);else if(selected.size<90)selected.add(value);else{msg('Możesz wybrać maksymalnie 90 dat.');return;}draw();};grid.append(button);
    }
    host.append(grid,node('p',selected.size?'Wybrane daty: '+[...selected].sort().join(', '):'Zaznacz dni, w których będziesz w tym punkcie.'));
  }
  draw();return {values(){return [...selected].sort();},clear(){selected.clear();draw();}};
}
function pickupDatesPayload(editor=false){
  if(!pickupDatesEnabled)return {};
  const calendar=editor?pickupEditCalendar:pickupCreateCalendar,values=calendar?.values()||[];
  if(!values.length)throw Error('Zaznacz przynajmniej jedną datę obecności w punkcie.');
  return {attendance_dates:values};
}
function resetPickupCalendars(){
  pickupCreateCalendar?.clear();pickupEditCalendar?.clear();
  pickupEditCalendar=null;el('point-edit-calendar').replaceChildren();
}
function editPickupCalendar(point){
  if(pickupDatesEnabled)pickupEditCalendar=createPickupCalendar(el('point-edit-calendar'),point.attendance_dates||[]);
}
async function loadPickupCalendars(){
  try{const response=await fetch('/pickup-point-dates/config',{cache:'no-store'});if(!response.ok||!(await response.json()).enabled)return;
    pickupDatesEnabled=true;el('point-calendar-fields').hidden=false;el('point-edit-calendar-fields').hidden=false;
    pickupCreateCalendar=createPickupCalendar(el('point-calendar'));
    if(typeof showPointEditor==='function'&&role==='rolnik')showPointEditor();
  }catch{/* Keep legacy point forms if the calendar feature is disabled. */}
}
loadPickupCalendars();
