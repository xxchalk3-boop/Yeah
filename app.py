#!/usr/bin/env python3
"""
chalkobusf web UI — browser interface for the NewtonScript obfuscator.

No extra dependencies required (uses Python's built-in http.server).

Usage:
  python3 app.py              # opens http://127.0.0.1:5000
  python3 app.py --port 8080
  python3 app.py --host 0.0.0.0 --port 8080  # expose on local network
  python3 app.py --no-browser                 # don't auto-open browser tab
"""

import json
import argparse
import sys
import os
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import _Chalkobusf

# ── embedded single-page app ──────────────────────────────────────────────────

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>chalkobusf — NewtonScript Obfuscator</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg:      #0d1117;
  --surface: #161b22;
  --border:  #30363d;
  --text:    #e6edf3;
  --muted:   #8b949e;
  --accent:  #58a6ff;
  --green:   #3fb950;
  --orange:  #f0883e;
  --red:     #f85149;
  --output:  #a5d6ff;
}
html, body { height: 100%; }
body { font-family: ui-monospace,'Cascadia Code','Courier New',monospace;
       background: var(--bg); color: var(--text);
       display: flex; flex-direction: column; overflow: hidden; }

/* header */
header { background: var(--surface); border-bottom: 1px solid var(--border);
         padding: 9px 20px; display: flex; align-items: center; gap: 14px;
         flex-shrink: 0; }
.logo  { font-size: 15px; font-weight: 700; color: var(--accent); letter-spacing: .3px; }
.logo span { color: var(--muted); font-weight: 400; font-size: 12px; margin-left: 8px; }
.hlinks { margin-left: auto; display: flex; gap: 10px; }
.hlink  { font-size: 11px; color: var(--muted); text-decoration: none; }
.hlink:hover { color: var(--accent); }

/* toolbar */
.toolbar { background: var(--surface); border-bottom: 1px solid var(--border);
           padding: 7px 20px; display: flex; align-items: center; gap: 10px;
           flex-wrap: wrap; flex-shrink: 0; }
.presets { display: flex; gap: 5px; }
.pbtn { background: #21262d; border: 1px solid var(--border); color: var(--text);
        padding: 4px 11px; border-radius: 5px; cursor: pointer; font-size: 12px;
        font-family: inherit; }
