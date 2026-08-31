// Paste into javascript_tool on an open, logged-in app.vts.com tab.
// Read-only: it fetches nothing but GETs and writes nothing to VTS.
// Returns everything vts-config.json needs for this user's account.
// NOTE: the leading `await` matters — without it javascript_tool returns an
// unresolved Promise instead of the result.
await (async () => {
  const H = {'Accept':'application/json','X-Requested-With':'XMLHttpRequest'};
  const out = {ok:false, errors:[]};

  // --- who am I -------------------------------------------------------
  // The page bootstraps a global `vts` object; user + reference data both live there.
  const v = window.vts;
  if (!v || !v.user) {
    out.errors.push('window.vts.user missing — not signed in, or not on an app.vts.com page.');
    return out;
  }
  const u = v.user;
  out.user = {id:u.id, name:u.name, first_name:u.first_name, last_name:u.last_name,
              email:u.email, account_id:u.account_id, persona:u.persona,
              accounts:(u.accounts||[]).map(a=>({id:a.id,name:a.name}))};

  // --- taxonomy ids ---------------------------------------------------
  // Platform-level, but re-read rather than trusted so a changed id surfaces here
  // instead of as a silently mis-filed deal.
  const rd = v.reference_data || {};
  const byName = (list, want) =>
    (list||[]).find(x => (x.name||x.reason||'').toLowerCase() === want) || null;

  const retail = byName(rd.tenant_industries, 'retail (general)');
  const dealNew = byName(rd.deal_types, 'new');
  out.ids = {
    tenant_industry_retail_general: retail ? retail.id : null,
    deal_type_id: dealNew ? dealNew.id : null,
    dead_deal_reasons: Object.fromEntries(
      (rd.dead_deal_reasons||[]).map(r => [r.reason, r.id])),
    deal_stages: Object.fromEntries(
      (rd.deal_stages||[]).map(s => [s.status, s.display_name])),
  };
  if (!out.ids.tenant_industry_retail_general) out.errors.push("no 'retail (general)' industry on this account");
  if (!out.ids.dead_deal_reasons.requirement_dead) out.errors.push("no 'requirement_dead' dead-deal reason on this account");

  // --- every property this user can see --------------------------------
  try {
    let page = 1, props = [];
    while (true) {
      const r = await fetch(`/api/horse/properties?page=${page}&page_size=100`,
                            {headers:H, credentials:'same-origin'});
      if (!r.ok) { out.errors.push(`properties page ${page} -> HTTP ${r.status}`); break; }
      const j = await r.json();
      props = props.concat(j.properties || []);
      if (page >= (j.num_pages || 1)) break;
      page++;
    }
    out.properties = props.map(p => ({
      id: p.id,
      name: p.name || p.property_name || p.display_name_short,
      city_state: p.city_state || null,
    })).sort((a,b) => (a.name||'').localeCompare(b.name||''));
  } catch (e) {
    out.errors.push('properties fetch failed: ' + String(e));
    out.properties = [];
  }

  out.ok = out.errors.length === 0;
  return out;
})();
