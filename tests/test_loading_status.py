"""Exercise the real browser timer without waiting or a Streamlit rerun."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_loading_timer_tracks_busy_completion_and_measured_history():
    if not shutil.which('node'):
        pytest.skip('Node required for component regression')
    path = Path(__file__).resolve().parents[1] / 'src/loading_status_component/component.js'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let now=10000,running=true,tick,box,removed=0,cleared=0;
const parentElement={};
const storage=new Map([['flipfynd.open-times.v1','[12,14,16]']]);
const messages=[];
const parent={performance:{timeOrigin:0},postMessage:m=>messages.push(m),
sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
document:{createElement:()=>({style:{},setAttribute:()=>{},remove:()=>removed++}),
getElementById:()=>null,body:{appendChild:x=>box=x},querySelector:()=>running?{}:null}};
parent.performance.timeOrigin=1000;
const context={window:parent,Date:{now:()=>now},setInterval:f=>{tick=f;return 1;},clearInterval:()=>cleared++};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8').replace('export default function','function mount'),context);
let cleanup=context.mount({parentElement});
assert(box.textContent.includes('9 s'));
assert(box.textContent.includes('cirka 14 s'));
now=18000;tick();assert(box.textContent.includes('längre tid'));
running=false;tick();assert(box.textContent.includes('Vyn har uppdaterats'));
assert(!box.textContent.includes('klar'), 'view completion must not claim that background search finished');
assert.equal(JSON.parse(storage.get('flipfynd.open-times.v1')).at(-1),17);
now=24000;tick();assert.equal(box.style.display,'none');
running=true;tick();now=27000;tick();
assert(box.textContent.includes('Uppdaterar vyn · 3 s'));
assert(!box.textContent.includes('cirka'),'startup estimate must not describe another operation');
cleanup();assert.equal(cleared,1);assert.equal(removed,1);
cleanup=context.mount({parentElement});
now=28000;tick();assert(box.textContent.includes('Uppdaterar vyn · 4 s'), 'rerender preserves the active clock');
cleanup();assert.equal(cleared,2);assert.equal(removed,2);
assert.equal(messages.length,0,'timer must not cause reruns');
'''
    subprocess.run(['node', '-e', script, str(path)], check=True, capture_output=True, text=True)