.pbtn:hover { background: #2d333b; }
.pbtn.on    { background: #1f6feb; border-color: var(--accent); }
.vbar  { width: 1px; background: var(--border); align-self: stretch; margin: 0 2px; }
.passes { display: flex; gap: 6px; flex-wrap: wrap; flex: 1; min-width: 0; }
.cb { display: flex; align-items: center; gap: 4px; font-size: 11px;
      color: var(--muted); cursor: pointer; user-select: none; white-space: nowrap; }
.cb:hover { color: var(--text); }
.cb input { accent-color: var(--accent); cursor: pointer; }
.go { background: #238636; border: 1px solid #2ea043; color: #fff;
      padding: 5px 18px; border-radius: 5px; cursor: pointer;
      font: 600 13px/1 inherit; flex-shrink: 0; }
.go:hover    { background: #2ea043; }
.go:active   { opacity: .85; }
.go:disabled { opacity: .45; cursor: default; }

/* editors */
.editors { display: flex; flex: 1; overflow: hidden; min-height: 0; }
.pane { display: flex; flex-direction: column; flex: 1; overflow: hidden; }
.pane + .pane { border-left: 1px solid var(--border); }
.pane-hdr { background: var(--surface); border-bottom: 1px solid var(--border);
            padding: 5px 14px; display: flex; align-items: center;
            justify-content: space-between; flex-shrink: 0; }
.pane-title { font-size: 11px; color: var(--muted); text-transform: uppercase;
              letter-spacing: .5px; }
.acts { display: flex; gap: 5px; }
.act { background: #21262d; border: 1px solid var(--border); color: var(--muted);
       padding: 2px 9px; border-radius: 4px; cursor: pointer;
       font: 11px/1.5 inherit; }
.act:hover { background: #2d333b; color: var(--text); }
textarea { flex: 1; background: var(--bg); color: var(--text); border: none;
           resize: none; padding: 14px 16px; font: 12.5px/1.65 inherit;
           outline: none; min-height: 0; }
#out-ta { color: var(--output); }

/* status bar */
.sbar { background: var(--surface); border-top: 1px solid var(--border);
        padding: 4px 20px; display: flex; gap: 20px; font-size: 11px;
        color: var(--muted); flex-shrink: 0; align-items: center; flex-wrap: wrap; }
.si   { display: flex; gap: 5px; white-space: nowrap; }
.sv   { color: var(--accent); }
#smsg { margin-left: auto; font-weight: 600; }
</style>
</head>
<body>

<header>
  <div class="logo">chalkobusf<span>NewtonScript Source Obfuscator</span></div>
  <div class="hlinks">
    <a class="hlink" href="https://github.com/xxchalk3-boop/Yeah" target="_blank">GitHub</a>
  </div>
</header>

<div class="toolbar">
  <div class="presets">
    <button class="pbtn" id="pl" onclick="setPreset('light')">Light</button>
    <button class="pbtn" id="pm" onclick="setPreset('medium')">Medium</button>
    <button class="pbtn on" id="ph" onclick="setPreset('heavy')">Heavy</button>
    <button class="pbtn" id="pc" onclick="setPreset('custom')">Custom</button>
  </div>
  <div class="vbar"></div>
  <div class="passes">
    <label class="cb"><input type="checkbox" data-k="stripComments"  checked>strip comments</label>
    <label class="cb"><input type="checkbox" data-k="minifySpace"    checked>minify space</label>
    <label class="cb"><input type="checkbox" data-k="encodeStrings"  checked>encode strings</label>
    <label class="cb"><input type="checkbox" data-k="obfuscateNums"  checked>obfuscate nums</label>
    <label class="cb"><input type="checkbox" data-k="renameVars"     checked>rename vars</label>
    <label class="cb"><input type="checkbox" data-k="obfuscateNils"  checked>obfuscate nils</label>
    <label class="cb"><input type="checkbox" data-k="obfuscateBools" checked>obfuscate bools</label>
    <label class="cb"><input type="checkbox" data-k="deepNums"       checked>deep nums</label>
    <label class="cb"><input type="checkbox" data-k="addJunk"        checked>add junk</label>
  </div>
  <button class="go" id="gobtn" onclick="run()">Obfuscate &#8594;</button>
</div>

<div class="editors">
  <div class="pane">
    <div class="pane-hdr">
      <span class="pane-title">Input &mdash; NewtonScript source</span>
      <div class="acts">
        <button class="act" onclick="loadExample()">Example</button>
        <button class="act" onclick="uploadFile()">Upload</button>
        <button class="act" onclick="clearAll()">Clear</button>
      </div>
    </div>
    <textarea id="in-ta" spellcheck="false"
      placeholder="Paste NewtonScript source here&#8230;&#10;(or click Example / Upload)"></textarea>
  </div>
  <div class="pane">
    <div class="pane-hdr">
      <span class="pane-title">Output &mdash; Obfuscated</span>
      <div class="acts">
        <button class="act" onclick="copyOut()">Copy</button>
        <button class="act" onclick="downloadOut()">Download .ns</button>
      </div>
    </div>
    <textarea id="out-ta" spellcheck="false" readonly
      placeholder="Obfuscated output appears here&#8230;&#10;&#10;Tip: Ctrl+Enter to run"></textarea>
  </div>
</div>

<div class="sbar">
  <div class="si">Input: <span class="sv" id="s-in">&mdash;</span></div>
  <div class="si">Output: <span class="sv" id="s-out">&mdash;</span></div>
  <div class="si">Expansion: <span class="sv" id="s-ratio">&mdash;</span></div>
  <div class="si">Passes: <span class="sv" id="s-np">9</span> active</div>
  <span id="smsg"></span>
</div>

<input type="file" id="file-pick" accept=".ns,.txt" style="display:none">

<script>
const PRESETS = {
  light:  ['stripComments','minifySpace','renameVars'],
  medium: ['stripComments','minifySpace','obfuscateNums','renameVars','obfuscateNils','obfuscateBools'],
  heavy:  ['stripComments','minifySpace','encodeStrings','obfuscateNums','deepNums',
           'renameVars','obfuscateNils','obfuscateBools','addJunk'],
};

function setPreset(name) {
  document.querySelectorAll('.pbtn').forEach(b => b.classList.remove('on'));
  document.getElementById({light:'pl',medium:'pm',heavy:'ph',custom:'pc'}[name]).classList.add('on');
  if (name === 'custom') return;
  const keys = new Set(PRESETS[name]);
  document.querySelectorAll('[data-k]').forEach(cb => { cb.checked = keys.has(cb.dataset.k); });
  refreshCount();
}

function getOpts() {
  const o = {};
  document.querySelectorAll('[data-k]:checked').forEach(cb => { o[cb.dataset.k] = true; });
  return o;
}

function refreshCount() {
  document.getElementById('s-np').textContent =
    document.querySelectorAll('[data-k]:checked').length;
}

document.querySelectorAll('[data-k]').forEach(cb =>
  cb.addEventListener('change', () => {
    refreshCount();
    // switch to Custom if selection no longer matches any preset
    const checked = new Set([...document.querySelectorAll('[data-k]:checked')].map(c => c.dataset.k));
    const match = Object.entries(PRESETS).find(([, keys]) =>
      keys.length === checked.size && keys.every(k => checked.has(k)));
    document.querySelectorAll('.pbtn').forEach(b => b.classList.remove('on'));
    document.getElementById(match ? {light:'pl',medium:'pm',heavy:'ph'}[match[0]] : 'pc')
            .classList.add('on');
  })
);

async function run() {
  const src = document.getElementById('in-ta').value;
  if (!src.trim()) { flash('Paste some NewtonScript first', 'var(--orange)'); return; }
  const btn = document.getElementById('gobtn');
  btn.disabled = true; btn.textContent = 'Running…';
  try {
    const r = await fetch('/obfuscate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({source: src, opts: getOpts()})
    });
    if (!r.ok) { const t = await r.text(); throw new Error(t || r.statusText); }
    const d = await r.json();
    document.getElementById('out-ta').value = d.result;
    document.getElementById('s-in').textContent    = fmtBytes(d.input_size);
    document.getElementById('s-out').textContent   = fmtBytes(d.output_size);
    document.getElementById('s-ratio').textContent =
      d.input_size > 0 ? (d.output_size / d.input_size).toFixed(2) + '\xd7' : '—';
    flash('Done ✓', 'var(--green)');
  } catch(e) {
    flash('Error: ' + e.message, 'var(--red)');
  } finally {
    btn.disabled = false; btn.textContent = 'Obfuscate →';
  }
}

function fmtBytes(n) {
  return n >= 1024 ? (n / 1024).toFixed(1) + ' KB' : n + ' B';
}

function flash(text, color) {
  const el = document.getElementById('smsg');
  el.textContent = text; el.style.color = color;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.textContent = '', 3000);
}

function copyOut() {
  const v = document.getElementById('out-ta').value;
  if (!v) { flash('Nothing to copy', 'var(--orange)'); return; }
  navigator.clipboard.writeText(v).then(() => flash('Copied!', 'var(--green)'));
}

function downloadOut() {
  const v = document.getElementById('out-ta').value;
  if (!v) { flash('Nothing to download', 'var(--orange)'); return; }
  const a = document.createElement('a');
  a.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(v);
  a.download = 'obfuscated.ns';
  a.click();
}

function clearAll() {
  document.getElementById('in-ta').value = '';
  document.getElementById('out-ta').value = '';
  ['s-in','s-out','s-ratio'].forEach(id => document.getElementById(id).textContent = '—');
}

function loadExample() {
  document.getElementById('in-ta').value =
`// compute the area of a rectangle
local width  := 10;
local height := 5;
local flag   := true;
local result := nil;
if flag then
begin
  result := width * height;
  Print("Area: " & NumberStr(result));
end;`;
}

function uploadFile() {
  document.getElementById('file-pick').click();
}

document.getElementById('file-pick').addEventListener('change', function() {
  const f = this.files[0]; if (!f) return;
  const reader = new FileReader();
  reader.onload = e => document.getElementById('in-ta').value = e.target.result;
  reader.readAsText(f);
  this.value = '';
});

// drag-and-drop onto input pane
const inTA = document.getElementById('in-ta');
inTA.addEventListener('dragover', e => { e.preventDefault(); inTA.style.opacity = '.6'; });
inTA.addEventListener('dragleave', () => { inTA.style.opacity = ''; });
inTA.addEventListener('drop', e => {
  e.preventDefault(); inTA.style.opacity = '';
  const f = e.dataTransfer.files[0]; if (!f) return;
  new FileReader().onload = ev => { inTA.value = ev.target.result; };
  new FileReader().readAsText(f);
});

// Ctrl+Enter / Cmd+Enter to obfuscate
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') run();
});

