"""Exercise the real browser timer without waiting or a Streamlit rerun."""
from pathlib import Path
import shutil
import subprocess
import pytest


def test_loading_timer_tracks_busy_completion_and_measured_history():
    if not shutil.which('node'):
        pytest.skip('Node required for component regression')
    path = Path(__file__).resolve().parents[1] / 'src/loading_status_component/index.html'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let now=10000,running=true,tick,box;
const storage=new Map([['flipfynd.open-times.v1','[12,14,16]']]);
const messages=[];
const parent={performance:{timeOrigin:0},postMessage:m=>messages.push(m),
sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
document:{createElement:()=>({style:{},setAttribute:()=>{},remove:()=>{}}),
getElementById:()=>null,body:{appendChild:x=>box=x},querySelector:()=>running?{}:null}};
parent.performance.timeOrigin=1000;
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8').split('<script>')[1].split('</script>')[0],
{parent,Date:{now:()=>now},addEventListener:()=>{},setInterval:f=>{tick=f;return 1;},clearInterval:()=>{}});
assert(box.textContent.includes('9 s'));
assert(box.textContent.includes('cirka 14 s'));
now=18000;tick();assert(box.textContent.includes('längre tid'));
running=false;tick();assert(box.textContent.includes('klar'));
assert.equal(JSON.parse(storage.get('flipfynd.open-times.v1')).at(-1),17);
now=24000;tick();assert.equal(box.style.display,'none');
running=true;tick();now=27000;tick();
assert(box.textContent.includes('Uppdaterar vyn · 3 s'));
assert(!box.textContent.includes('cirka'),'startup estimate must not describe another operation');
assert(!messages.some(m=>m.type==='streamlit:setComponentValue'),'timer must not cause reruns');
'''
    subprocess.run(['node', '-e', script, str(path)], check=True, capture_output=True, text=True)
