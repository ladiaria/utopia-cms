let activeModal = null;

function onKeyDown(e) {
  if (e.key === 'Escape') closeModal(activeModal);
}

export function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;

  activeModal = id;
  modal.setAttribute('aria-hidden', 'false');
  modal.classList.add('modal--open');
  document.body.classList.add('modal-open');
  document.addEventListener('keydown', onKeyDown);

  modal.addEventListener('click', function onOverlayClick(e) {
    if (e.target === modal) {
      closeModal(id);
      modal.removeEventListener('click', onOverlayClick);
    }
  });
}

export function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;

  activeModal = null;
  modal.setAttribute('aria-hidden', 'true');
  modal.classList.remove('modal--open');
  document.body.classList.remove('modal-open');
  document.removeEventListener('keydown', onKeyDown);
}
