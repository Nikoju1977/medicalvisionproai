/* MedVision Web Knowledge UI — manual research reference explorer. */
(function () {
  'use strict';

  function esc(v) {
    return String(v || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function refLink(item) {
    if (item.pmid) return 'https://pubmed.ncbi.nlm.nih.gov/' + encodeURIComponent(item.pmid) + '/';
    if (item.doi) return 'https://doi.org/' + encodeURIComponent(item.doi);
    if (item.nct) return 'https://clinicaltrials.gov/study/' + encodeURIComponent(item.nct);
    return '';
  }

  function mount() {
    if (!window.MedVisionKnowledge || document.getElementById('mv-web-knowledge-btn')) return;

    const style = document.createElement('style');
    style.textContent = `
      #mv-web-knowledge-btn{position:fixed;right:16px;bottom:16px;z-index:2147483000;border:0;border-radius:999px;padding:10px 14px;font:600 13px system-ui;box-shadow:0 8px 30px rgba(0,0,0,.22);cursor:pointer}
      #mv-web-knowledge-panel{position:fixed;inset:0;z-index:2147483001;background:rgba(0,0,0,.62);display:none;align-items:center;justify-content:center;padding:16px}
      #mv-web-knowledge-panel[data-open="1"]{display:flex}
      #mv-web-knowledge-card{width:min(760px,100%);max-height:88vh;overflow:auto;background:#fff;color:#111;border-radius:16px;padding:18px;box-shadow:0 20px 80px rgba(0,0,0,.35);font:14px/1.45 system-ui}
      #mv-web-knowledge-card h2{margin:0 0 8px;font-size:20px}
      #mv-web-knowledge-form{display:flex;gap:8px;margin:12px 0}
      #mv-web-knowledge-topic{flex:1;min-width:0;padding:10px 12px;border:1px solid #bbb;border-radius:10px}
      #mv-web-knowledge-form button,#mv-web-knowledge-close{padding:10px 12px;border:0;border-radius:10px;cursor:pointer}
      .mvwk-ref{padding:12px 0;border-top:1px solid #e5e5e5}
      .mvwk-meta{font-size:12px;opacity:.72;margin:4px 0}
      .mvwk-summary{margin-top:6px}
      .mvwk-note{font-size:12px;opacity:.72}
    `;
    document.head.appendChild(style);

    const button = document.createElement('button');
    button.id = 'mv-web-knowledge-btn';
    button.type = 'button';
    button.textContent = 'Sources web';

    const panel = document.createElement('div');
    panel.id = 'mv-web-knowledge-panel';
    panel.innerHTML = `
      <section id="mv-web-knowledge-card" role="dialog" aria-modal="true" aria-labelledby="mv-web-knowledge-title">
        <button id="mv-web-knowledge-close" type="button" style="float:right">Fermer</button>
        <h2 id="mv-web-knowledge-title">Références médicales web</h2>
        <p class="mvwk-note">Recherche documentaire manuelle dans Europe PMC/PubMed et ClinicalTrials.gov. Les résultats sont du contexte de recherche, pas une conclusion clinique.</p>
        <form id="mv-web-knowledge-form">
          <input id="mv-web-knowledge-topic" autocomplete="off" placeholder="Ex. pneumothorax radiographie thoracique" aria-label="Sujet de recherche">
          <button type="submit">Rechercher</button>
        </form>
        <div id="mv-web-knowledge-status" class="mvwk-note"></div>
        <div id="mv-web-knowledge-results"></div>
      </section>`;

    document.body.appendChild(button);
    document.body.appendChild(panel);

    const close = () => { panel.dataset.open = '0'; };
    button.addEventListener('click', () => {
      panel.dataset.open = '1';
      setTimeout(() => document.getElementById('mv-web-knowledge-topic').focus(), 0);
    });
    panel.addEventListener('click', e => { if (e.target === panel) close(); });
    document.getElementById('mv-web-knowledge-close').addEventListener('click', close);

    document.getElementById('mv-web-knowledge-form').addEventListener('submit', async e => {
      e.preventDefault();
      const topic = document.getElementById('mv-web-knowledge-topic').value;
      const status = document.getElementById('mv-web-knowledge-status');
      const results = document.getElementById('mv-web-knowledge-results');
      status.textContent = 'Recherche des références…';
      results.innerHTML = '';
      try {
        const data = await window.MedVisionKnowledge.search({ topic });
        status.textContent = data.references.length + ' référence(s) — ' + new Date(data.retrieved_at).toLocaleString();
        results.innerHTML = data.references.map(item => {
          const url = refLink(item);
          const ids = [item.pmid && ('PMID ' + item.pmid), item.doi && ('DOI ' + item.doi), item.nct && item.nct].filter(Boolean).join(' · ');
          return `<article class="mvwk-ref"><strong>${esc(item.title || 'Sans titre')}</strong><div class="mvwk-meta">${esc(item.source)}${item.year ? ' · ' + esc(item.year) : ''}${ids ? ' · ' + esc(ids) : ''}${item.status ? ' · ' + esc(item.status) : ''}</div>${item.summary ? `<div class="mvwk-summary">${esc(item.summary)}</div>` : ''}${url ? `<div><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Ouvrir la source</a></div>` : ''}</article>`;
        }).join('') || '<p>Aucune référence trouvée.</p>';
      } catch (err) {
        status.textContent = 'Recherche indisponible pour le moment.';
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
