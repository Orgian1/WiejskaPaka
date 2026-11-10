// Public contact form. Mail delivery will be connected separately.
(() => {
  const form = document.getElementById('contact-form');
  const topic = document.getElementById('contact-topic');
  const status = document.getElementById('contact-status');
  if (!form || !topic || !status) return;

  for (const link of document.querySelectorAll('[data-contact-topic]')) {
    link.addEventListener('click', () => {
      topic.value = link.dataset.contactTopic === 'problem' ? 'problem' : 'contact';
      document.getElementById('contact-heading').focus({preventScroll: true});
    });
  }
  // Also block implicit submission with Enter. Never put form data in a URL.
  form.addEventListener('submit', event => {
    event.preventDefault();
    status.textContent = 'Wysyłka wiadomości nie jest jeszcze uruchomiona. Wiadomość nie została wysłana.';
  });
})();
