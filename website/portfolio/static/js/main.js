// Activate tag filter buttons
function setActive(el) {
  document.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
}
