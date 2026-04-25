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

// Últimas publicações da rede
(async () => {
  const lista = document.getElementById('ultimos-lista');
  if (!lista) return;
  try {
    const res = await fetch('data/ultimos_posts.json');
    if (!res.ok) return;
    const { posts } = await res.json();
    if (!posts || posts.length === 0) return;

    const secao = lista.closest('.secao-ultimos');

    lista.innerHTML = posts.slice(0, 8).map(p => `
      <a href="${p.url}" class="ultimo-item" role="listitem" target="_blank" rel="noopener"
         style="--cor-post: ${p.cor}">
        <div class="ultimo-cor"></div>
        <div class="ultimo-conteudo">
          <div class="ultimo-meta">
            <span class="ultimo-blog-nome">${p.blog}</span>
            <span class="ultimo-data">${p.data}</span>
          </div>
          <div class="ultimo-titulo">${p.titulo}</div>
        </div>
      </a>
    `).join('');

    if (secao) secao.removeAttribute('hidden');
  } catch (_) {}
})();
