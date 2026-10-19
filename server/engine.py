import json, re, html, os, statistics, math
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
        result.append({**{k:len(d[k]) for k in ("entries","finished","withdrawn","excluded","absent")},"date":d["date"],"closed":d["closed"] and d["started"],"advance":advance})
    complete=[d for d in result if d["closed"]]
    means={k:round(statistics.mean(d[k] for d in complete),2) if complete else None for k in ("entries","finished","withdrawn")}
    advances=[d["advance"] for d in complete if d["advance"] is not None and d["advance"]>0]
    means["advance"]=round(statistics.mean(advances),2) if advances else None
    return {"days":result,"means":means,"latest":latest,"frontier":frontier,"last_finished":last_finished,"complete":len(complete)}

def forecast(a,target):
    # Scenario envelope, not a calibrated confidence interval. No target-dependent public fields.
    rates=[d["advance"] for d in a["days"] if d["closed"] and d["advance"] and d["advance"]>0]
    if len(rates)<5 or target<=a["frontier"]: return "Sin estimación futura fiable"
    rates.sort(); slow=rates[len(rates)//4]; fast=rates[3*len(rates)//4]
    dates=[]
    for rate in (fast,slow):
        sessions=math.ceil((target-a["frontier"])/rate); dt=datetime.fromisoformat(a["latest"])
        # Observed Mon-Wed cadence; explicitly a scenario, not an official calendar.
        while sessions:
            dt+=timedelta(days=1)
            if dt.weekday() in (0,1,2) or dt.date().isoformat() in ("2026-11-05","2026-11-12","2026-11-19"): sessions-=1
        dates.append(dt)
    labels=[d.strftime("%d/%m/%Y") for d in dates]
    return " o ".join(dict.fromkeys(labels)) + " · escenarios orientativos"

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
