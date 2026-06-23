#!/usr/bin/env python3
"""
generar.py
Lee todos los archivos .WD3 de la carpeta data/, fusiona los registros,
y genera index.html con el dashboard actualizado.

Uso local:  python generar.py
GitHub CI:  se ejecuta automáticamente al subir un .WD3
"""
import re, os, sys
from datetime import datetime
from collections import defaultdict

# ── 1. Leer todos los WD3 de la carpeta data/ ─────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(SCRIPT_DIR, 'data')
OUT_FILE   = os.path.join(SCRIPT_DIR, 'index.html')

if not os.path.isdir(DATA_DIR):
    print("ERROR: carpeta 'data/' no encontrada.")
    sys.exit(1)

wd3_files = sorted(f for f in os.listdir(DATA_DIR) if f.lower().endswith('.wd3'))
if not wd3_files:
    print("ERROR: no hay archivos .WD3 en data/")
    sys.exit(1)

print(f"Archivos encontrados: {wd3_files}")

# ── 2. Parsear y deduplicar por timestamp ─────────────────────────────
PATTERN = re.compile(
    r'RM;(\d{12});\d+;(\d+);\d+;([\d.]+);([\d.]+);([\d.]+);(\d+);(\d+);\d+;\d+;([\d.]+);')

seen      = set()
all_recs  = {}   # timestamp → record dict

for fname in wd3_files:
    path = os.path.join(DATA_DIR, fname)
    text = open(path, encoding='utf-8', errors='ignore').read()
    for m in PATTERN.finditer(text):
        ts = m.group(1)
        if ts in seen:
            continue
        seen.add(ts)
        dt  = datetime(int(ts[:4]),int(ts[4:6]),int(ts[6:8]),
                       int(ts[8:10]),int(ts[10:12]))
        tc  = round((float(m.group(4))-32)*5/9, 1)
        all_recs[ts] = {
            'dt':dt, 'dia': f"{ts[6:8]}/{ts[4:6]}/{ts[:4]}",
            'tc':tc, 'hum':float(m.group(5)),
            'rain_mm':round(float(m.group(3))*25.4, 1),
            'wind':int(m.group(7)), 'volt':float(m.group(8)),
            'batt':int(m.group(2))
        }

parsed = [all_recs[k] for k in sorted(all_recs)]
print(f"Registros únicos: {len(parsed)}")

if not parsed:
    print("ERROR: sin registros válidos.")
    sys.exit(1)

# ── 3. Series temporales ──────────────────────────────────────────────
ts_lbl, ts_tc, ts_hum, ts_wind, ts_rain, ts_volt = [], [], [], [], [], []
for p in parsed:
    ts_lbl.append(p['dt'].strftime('%d/%m %H:%M'))
    ts_tc.append(p['tc']); ts_hum.append(p['hum'])
    ts_wind.append(p['wind']); ts_rain.append(p['rain_mm'])
    ts_volt.append(p['volt'])

# ── 4. Agregados diarios ──────────────────────────────────────────────
by_day = defaultdict(list)
for p in parsed:
    by_day[p['dt'].strftime('%d/%m/%Y')].append(p)

d_keys = list(dict.fromkeys(p['dt'].strftime('%d/%m/%Y') for p in parsed))
d_lbl  = [k[:5] for k in d_keys]   # "15/06"
d_tmin = [round(min(v['tc']      for v in by_day[k]),1) for k in d_keys]
d_tavg = [round(sum(v['tc']      for v in by_day[k])/len(by_day[k]),1) for k in d_keys]
d_tmax = [round(max(v['tc']      for v in by_day[k]),1) for k in d_keys]
d_rain = [round(sum(v['rain_mm'] for v in by_day[k]),1) for k in d_keys]
d_wmax = [max(v['wind']          for v in by_day[k]) for k in d_keys]
d_havg = [round(sum(v['hum']     for v in by_day[k])/len(by_day[k]),1) for k in d_keys]
d_hmin = [round(min(v['hum']     for v in by_day[k]),1) for k in d_keys]
d_hmax = [round(max(v['hum']     for v in by_day[k]),1) for k in d_keys]

