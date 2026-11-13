// Public contact form. Mail delivery will be connected separately.
(() => {
  const form = document.getElementById('contact-form');
  const topic = document.getElementById('contact-topic');
  const status = document.getElementById('contact-status');
  if (!form || !topic || !status) return;

  const disclosure=document.getElementById('contact-disclosure');
  globalThis.resetContactView=()=>{if(disclosure)disclosure.open=false;form.reset();status.textContent='Wysyłka wiadomości nie jest jeszcze uruchomiona. Zgłoszenia zakupowe zapiszesz po zalogowaniu.'};
  if(disclosure)disclosure.addEventListener('toggle',()=>{
    if(disclosure.open&&typeof loadSupportCases==='function')act(loadSupportCases);
  });
  // Also block implicit submission with Enter. Never put form data in a URL.
  form.addEventListener('submit', event => {
    event.preventDefault();
    status.textContent = 'Wysyłka wiadomości nie jest jeszcze uruchomiona. Wiadomość nie została wysłana.';
  });
})();
