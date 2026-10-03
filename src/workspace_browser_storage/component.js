export default function({data,parentElement,setStateValue}) {
  const prefix = 'flipfynd.workspace.v1.';
  const valid = t => /^[a-f0-9]{32}$/.test(t || '');
  const parent=window, args=data||{};
  let token='', doc=null, timer;
  const scheduleDrafts=()=>{clearTimeout(timer);timer=setTimeout(drafts,250);};
  const visibilityDrafts=()=>{if(doc.hidden) drafts();};
  const names = {'Säljare (valfritt)':'seller_top5_alias','Tradera-profil':'seller_top5_profile_url',
    'Sök spelare, set eller kort':'search_text','Budget – max totalpris inkl. frakt':'search_budget',
    'Sport':'search_sport','Annonsform':'search_sale_type','Korttyp':'ordinary_card_type_filter',
    'Ta med äldre sparade annonser':'search_archive','Visa även svaga kandidater':'search_show_skip',
    'Minsta analyssäkerhet':'search_minimum_confidence','Antal fynd att visa':'search_show_count',
    'Visa fördjupad analys':'show_advanced_terminal'};
  function drafts() {
    if (!doc || !valid(token)) return;
    try {
      const widgets={};
      for (const box of doc.querySelectorAll('[data-testid="stTextInput"], [data-testid="stNumberInput"], [data-testid="stSelectbox"], [data-testid="stCheckbox"], [data-testid="stSlider"], [data-testid="stRadio"]')) {
        const label=box.querySelector('label')?.textContent?.trim();
        const key=names[label], input=box.querySelector('input:checked') || box.querySelector('input');
        if (key && input) {
          let value=input.value;
          if (input.type==='checkbox') value=input.checked;
          else if(input.type==='radio') value=input.closest('label')?.textContent?.trim();
          else if(['search_budget','search_show_count','search_minimum_confidence'].includes(key)) value=Number(value);
          if (value!==undefined && (typeof value!=='number' || Number.isFinite(value))) widgets[key]=value;
        }
      }
      localStorage.setItem(prefix+token+'.drafts', JSON.stringify({at:Date.now()/1000,widgets}));
    } catch (_) {}
  }
  try {
    doc=parent.document;
    doc.addEventListener('input',scheduleDrafts,true);
    doc.addEventListener('change',scheduleDrafts,true);
    doc.addEventListener('visibilitychange',visibilityDrafts);
    parent.addEventListener('pagehide',drafts);
  } catch (_) {} // Restricted browser storage must not prevent server recovery.

  let reply={token:'',blob:''};
  try {
    token=valid(args.token) ? args.token : localStorage.getItem(prefix+'latest');
    if(valid(token)) {
      if(args.blob) {
        localStorage.setItem(prefix+token,args.blob);
        localStorage.setItem(prefix+'latest',token);
        // Do not discard another open tab's recovery record.
      }
      reply={token,blob:localStorage.getItem(prefix+token)||'',
        drafts:JSON.parse(localStorage.getItem(prefix+token+'.drafts')||'null')};
    }
  } catch (_) {reply={token:args.token||'',error:'STORAGE_UNAVAILABLE'};}
  // Recovery is a handshake, not a notification for each saved snapshot.
  // Echoing a new blob/draft makes Streamlit rerun the entire app.
  const requestToken=args.token||'';
  if(args.hydrated) parentElement.dataset.repliedFor=requestToken;
  if(requestToken!==parentElement.dataset.repliedFor) {
    parentElement.dataset.repliedFor=requestToken;
    setStateValue('reply',reply);
  }
  return () => {
    clearTimeout(timer);
    if(doc) {
      doc.removeEventListener('input',scheduleDrafts,true);
      doc.removeEventListener('change',scheduleDrafts,true);
      doc.removeEventListener('visibilitychange',visibilityDrafts);
    }
    parent.removeEventListener('pagehide',drafts);
  };
}
