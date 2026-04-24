// Menu mobile
const toggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('.nav-principal');
if (toggle && nav) {
  toggle.addEventListener('click', () => nav.classList.toggle('aberto'));
}

// FAQ accordion
document.querySelectorAll('.faq-pergunta').forEach(btn => {
  btn.addEventListener('click', () => {
    const item = btn.closest('.faq-item');
    const aberto = item.classList.contains('aberto');
    document.querySelectorAll('.faq-item.aberto').forEach(i => i.classList.remove('aberto'));
    if (!aberto) item.classList.add('aberto');
  });
});