# ── 5. Stats globales ─────────────────────────────────────────────────
total_rain  = round(sum(d_rain),1)
abs_tmax    = max(ts_tc)
abs_tmin    = min(ts_tc)
dias_lluvia = sum(1 for r in d_rain if r > 0)
n_rec       = len(parsed)
fecha_ini   = parsed[0]['dt'].strftime('%d %b %Y')
fecha_fin   = parsed[-1]['dt'].strftime('%d %b %Y')
generado    = datetime.now().strftime('%d/%m/%Y %H:%M UTC')

def jsl(lst):  return str(lst)
def jss(lst):  return str(lst).replace("'", '"')

# ── 6. HTML ────────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Dashboard meteorológico WatchDog 3000, Suchitepéquez, Guatemala.">
<title>WatchDog 3000 · Suchitepéquez · {fecha_ini}–{fecha_fin}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
:root{{--bg:#F0EEEA;--surf:#fff;--surf2:#F7F5F1;--brd:rgba(0,0,0,0.08);
      --shd:0 1px 4px rgba(0,0,0,0.08);--navy:#1D3461;--blue:#1F7FDF;
      --coral:#E05A2B;--teal:#1A9E72;--steel:#2E86AB;--txt:#18181A;
      --muted:#6E6D68;--sub:#9A9891;--r:12px;--r2:8px;--sp:16px}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--txt);font-size:14px;line-height:1.5}}
nav{{background:var(--navy);color:#fff;padding:14px var(--sp);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,0.3)}}
.nav-t{{font-size:15px;font-weight:700}}.nav-s{{font-size:10px;color:#A8B8CC;margin-top:2px}}
.nav-meta{{font-size:11px;color:#A8B8CC;display:flex;gap:14px;flex-wrap:wrap}}
.dot{{width:7px;height:7px;border-radius:50%;background:#4ADE80;display:inline-block;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}
main{{max-width:1280px;margin:0 auto;padding:20px var(--sp) 40px}}
.banner{{background:linear-gradient(135deg,var(--navy),#2C5282);color:#fff;border-radius:var(--r);padding:20px 24px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
.banner h2{{font-size:17px;font-weight:700;margin-bottom:4px}}.banner p{{font-size:11px;color:#A8B8CC}}
.chips{{display:flex;gap:8px;flex-wrap:wrap}}
.chip{{background:rgba(255,255,255,0.12);border-radius:20px;padding:4px 12px;font-size:11px;font-weight:500;color:#E2EAF4}}
.kpi-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:20px}}
.kpi{{background:var(--surf);border-radius:var(--r);border:.5px solid var(--brd);padding:14px 16px;box-shadow:var(--shd)}}
.kpi-l{{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);margin-bottom:6px}}
.kpi-v{{font-size:24px;font-weight:700;line-height:1;margin-bottom:4px}}.kpi-s{{font-size:11px;color:var(--sub)}}
.panels{{display:grid;gap:16px;margin-bottom:16px}}
.r1{{grid-template-columns:1fr}}.r2{{grid-template-columns:1fr 1fr}}.r3{{grid-template-columns:2fr 1fr 1fr}}
.panel{{background:var(--surf);border-radius:var(--r);border:.5px solid var(--brd);box-shadow:var(--shd);padding:16px 18px}}
.ph{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px}}
.pt{{font-size:12px;font-weight:600}}.leg{{display:flex;gap:12px;flex-wrap:wrap}}
.li{{display:flex;align-items:center;gap:5px;font-size:10px;color:var(--muted)}}
.ll{{width:14px;height:2px;border-radius:1px;flex-shrink:0}}
.ld{{width:14px;height:0;border-top:2px dashed;flex-shrink:0}}
.storm{{background:linear-gradient(135deg,#EBF4FC,#D6E8FA);border:1px solid #B0D0ED;border-radius:var(--r);padding:20px 24px;margin-bottom:16px}}
.sh{{display:flex;align-items:center;gap:10px;margin-bottom:14px}}
.si{{font-size:28px}}.sh h3{{font-size:15px;font-weight:700;color:var(--navy)}}.sh p{{font-size:11px;color:var(--muted)}}
.ss{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.sv{{background:rgba(255,255,255,.7);border-radius:var(--r2);padding:12px 14px;border:.5px solid rgba(255,255,255,.9)}}
.sv-val{{font-size:20px;font-weight:700;color:var(--navy);margin-bottom:2px}}.sv-l{{font-size:10px;color:var(--muted)}}
.tw{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:12px}}
thead th{{background:var(--navy);color:#fff;padding:8px 12px;text-align:right;font-weight:600;font-size:11px}}
thead th:first-child{{text-align:left;border-radius:var(--r2) 0 0 0}}thead th:last-child{{border-radius:0 var(--r2) 0 0}}
tbody tr{{border-bottom:.5px solid var(--brd)}}tbody tr:nth-child(even){{background:var(--surf2)}}
tbody tr.rn{{background:#EBF4FC}}tbody td{{padding:8px 12px;text-align:right}}tbody td:first-child{{text-align:left;font-weight:600;color:var(--navy)}}
tfoot td{{background:var(--surf2);padding:8px 12px;text-align:right;font-weight:600;color:var(--navy);border-top:1.5px solid var(--navy)}}tfoot td:first-child{{text-align:left}}
.rb{{background:#2E86AB;color:#fff;border-radius:20px;padding:1px 7px;font-size:10px;font-weight:600}}
footer{{text-align:center;font-size:11px;color:var(--sub);padding:24px 0 8px;border-top:.5px solid var(--brd);margin-top:8px}}
@media(max-width:900px){{.kpi-grid{{grid-template-columns:repeat(3,1fr)}}.r2,.r3{{grid-template-columns:1fr}}.ss{{grid-template-columns:repeat(2,1fr)}}.nav-meta{{display:none}}}}
@media(max-width:540px){{.kpi-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<nav>
  <div><div class="nav-t">&#127782; WatchDog 3000 &mdash; Sembrad&iacute;o de Ma&iacute;z</div>
  <div class="nav-s">Suchitep&eacute;quez, Guatemala</div></div>
  <div class="nav-meta">
    <span>&#128205; 14.364°N, -91.552°W</span>
    <span>&#128345; UTC-6</span>
    <span><span class="dot"></span>&nbsp;ID 54400111</span>
    <span>&#128260; Actualizado: {generado}</span>
  </div>
</nav>
<main>
<div class="banner">
  <div><h2>{fecha_ini} &ndash; {fecha_fin}</h2>
  <p>WatchDog 3000 Wireless &bull; Firmware 00.01.75 &bull; {n_rec} registros &bull; 10 min/registro</p></div>
  <div class="chips">
    <span class="chip">&#127303; Temporada de lluvias</span>
    <span class="chip">&#127783; {dias_lluvia} d&iacute;a(s) con lluvia</span>
    <span class="chip">&#9728; {len(d_keys)} d&iacute;as registrados</span>
  </div>
</div>

<div class="kpi-grid">
  <div class="kpi"><div class="kpi-l">Lluvia total</div>
    <div class="kpi-v" style="color:var(--steel)">{total_rain}<span style="font-size:13px;font-weight:500"> mm</span></div>
    <div class="kpi-s">{dias_lluvia} d&iacute;a(s) con lluvia</div></div>
  <div class="kpi"><div class="kpi-l">Temp. m&aacute;xima</div>
    <div class="kpi-v" style="color:var(--coral)">{abs_tmax}<span style="font-size:13px;font-weight:500"> °C</span></div>
    <div class="kpi-s">pico del per&iacute;odo</div></div>
  <div class="kpi"><div class="kpi-l">Temp. m&iacute;nima</div>
    <div class="kpi-v" style="color:var(--blue)">{abs_tmin}<span style="font-size:13px;font-weight:500"> °C</span></div>
    <div class="kpi-s">m&iacute;nimo nocturno</div></div>
  <div class="kpi"><div class="kpi-l">Viento m&aacute;ximo</div>
    <div class="kpi-v" style="color:var(--teal)">{max(ts_wind)}<span style="font-size:13px;font-weight:500"> mph</span></div>
    <div class="kpi-s">r&aacute;faga m&aacute;xima</div></div>
  <div class="kpi"><div class="kpi-l">Registros</div>
    <div class="kpi-v" style="color:var(--navy)">{n_rec}</div>
    <div class="kpi-s">{len(d_keys)} d&iacute;as &bull; 10 min/reg.</div></div>
</div>

<div class="panels r1"><div class="panel">
  <div class="ph"><span class="pt">&#128202; Serie temporal &mdash; Temperatura y Humedad relativa</span>
  <div class="leg"><span class="li"><span class="ll" style="background:#E05A2B"></span>Temperatura (°C)</span>
  <span class="li"><span class="ld" style="border-color:#1F7FDF"></span>Humedad %HR</span></div></div>
  <div style="position:relative;height:210px"><canvas id="cS"></canvas></div>
</div></div>

<div class="panels r3">
  <div class="panel"><div class="ph"><span class="pt">&#127777; Temperatura diaria &mdash; rango y promedio</span></div>
    <div style="position:relative;height:185px"><canvas id="cTD"></canvas></div></div>
  <div class="panel"><div class="ph"><span class="pt">&#127783; Lluvia total diaria</span></div>
    <div style="position:relative;height:185px"><canvas id="cRD"></canvas></div></div>
  <div class="panel"><div class="ph"><span class="pt">&#128168; Viento m&aacute;ximo diario</span></div>
    <div style="position:relative;height:185px"><canvas id="cWD"></canvas></div></div>
</div>

<div class="panels r2">
  <div class="panel"><div class="ph"><span class="pt">&#128167; Humedad relativa diaria &mdash; rango y promedio</span></div>
    <div style="position:relative;height:155px"><canvas id="cHD"></canvas></div></div>
  <div class="panel"><div class="ph"><span class="pt">&#9889; Voltaje &mdash; ciclo panel solar (primeros 2 d&iacute;as)</span></div>
    <div style="position:relative;height:155px"><canvas id="cV"></canvas></div></div>
</div>

<div class="storm">
  <div class="sh"><span class="si">&#9928;</span>
    <div><h3>Tormenta convectiva &mdash; 15 jun 2026</h3>
    <p>Evento principal de precipitaci&oacute;n &bull; Inicio 18:10 &bull; Precursores desde 17:30</p></div></div>
  <div class="ss">
    <div class="sv"><div class="sv-val">59.7 mm</div><div class="sv-l">Lluvia en ~40 min</div></div>
    <div class="sv"><div class="sv-val">21.3 mm</div><div class="sv-l">Pico m&aacute;x. (18:31 / 10min)</div></div>
    <div class="sv"><div class="sv-val">22 mph</div><div class="sv-l">Viento m&aacute;ximo (17:50)</div></div>
    <div class="sv"><div class="sv-val">37→23 °C</div><div class="sv-l">Ca&iacute;da de temperatura</div></div>
  </div>
</div>

<div class="panel" style="margin-bottom:16px">
  <div class="ph" style="margin-bottom:14px"><span class="pt">&#128203; Resumen diario</span></div>
  <div class="tw"><table>
    <thead><tr><th>Fecha</th><th>T M&iacute;n</th><th>T Prom</th><th>T M&aacute;x</th>
      <th>HR M&iacute;n</th><th>HR Prom</th><th>HR M&aacute;x</th><th>Lluvia (mm)</th><th>Viento M&aacute;x</th></tr></thead>
    <tbody id="tb"></tbody><tfoot><tr id="tf"></tr></tfoot>
  </table></div>
</div>

<footer>
  WatchDog 3000 Wireless &bull; ID 54400111 &bull; Suchitep&eacute;quez, Guatemala &bull;
  Firmware 00.01.75 &bull; Generado autom&aacute;ticamente: {generado}
</footer></main>

<script>
const tsL={jss(ts_lbl)},tsT={jsl(ts_tc)},tsH={jsl(ts_hum)};
const tsW={jsl(ts_wind)},tsR={jsl(ts_rain)},tsV={jsl(ts_volt)};
const dL={jss(d_lbl)},dTn={jsl(d_tmin)},dTa={jsl(d_tavg)},dTx={jsl(d_tmax)};
const dR={jsl(d_rain)},dWx={jsl(d_wmax)},dHa={jsl(d_havg)},dHn={jsl(d_hmin)},dHx={jsl(d_hmax)};
const GC='rgba(0,0,0,0.06)',TC='#999';
const XT={{color:TC,font:{{size:10}},maxRotation:0,autoSkip:true}};
Chart.defaults.font.family="'Inter',system-ui,sans-serif";
new Chart('cS',{{type:'line',data:{{labels:tsL,datasets:[
  {{label:'T',data:tsT,yAxisID:'yT',borderColor:'#E05A2B',borderWidth:1.2,pointRadius:0,tension:0.1}},
  {{label:'H',data:tsH,yAxisID:'yH',borderColor:'#1F7FDF',borderWidth:1,borderDash:[4,3],pointRadius:0,tension:0.1}}
]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},
  plugins:{{legend:{{display:false}},decimation:{{enabled:true,algorithm:'lttb',samples:300}},
    tooltip:{{callbacks:{{label:c=>c.datasetIndex===0?` ${{c.parsed.y}}°C`:` ${{c.parsed.y}}% HR`}}}}}},
  scales:{{x:{{grid:{{color:GC}},ticks:{{...XT,maxTicksLimit:8}}}},
    yT:{{position:'left',grid:{{color:GC}},ticks:{{color:'#E05A2B',font:{{size:9}},callback:v=>v+'°C'}},min:20,max:40}},
    yH:{{position:'right',grid:{{display:false}},ticks:{{color:'#1F7FDF',font:{{size:9}},callback:v=>v+'%'}},min:40,max:100}}}}
}}}});
new Chart('cTD',{{data:{{labels:dL,datasets:[
  {{type:'bar',data:dL.map((_,i)=>[dTn[i],dTx[i]]),backgroundColor:'rgba(224,90,43,.18)',borderColor:'rgba(224,90,43,.4)',borderWidth:1,borderRadius:4,order:2}},
  {{type:'line',data:dTa,borderColor:'#E05A2B',borderWidth:2.5,pointRadius:5,pointBackgroundColor:'#E05A2B',tension:0,order:1}}
]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},
  tooltip:{{callbacks:{{label:c=>c.datasetIndex===0?` Rango ${{c.parsed.y[0]}}–${{c.parsed.y[1]}}°C`:` Prom ${{c.parsed.y}}°C`}}}}}},
  scales:{{x:{{grid:{{color:GC}},ticks:XT}},y:{{grid:{{color:GC}},ticks:{{color:TC,font:{{size:9}},callback:v=>v+'°C'}},min:20,max:40}}}}
}}}});
new Chart('cRD',{{type:'bar',data:{{labels:dL,datasets:[{{data:dR,
  backgroundColor:dR.map(v=>v>0?'rgba(46,134,171,.8)':'rgba(46,134,171,.12)'),borderRadius:5,borderWidth:0}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>` ${{c.parsed.y}} mm`}}}}}},
  scales:{{x:{{grid:{{display:false}},ticks:XT}},y:{{grid:{{color:GC}},ticks:{{color:TC,font:{{size:9}},callback:v=>v+'mm'}},min:0}}}}
}}}});
new Chart('cWD',{{type:'bar',data:{{labels:dL,datasets:[{{data:dWx,backgroundColor:'rgba(26,158,114,.7)',borderRadius:5,borderWidth:0}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>` ${{c.parsed.y}} mph`}}}}}},
  scales:{{x:{{grid:{{display:false}},ticks:XT}},y:{{grid:{{color:GC}},ticks:{{color:TC,font:{{size:9}},callback:v=>v+'mph'}},min:0}}}}
}}}});
new Chart('cHD',{{data:{{labels:dL,datasets:[
  {{type:'bar',data:dL.map((_,i)=>[dHn[i],dHx[i]]),backgroundColor:'rgba(31,127,223,.12)',borderColor:'rgba(31,127,223,.35)',borderWidth:1,borderRadius:4,order:2}},
  {{type:'line',data:dHa,borderColor:'#1F7FDF',borderWidth:2.5,pointRadius:5,pointBackgroundColor:'#1F7FDF',tension:0,order:1}}
]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},
  tooltip:{{callbacks:{{label:c=>c.datasetIndex===0?` Rango ${{c.parsed.y[0]}}–${{c.parsed.y[1]}}%`:` Prom ${{c.parsed.y}}%`}}}}}},
  scales:{{x:{{grid:{{color:GC}},ticks:XT}},y:{{grid:{{color:GC}},ticks:{{color:TC,font:{{size:9}},callback:v=>v+'%'}},min:40,max:100}}}}
}}}});
const v2=tsV.slice(0,Math.min(150,tsV.length)),l2=tsL.slice(0,v2.length);
new Chart('cV',{{type:'line',data:{{labels:l2,datasets:[{{data:v2,borderColor:'#7F77DD',borderWidth:1.5,pointRadius:0,tension:0.1}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{callbacks:{{label:c=>` ${{c.parsed.y.toFixed(3)}}V`}}}}}},
  scales:{{x:{{grid:{{display:false}},ticks:{{...XT,maxTicksLimit:6}}}},y:{{grid:{{color:GC}},ticks:{{color:TC,font:{{size:9}},callback:v=>v.toFixed(0)+'V'}},min:5,max:10}}}}
}}}});
const tb=document.getElementById('tb');
dL.forEach((d,i)=>{{const tr=document.createElement('tr');
  if(dR[i]>0)tr.className='rn';
  tr.innerHTML=`<td>${{d}}</td><td>${{dTn[i]}}°C</td><td>${{dTa[i]}}°C</td><td>${{dTx[i]}}°C</td><td>${{dHn[i]}}%</td><td>${{dHa[i]}}%</td><td>${{dHx[i]}}%</td><td>${{dR[i]>0?`<span class="rb">${{dR[i]}}</span>`:`<span style="color:#ccc">—</span>`}}</td><td>${{dWx[i]}} mph</td>`;
  tb.appendChild(tr);}});
const sumR=dR.reduce((a,b)=>a+b,0).toFixed(1);
document.getElementById('tf').innerHTML=`<td>Total / Prom</td><td>${{Math.min(...dTn).toFixed(1)}}°C</td><td>${{(dTa.reduce((a,b)=>a+b)/dTa.length).toFixed(1)}}°C</td><td>${{Math.max(...dTx).toFixed(1)}}°C</td><td>${{Math.min(...dHn).toFixed(1)}}%</td><td>${{(dHa.reduce((a,b)=>a+b)/dHa.length).toFixed(1)}}%</td><td>${{Math.max(...dHx).toFixed(1)}}%</td><td><strong>${{sumR}} mm</strong></td><td>${{Math.max(...dWx)}} mph</td>`;
</script></body></html>"""

with open(OUT_FILE, 'w', encoding='utf-8') as f:
    f.write(HTML)
print(f"✓ index.html generado ({len(HTML)//1024} KB) → {OUT_FILE}")
