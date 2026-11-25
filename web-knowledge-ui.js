/* MedVision Web Knowledge UI — manual research reference explorer. */
(function () {
  'use strict';

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
        <label class="mvwk-note"><input id="mv-web-knowledge-consent" type="checkbox"> Je confirme que la recherche ne contient aucune donnée personnelle ou de santé identifiable. Le sujet sera envoyé aux bases documentaires externes.</label>
        <div id="mv-web-knowledge-status" class="mvwk-note" role="status" aria-live="polite"></div>
        <div id="mv-web-knowledge-results"></div>
      </section>`;

    document.body.appendChild(button);
    document.body.appendChild(panel);

    let generation = 0;
    const consent = document.getElementById('mv-web-knowledge-consent');
    const close = () => { generation++; panel.dataset.open = '0'; consent.checked = false; button.focus(); };
    panel.addEventListener('keydown', e=>{if(e.key==='Escape'){e.preventDefault();close();}});
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
      if (!consent.checked) { status.textContent = 'Confirmez l’absence de données identifiantes avant la recherche.'; return; }
      if (!window.MedVisionKnowledge.cleanTopic(topic)) { status.textContent = 'Saisissez un sujet documentaire général.'; return; }
      consent.checked=false;
      const request=++generation;
      status.textContent = 'Recherche des références…';
      results.textContent = '';
      try {
        const data = await window.MedVisionKnowledge.search({ topic });
        if(request!==generation)return;
        const unavailable=(data.sources||[]).filter(s=>s.status==='unavailable');
        status.textContent = unavailable.length===2?'Les deux sources sont indisponibles. Aucun résultat ne peut être conclu.':data.references.length+' référence(s) — '+new Date(data.retrieved_at).toLocaleString()+(unavailable.length?' · Recherche partielle : '+unavailable.map(s=>s.name).join(', ')+' indisponible.':'');
        for(const item of data.references){
          const article=document.createElement('article');article.className='mvwk-ref';
          const title=document.createElement('strong');title.textContent=item.title||'Sans titre';article.appendChild(title);
          const ids=[item.pmid&&('PMID '+item.pmid),item.doi&&('DOI '+item.doi),item.nct].filter(Boolean).join(' · ');
          const meta=document.createElement('div');meta.className='mvwk-meta';meta.textContent=[item.source,item.year,ids,item.status].filter(Boolean).join(' · ');article.appendChild(meta);
          if(item.summary){const summary=document.createElement('div');summary.className='mvwk-summary';summary.textContent=item.summary;article.appendChild(summary);}
          const url=refLink(item);if(url){const a=document.createElement('a');a.href=url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Ouvrir la source';article.appendChild(a);}
          results.appendChild(article);
        }
        if(!data.references.length&&!unavailable.length){const p=document.createElement('p');p.textContent='Aucune référence trouvée.';results.appendChild(p);}
      } catch (err) {
        if(request===generation)status.textContent = 'Recherche indisponible pour le moment.';
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
