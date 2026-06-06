(function () {
  const grid = document.getElementById("postGrid");
  const searchForm = document.getElementById("searchForm");
  const searchInput = document.getElementById("searchInput");
  const likeButton = document.getElementById("likeButton");
  const commentForm = document.getElementById("commentForm");
  const commentList = document.getElementById("commentList");

  const reader = {
    slug: null,
    tag: document.getElementById("readerTag"),
    date: document.getElementById("readerDate"),
    title: document.getElementById("readerTitle"),
    content: document.getElementById("readerContent"),
    stats: document.getElementById("readerStats")
  };

  const stats = {
    views: document.getElementById("statViews"),
    likes: document.getElementById("statLikes"),
    comments: document.getElementById("statComments"),
    requests: document.getElementById("statRequests"),
    avg: document.getElementById("statAvg")
  };

  async function api(path, options) {
    const response = await fetch(path, Object.assign({
      headers: { "Content-Type": "application/json" }
    }, options || {}));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  }

  function renderPosts(posts) {
    grid.innerHTML = posts.map((post) => `
      <article class="post-card" data-slug="${post.slug}">
        <div class="post-meta">
          <span>${post.tag}</span>
          <time>${post.date}</time>
        </div>
        <h3>${post.title}</h3>
        <p>${post.summary}</p>
        <div class="card-stats">
          <span>${post.views || 0} 阅读</span>
          <span>${post.likes || 0} 点赞</span>
          <span>${post.comments || 0} 评论</span>
        </div>
      </article>
    `).join("");

    Array.from(grid.querySelectorAll(".post-card")).forEach((card) => {
      card.addEventListener("click", () => loadPost(card.dataset.slug));
    });
  }

  async function loadPosts() {
    const data = await api("/api/posts");
    renderPosts(data.posts);
    if (data.posts.length && !reader.slug) {
      await loadPost(data.posts[0].slug);
    }
  }

  async function loadPost(slug) {
    const data = await api(`/api/posts/${encodeURIComponent(slug)}`);
    const post = data.post;
    reader.slug = post.slug;
    reader.tag.textContent = post.tag;
    reader.date.textContent = post.date;
    reader.title.textContent = post.title;
    reader.content.textContent = post.content;
    reader.stats.textContent = `阅读 ${post.views} 次 / 点赞 ${post.likes} 次`;
    await loadComments(post.slug);
    await refreshStats();
  }

  async function loadComments(slug) {
    const data = await api(`/api/posts/${encodeURIComponent(slug)}/comments`);
    if (!data.comments.length) {
      commentList.innerHTML = `<p class="empty">还没有评论。</p>`;
      return;
    }
    commentList.innerHTML = data.comments.map((item) => `
      <div class="comment">
        <strong>${item.name}</strong>
        <time>${item.created_at}</time>
        <p>${item.message}</p>
      </div>
    `).join("");
  }

  async function refreshStats() {
    const data = await api("/api/stats");
    stats.views.textContent = data.views;
    stats.likes.textContent = data.likes;
    stats.comments.textContent = data.comments;
    stats.requests.textContent = data.requests;
    stats.avg.textContent = data.avg_ms;
  }

  searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const q = searchInput.value.trim();
    const data = await api(`/api/search?q=${encodeURIComponent(q)}`);
    renderPosts(data.posts);
  });

  likeButton.addEventListener("click", async () => {
    if (!reader.slug) return;
    await api(`/api/posts/${encodeURIComponent(reader.slug)}/like`, { method: "POST", body: "{}" });
    await loadPost(reader.slug);
    await loadPosts();
  });

  commentForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!reader.slug) return;
    const name = document.getElementById("commentName").value.trim() || "访客";
    const message = document.getElementById("commentMessage").value.trim();
    if (!message) return;
    await api(`/api/posts/${encodeURIComponent(reader.slug)}/comments`, {
      method: "POST",
      body: JSON.stringify({ name, message })
    });
    document.getElementById("commentMessage").value = "";
    await loadComments(reader.slug);
    await loadPosts();
    await refreshStats();
  });

  loadPosts().catch(() => {
    grid.innerHTML = `<p class="empty">文章加载失败，请稍后刷新。</p>`;
  });
  refreshStats().catch(() => {});
  setInterval(() => refreshStats().catch(() => {}), 8000);
})();
