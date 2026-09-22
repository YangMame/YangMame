(() => {
  const script = document.currentScript;
  const form = document.querySelector('#search-form');
  const input = document.querySelector('#query');
  const status = document.querySelector('#search-status');
  const results = document.querySelector('#results');
  let index;
  let generation = 0;
  async function search() {
    const current = ++generation;
    const query = input.value.trim();
    results.replaceChildren();
    if (!query) { status.textContent = '输入关键词，查找文章。'; return; }
    status.textContent = '正在搜索…';
    try {
      if (!index) { const response = await fetch(script.dataset.index); if (!response.ok) throw new Error('index'); index = await response.json(); }
      if (current !== generation) return;
      const words = query.toLocaleLowerCase().split(/\s+/);
      const found = index.filter(item => words.every(word => (item.title + ' ' + item.content).toLocaleLowerCase().includes(word)));
      status.textContent = found.length ? `找到 ${found.length} 篇文章` : '没有找到匹配的文章，请尝试其他关键词。';
      for (const item of found) {
        const article = document.createElement('article'); article.className = 'post-card';
        const heading = document.createElement('h2'); const link = document.createElement('a');
        link.href = item.url; link.textContent = item.title; heading.append(link);
        const summary = document.createElement('p'); summary.textContent = item.content.slice(0, 160) + '…';
        article.append(heading, summary); results.append(article);
      }
    } catch (_) { if (current === generation) status.textContent = '搜索索引加载失败，请稍后重试。'; }
  }
  form.addEventListener('submit', event => { event.preventDefault(); const url = new URL(location.href); url.searchParams.set('q', input.value); history.replaceState(null, '', url); search(); });
  input.value = new URLSearchParams(location.search).get('q') || '';
  if (input.value) search();
})();
