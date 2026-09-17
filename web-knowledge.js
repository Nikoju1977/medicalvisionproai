/* MedVision Web Knowledge — research references only.
   This module retrieves public biomedical references and registry records.
   It does not make diagnoses or treatment recommendations. */
(function (global) {
  'use strict';

  const cache = new Map();
  const TTL = 10 * 60 * 1000;

  function cleanTopic(value) {
    return String(value || '')
      .replace(/https?:\/\/\S+/gi, ' ')
      .replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g, ' ')
      .replace(/\b\d{4,}\b/g, ' ')
      .replace(/[<>\[\]{}]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 180);
  }

  async function fetchJson(url, timeoutMs) {
    const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const timer = ctl ? setTimeout(() => ctl.abort(), timeoutMs || 8000) : null;
    try {
      const response = await fetch(url, {
        method: 'GET', mode: 'cors', credentials: 'omit', signal: ctl ? ctl.signal : undefined
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return await response.json();
    } finally {
      if (timer) clearTimeout(timer);
    }
  }

  async function searchEuropePmc(topic) {
    const query = '(' + topic.replace(/[():\[\]\"]/g, ' ') + ') AND SRC:MED';
    const url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + new URLSearchParams({
      query, format: 'json', resultType: 'core', pageSize: '6', sort: 'P_PDATE_D desc', synonym: 'true'
    }).toString();
    try {
      const data = await fetchJson(url, 8000);
      const rows = (((data || {}).resultList || {}).result || []).slice(0, 6);
      return rows.map(r => ({
        source: 'Europe PMC / PubMed',
        kind: 'publication',
        title: String(r.title || '').slice(0, 300),
        year: String(r.pubYear || (r.firstPublicationDate || '').slice(0, 4) || ''),
        journal: String(r.journalTitle || '').slice(0, 120),
        pmid: String(r.pmid || ''),
        doi: String(r.doi || ''),
        summary: String(r.abstractText || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').slice(0, 900)
      }));
    } catch (error) {
      return [];
    }
  }

  async function searchClinicalTrials(topic) {
    const url = 'https://clinicaltrials.gov/api/v2/studies?' + new URLSearchParams({
      'query.term': topic, pageSize: '4', format: 'json'
    }).toString();
    try {
      const data = await fetchJson(url, 8000);
      const studies = Array.isArray(data && data.studies) ? data.studies : [];
      return studies.slice(0, 4).map(study => {
        const ps = study && study.protocolSection || {};
        const id = ps.identificationModule || {};
        const status = ps.statusModule || {};
        const desc = ps.descriptionModule || {};
        return {
          source: 'ClinicalTrials.gov',
          kind: 'trial_registry',
          title: String(id.briefTitle || id.officialTitle || '').slice(0, 300),
          nct: String(id.nctId || ''),
          status: String(status.overallStatus || ''),
          year: String(status.startDateStruct && status.startDateStruct.date || '').slice(0, 4),
          summary: String(desc.briefSummary || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').slice(0, 900)
        };
      });
    } catch (error) {
      return [];
    }
  }

  async function search(input) {
    const topic = cleanTopic(input && input.topic);
    if (!topic) return { topic: '', retrieved_at: new Date().toISOString(), references: [] };
    const key = topic.toLowerCase();
    const hit = cache.get(key);
    if (hit && Date.now() - hit.at < TTL) return hit.value;

    const parts = await Promise.all([searchEuropePmc(topic), searchClinicalTrials(topic)]);
    const seen = new Set();
    const references = [].concat(parts[0], parts[1]).filter(item => {
      const id = item.pmid || item.doi || item.nct || item.title;
      const k = String(id || '').toLowerCase();
      if (!k || seen.has(k)) return false;
      seen.add(k);
      return true;
    });
    const value = {
      topic,
      retrieved_at: new Date().toISOString(),
      references,
      notice: 'Research context only. Registry records and article abstracts are not clinical conclusions.'
    };
    cache.set(key, { at: Date.now(), value });
    return value;
  }

  global.MedVisionKnowledge = Object.freeze({ search, cleanTopic });
})(window);
