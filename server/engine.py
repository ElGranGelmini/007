import json, re, html, os, statistics, math, random
from collections import Counter
from pathlib import Path
from datetime import datetime, timedelta

def parse(text):
    text=text.strip()
    if text.startswith("```"): text=re.sub(r"^```[^\n]*\n|\n```$", "", text)
    obj=json.loads(text); obj=obj.get("data",obj)
    rows=obj["data"]
    if obj.get("limited") or len(rows)!=int(obj["recordsFiltered"]): raise ValueError("Historial incompleto")
    unique={}
    for r in rows:
        if r["idOposicion"]!=6: raise ValueError("Fuente incorrecta")
        key=r["idNotificacion"]
        if key in unique and unique[key]!=r: raise ValueError("Notificación contradictoria")
        unique[key]=r
    return sorted(unique.values(),key=lambda r:datetime.strptime(r["fecha"],"%H:%M:%S %d-%m-%Y"))

def analyze(rows):
    days={}; latest=None; frontier=None; last_finished=None
    for r in rows:
        dt=datetime.strptime(r["fecha"],"%H:%M:%S %d-%m-%Y"); day=dt.date().isoformat(); latest=day
        d=days.setdefault(day,{"date":day,"entries":set(),"finished":set(),"withdrawn":set(),"excluded":set(),"absent":set(),"closed":False,"started":False,"frontier":None})
        s=html.unescape(re.sub("<[^>]+>"," ",r["mensaje"])).lower()
        if re.search(r"comienza la sesión|inicia el primer ejercicio",s): d["started"]=True
        if "finaliza la sesión" in s: d["closed"]=True
        m=re.match(r"(?:entra|termina|se retira|se nombra|el)\s+(?:(?:el|al)\s+)?n\s*[º°o.]?\s*(\d+)",s)
        if not m: continue
        n=int(m[1]); event=False
        if s.startswith("entra"): d["entries"].add(n); event=True
        if s.startswith("termina"): d["finished"].add(n); last_finished=n; event=True
        if "se retira" in s: d["withdrawn"].add(n); last_finished=n; event=True
        if "excluido" in s: d["excluded"].add(n); last_finished=n; event=True
        if "no presente" in s: d["absent"].add(n); event=True
        if event: frontier=max(frontier or n,n)
        d["frontier"]=frontier
    result=[]; previous=None
    for d in days.values():
        if not d["entries"]: continue
        f=d["frontier"]; advance=None if previous is None else f-previous
        previous=f
        result.append({**{k:len(d[k]) for k in ("entries","finished","withdrawn","excluded","absent")},"date":d["date"],"closed":d["closed"] and d["started"],"advance":advance,"frontier":f})
    complete=[d for d in result if d["closed"]]
    means={k:round(statistics.mean(d[k] for d in complete),2) if complete else None for k in ("entries","finished","withdrawn")}
    advances=[d["advance"] for d in complete if d["advance"] is not None and d["advance"]>0]
    means["advance"]=round(statistics.mean(advances),2) if advances else None
    return {"days":result,"means":means,"latest":latest,"frontier":frontier,"last_finished":last_finished,"complete":len(complete),"calendar":read_calendar(rows)}

def read_calendar(rows):
    announced=set(); extra=set()
    for r in rows:
        text=html.unescape(re.sub("<[^>]+>"," ",r["mensaje"])).lower()
        if "convocatoria" in text:
            for day,month,year in re.findall(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})",text):
                try: announced.add(datetime(int(year),int(month),int(day)).date().isoformat())
                except ValueError: pass
        # Explicit exceptional sessions from the tribunal's announcement.
        match=re.search(r"jueves días ([\d, y]+) de noviembre",text)
        if match:
            year=datetime.strptime(r["fecha"],"%H:%M:%S %d-%m-%Y").year
            for day in re.findall(r"\d+",match[1]):
                extra.add(datetime(year,11,int(day)).date().isoformat())
    return {"announced":sorted(announced),"extra":sorted(extra)}

# Madrid public holidays: municipal/regional calendar. Exclusion is a scheduling
# assumption, overridden by an explicit tribunal convocatoria on that date.
HOLIDAYS={"2026-10-12","2026-11-02","2026-11-09"}

