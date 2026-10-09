export default function({parentElement}) {
  const parent=window;
  try {
    const doc=parent.document;
    const box=doc.createElement('div');
    box.id='flipfynd-loading-status';
    box.setAttribute('role','status');
    // The seconds change without repeated screen-reader announcements.
    box.setAttribute('aria-live','off');
    Object.assign(box.style,{position:'fixed',top:'64px',left:'16px',right:'16px',
      zIndex:'100000',padding:'10px 14px',background:'#21252c',color:'#f4ead7',
      border:'1px solid #ed7634',borderRadius:'8px',font:'14px system-ui',
      pointerEvents:'none',display:'none',boxShadow:'0 3px 12px #0006'});
    doc.getElementById(box.id)?.remove();
    doc.body.appendChild(box);
    const key='flipfynd.open-times.v1';
    let samples=[];
    try {samples=JSON.parse(parent.sessionStorage.getItem(key)||'[]')
      .filter(n=>Number.isFinite(n)&&n>0&&n<300).slice(-5);} catch(_){}
    const estimate=samples.length>=3 ? [...samples].sort((a,b)=>a-b)[Math.floor(samples.length/2)] : null;
    const clock=parentElement._flipfyndClock ||
      (parentElement._flipfyndClock={first:true,started:null,finished:null});
    function tick() {
      const running=!!doc.querySelector('[data-testid="stStatusWidgetRunningIcon"]');
      const now=Date.now();
      if(running) {
        if(clock.started===null) {
          clock.started=clock.first ? (parent.performance?.timeOrigin||now) : now;
          clock.finished=null;
        }
        const seconds=Math.max(0,(now-clock.started)/1000);
        box.style.display=seconds>=1?'block':'none';
        let detail='Återstående tid är ännu okänd.';
        if(clock.first && estimate!==null) detail=seconds<estimate
          ? `Tidigare öppningar tog cirka ${Math.round(estimate)} s totalt.`
          : 'Tar längre tid än tidigare. Återstående tid är okänd.';
        box.textContent=`${clock.first?'Laddar Flipfynd':'Uppdaterar vyn'} · ${Math.floor(seconds)} s. ${detail}`;
      } else if(clock.started!==null) {
        const seconds=(now-clock.started)/1000;
        if(clock.first) {
          samples.push(seconds);
          try {parent.sessionStorage.setItem(key,JSON.stringify(samples.slice(-5)));} catch(_){}
        }
        clock.first=false; clock.started=null; clock.finished=now;
        box.textContent=`Vyn har uppdaterats · ${Math.round(seconds)} s`;
        box.style.display=seconds>=1?'block':'none';
      } else if(clock.finished!==null && now-clock.finished>5000) box.style.display='none';
    }
    tick();
    const timer=setInterval(tick,250);
    return () => {clearInterval(timer);box.remove();};
  } catch(_) {} // The timing helper must never block the app.
}
