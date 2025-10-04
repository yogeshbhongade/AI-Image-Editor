// downloads.js: AJAX pagination, stats, and filtering for download history

function setThumbBackgrounds() {
  document.querySelectorAll('.thumb-square[data-bg-url]').forEach(el => {
    const url = el.getAttribute('data-bg-url');
    if (url) {
      el.style.backgroundImage = `url('${url}')`;
    } else {
      el.style.backgroundImage = '';
    }
  });
}

// HTML escape helper
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

document.addEventListener('DOMContentLoaded', function() {
  // Example: fetch stats and render
  fetch('/downloads/stats')
    .then(r => r.json())
    .then(data => {
      const statsDiv = document.getElementById('download-stats');
      if (statsDiv && data.total !== undefined) {
        statsDiv.innerHTML = `<h3>Total Downloads: ${data.total}</h3>`;
        if (data.file_types) {
          statsDiv.innerHTML += '<ul>' + data.file_types.map(ft => `<li>${ft._id}: ${ft.count}</li>`).join('') + '</ul>';
        }
      }
    })
    .catch(err => {
      console.error('Failed to load stats:', err);
      const statsDiv = document.getElementById('download-stats');
      if (statsDiv) statsDiv.innerHTML = '<div class="alert alert-danger">Failed to load stats. Please try again later.</div>';
    });

  setThumbBackgrounds();
  // Guard initial AJAX load
  const cardMain = document.querySelector('.Card-main[data-ajax-init="true"]');
  if (cardMain) {
    const search = document.getElementById('download-search')?.value || '';
    const start = document.getElementById('download-start')?.value || '';
    const end = document.getElementById('download-end')?.value || '';
    fetchDownloads(1, 10, search, start, end);
  }

  // Pagination click handler
  document.body.addEventListener('click', function(e) {
    if (e.target.matches('.downloads-pagination a[data-page]')) {
      e.preventDefault();
      const page = parseInt(e.target.getAttribute('data-page'));
      const query = document.getElementById('download-search')?.value || '';
      const start = document.getElementById('download-start')?.value || '';
      const end = document.getElementById('download-end')?.value || '';
      fetchDownloads(page, 10, query, start, end);
    }
  });

  // Search and date filter handler
  document.body.addEventListener('input', function(e) {
    if (["download-search", "download-start", "download-end"].includes(e.target.id)) {
      const query = document.getElementById('download-search')?.value || '';
      const start = document.getElementById('download-start')?.value || '';
      const end = document.getElementById('download-end')?.value || '';
      fetchDownloads(1, 10, query, start, end);
    }
  });

  // Export handler
  document.body.addEventListener('click', function(e) {
    if (e.target.id === 'download-export') {
      const query = document.getElementById('download-search')?.value || '';
      const start = document.getElementById('download-start')?.value || '';
      const end = document.getElementById('download-end')?.value || '';
      let url = '/downloads/export';
      let params = [];
      if (query) params.push(`q=${encodeURIComponent(query)}`);
      if (start) params.push(`start=${encodeURIComponent(start)}`);
      if (end) params.push(`end=${encodeURIComponent(end)}`);
      if (params.length) url += '?' + params.join('&');
      window.location = url;
    }
  });
});

// --- AJAX Pagination, Search/Filter, Export ---
function renderDownloads(downloads) {
  const cardMain = document.querySelector('.Card-main');
  if (!cardMain) return;
  if (!downloads.length) {
    cardMain.innerHTML = '<div class="alert alert-info">No download history found.</div>';
    return;
  }
  // Get processed image URL template from root
  const tpl = document.getElementById('downloads-root')?.dataset.processedTemplate || '';
  cardMain.innerHTML = downloads.map(d => {
    const url = tpl.replace('__FILENAME__', encodeURIComponent(d.filename));
    return `
      <div class="d-card">
        <div class="thumb-square" data-bg-url="${url}">
          <noscript><img src="${url}" alt="${esc(d.filename)}" style="width:100%;height:180px;object-fit:cover;" /></noscript>
        </div>
        <div class="downloads-card-content mt-2">
          <p class="p">${esc(d.filename)}</p>
          <p class="small">Downloaded on ${esc(d.download_timestamp || '')}</p>
          <p class="small">Type: ${esc(d.file_type)}, Size: ${d.file_size || 0} bytes</p>
        </div>
      </div>
    `;
  }).join('');
  setThumbBackgrounds();
}

function renderPagination(page, per_page, total) {
  const pagDiv = document.querySelector('.downloads-pagination');
  if (!pagDiv) return;
  let html = '';
  if (page > 1) {
    html += `<a href="#" data-page="${page-1}">&laquo; Prev</a>`;
  }
  html += `<span>Page ${page}</span>`;
  if ((page * per_page) < total) {
    html += `<a href="#" data-page="${page+1}">Next &raquo;</a>`;
  }
  pagDiv.innerHTML = html;
}

function fetchDownloads(page=1, per_page=10, query='', start='', end='') {
  let url = `/downloads/history?page=${page}&per_page=${per_page}`;
  if (query) url += `&q=${encodeURIComponent(query)}`;
  if (start) url += `&start=${encodeURIComponent(start)}`;
  if (end) url += `&end=${encodeURIComponent(end)}`;
  fetch(url)
    .then(r => r.json())
    .then(data => {
      renderDownloads(data.downloads);
      renderPagination(data.page, data.per_page, data.total);
    })
    .catch(err => {
      console.error('Failed to load downloads:', err);
      const cardMain = document.querySelector('.Card-main');
      if (cardMain) cardMain.innerHTML = '<div class="alert alert-danger">Failed to load downloads. Please try again later.</div>';
    });
}