def session_day(dt,calendar):
    key=dt.date().isoformat()
    if key in calendar.get("announced",[]) or key in calendar.get("extra",[]): return True
    return key not in HOLIDAYS and dt.weekday() in (0,1,2)

def training_days(a):
    return [d for d in a["days"] if d["closed"] and d["advance"] is not None and d["advance"]>=0]

def distribution(history,weekday):
    # Recent observations get more weight; keep a pooled contribution because
    # weekday samples are small. Unknown weekdays use the pooled sample only.
    weights=[2**(-(len(history)-1-i)/6) for i in range(len(history))]
    same=[i for i,d in enumerate(history) if datetime.fromisoformat(d["date"]).weekday()==weekday]
    total=sum(weights); same_total=sum(weights[i] for i in same)
    strength=len(same)/(len(same)+1) if same else 0
    probabilities=[(1-strength)*w/total+(strength*w/same_total if i in same else 0) for i,w in enumerate(weights)]
    return [d["advance"] for d in history],probabilities

def expected_advance(history,weekday):
    values,weights=distribution(history,weekday)
    return sum(v*w for v,w in zip(values,weights))

def forecast_details(a,target,simulations=6000):
    history=training_days(a)
    if len(history)<5 or target<=a["frontier"]: return None
    calendar=a.get("calendar",{}); anchor=datetime.fromisoformat(a["latest"])
    # The explicit calendar and holiday assumptions are scoped to this phase.
    limit=datetime(2026,11,30)
    if anchor>limit: return None
    future=[]; dt=anchor
    current=next((d for d in reversed(a["days"]) if d["date"]==a["latest"]),None)
    if current and not current["closed"]:
        # Sample a full day's advance and subtract the progress already observed.
        # Missing previous-day reference: wait for the next completed day.
        if current.get("advance") is None: return None
        future.append((dt,current["advance"]))
    while dt<limit:
        dt+=timedelta(days=1)
        if session_day(dt,calendar): future.append((dt,0))
    pools={w:distribution(history,w) for w in range(7)}
    rng=random.Random(20261019); hits=Counter()
    for _ in range(simulations):
        remaining=target-a["frontier"]
        # Shared trajectory uncertainty prevents treating the estimated mean as exact.
        drift=rng.triangular(.85,1.15,1)
        for dt,consumed in future:
            values,weights=pools[dt.weekday()]
            advance=max(0,rng.choices(values,weights=weights,k=1)[0]*drift-consumed)
            remaining-=advance
            if remaining<=0:
                hits[dt.date().isoformat()]+=1
                break
    if sum(hits.values())<simulations*.95: return None
    top=sorted(hits,key=lambda d:(-hits[d],d))[:2]
    return {"candidates":top,"counts":dict(hits),"simulations":simulations}

def forecast(a,target):
    result=forecast_details(a,target)
    if not result: return "Sin estimación futura fiable"
    # These are the two most frequent dates in the model, not interval endpoints
    # and not a calibrated statement that other dates are impossible.
    dates=[datetime.fromisoformat(d).strftime("%d/%m/%Y") for d in sorted(result["candidates"])]
    return " o ".join(dates)+" · días candidatos"

def build(source,out):
    a=analyze(parse(source)); target=os.environ.get("TARGET_NUMBER")
    public={"updated":a["latest"],"last":a["last_finished"],"complete":a["complete"],"means":a["means"],"forecast":"Reservada por privacidad", "mode":"Histórico importado"}
    # A secret matching a public observation must never be emitted.
    if target and public["last"]==int(target): public["last"]=None
    if os.environ.get("LIVE_MODE")=="1": public["mode"]="Consulta oficial verificada"
    if target:
        private=forecast(a,int(target))
        if os.environ.get("PRIVATE_REPORT"): Path(os.environ["PRIVATE_REPORT"]).write_text(private)
        if os.environ.get("PUBLISH_COARSE_FORECAST")=="true": public["forecast"]=private
    out=Path(out); out.mkdir(exist_ok=True)
    payload=json.dumps(public,ensure_ascii=False)
    if target and target in payload: raise ValueError("Publicación bloqueada por privacidad")
    (out/"data.js").write_text("window.SHURMAN="+payload+";\n")
    return a

if __name__=="__main__":
    import sys
    build(Path(sys.argv[1]).read_text(),sys.argv[2])
