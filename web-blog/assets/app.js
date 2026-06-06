(function () {
  const grid = document.getElementById("postGrid");
  const posts = window.BLOG_POSTS || [];

  grid.innerHTML = posts.map((post) => `
    <article class="post-card">
      <div class="post-meta">
        <span>${post.tag}</span>
        <time>${post.date}</time>
      </div>
      <h3>${post.title}</h3>
      <p>${post.summary}</p>
    </article>
  `).join("");
})();