refreshCount();
</script>
</body>
</html>"""


# ── HTTP server ───────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._reply(200, 'text/html; charset=utf-8', _HTML.encode())

    def do_POST(self):
        if self.path != '/obfuscate':
            self._reply(404, 'text/plain', b'Not found')
            return
        length = int(self.headers.get('Content-Length', 0))
        try:
            body   = json.loads(self.rfile.read(length))
            source = body.get('source', '')
            opts   = {k: bool(v) for k, v in body.get('opts', {}).items()}
            result = _Chalkobusf().obfuscate(source, opts)
            resp   = json.dumps({
                'result':      result,
                'input_size':  len(source.encode()),
                'output_size': len(result.encode()),
            })
            self._reply(200, 'application/json', resp.encode())
        except Exception as exc:
            self._reply(500, 'text/plain', str(exc).encode())

    def _reply(self, code, ct, body):
        self.send_response(code)
        self.send_header('Content-Type', ct)
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress per-request logging; server start/stop is printed by main()


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description='chalkobusf web UI — browser interface for the NewtonScript obfuscator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split('Usage:')[1],
    )
    p.add_argument('--port',       type=int, default=5000, metavar='N',
                   help='port to listen on (default: 5000)')
    p.add_argument('--host',       default='127.0.0.1', metavar='ADDR',
                   help='bind address (default: 127.0.0.1)')
    p.add_argument('--no-browser', action='store_true',
                   help='do not auto-open a browser tab on startup')
    args = p.parse_args()

    url    = f'http://{args.host}:{args.port}'
    server = HTTPServer((args.host, args.port), _Handler)
    print(f'chalkobusf UI  →  {url}')
    print('Press Ctrl+C to stop.')
    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()
