import json, re, html, os, statistics, math, random
from collections import Counter
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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
    days={}; latest=None; frontier=None; last_finished=None; last_entered=None
    for r in rows:
        dt=datetime.strptime(r["fecha"],"%H:%M:%S %d-%m-%Y"); day=dt.date().isoformat(); latest=day
        d=days.setdefault(day,{"date":day,"entries":set(),"finished":set(),"withdrawn":set(),"excluded":set(),"absent":set(),"closed":False,"started":False,"frontier":None})
        s=html.unescape(re.sub("<[^>]+>"," ",r["mensaje"])).lower()
        if re.search(r"comienza la sesión|inicia el primer ejercicio",s): d["started"]=True
        if "finaliza la sesión" in s: d["closed"]=True
        m=re.match(r"(?:entra|termina|se retira|se nombra|el)\s+(?:(?:el|al)\s+)?n\s*[º°o.]?\s*(\d+)",s)
        if not m: continue
        n=int(m[1]); event=False
        if s.startswith("entra"): d["entries"].add(n); last_entered=n; event=True
        if s.startswith("termina"): d["finished"].add(n); last_finished=n; event=True
        if "se retira" in s: d["withdrawn"].add(n); last_finished=n; event=True
        if "excluido" in s: d["excluded"].add(n); last_finished=n; event=True
        if "no presente" in s: d["absent"].add(n); event=True
        if event: frontier=max(frontier or n,n)
        d["frontier"]=frontier
    result=[]; previous=None
    for d in days.values():
        if not any(d[k] for k in ("entries","finished","withdrawn","excluded","absent")):
            continue
        f=d["frontier"]
        advance=None if previous is None else max(0,f-previous)
        # El avance neto incluye TODOS los puestos consumidos aunque no
        # hayan efectuado el ejercicio. Los huecos solo son una aproximación
        # a números sin entrada observada, no ausencias definitivas.
        entries_in_range=(len({n for n in d["entries"] if previous < n <= f})
                          if previous is not None else None)
        without_entry=(max(0,advance-entries_in_range)
                       if advance is not None else None)
        result.append({**{k:len(d[k]) for k in ("entries","finished","withdrawn","excluded","absent")},
                       "date":d["date"],"closed":d["closed"] and d["started"],
                       "advance":advance,"without_entry":without_entry,
                       "entries_in_range":entries_in_range,"frontier":f})
        previous=f
    complete=[d for d in result if d["closed"]]
    means={k:round(statistics.mean(d[k] for d in complete),2) if complete else None for k in ("entries","finished","withdrawn")}
    for key in ("advance","without_entry"):
        valid=[d[key] for d in complete if d[key] is not None]
        means[key]=round(statistics.mean(valid),2) if valid else None
    # Instantánea de la última jornada, incluso cuando aún no ha terminado.
    # Las medias anteriores siguen utilizando exclusivamente sesiones cerradas.
    latest_session=next((d for d in reversed(list(days.values())) if
                         d["started"] or d["entries"] or d["finished"] or d["withdrawn"]),None)
    recent=None
    if latest_session is not None:
        matching=next((d for d in reversed(result) if d["date"]==latest_session["date"]),None)
        advance=matching["advance"] if matching else (0 if result else None)
        recent={"date":latest_session["date"],
                "closed":bool(latest_session["closed"] and latest_session["started"]),
                "entries":len(latest_session["entries"]),
                "finished":len(latest_session["finished"]),
                "withdrawn":len(latest_session["withdrawn"]),
                "absent":len(latest_session["absent"]),
                "advance":advance,
                "without_entry":matching["without_entry"] if matching else (0 if result else None)}
    return {"days":result,"means":means,"recent":recent,"latest":latest,"frontier":frontier,"last_finished":last_finished,"last_entered":last_entered,"complete":len(complete),"calendar":read_calendar(rows)}

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

def preparation_dates(a,result):
    # Planning policy requested by the owner: use an early quantile rather than
    # present modal dates as a deadline. This changes the decision, not the model.
    # The empirical 20th percentile is not a calibrated real-world probability.
    threshold=result["simulations"]*.20
    cumulative=0; first=None
    for day,count in sorted(result["counts"].items()):
        cumulative+=count
        if cumulative>=threshold:
            first=day
            break
    if first is None: return []
    dates=[first]; dt=datetime.fromisoformat(first)
    while dt<datetime(2026,11,30):
        dt+=timedelta(days=1)
        if session_day(dt,a.get("calendar",{})):
            dates.append(dt.date().isoformat())
            break
    return dates

def forecast(a,target):
    result=forecast_details(a,target)
    if not result: return "Sin estimación futura fiable"
    dates=[datetime.fromisoformat(d).strftime("%d/%m/%Y") for d in preparation_dates(a,result)]
    return " / ".join(dates)+" · margen para ir preparado"

def probability_cards(result):
    if not result: return []
    counts=result["counts"]; total=result["simulations"]
    top=sorted(counts,key=lambda d:(-counts[d],d))[:5]
    # Include uncompleted trajectories in Other, never silently renormalize.
    buckets=[counts[d] for d in top]+[total-sum(counts[d] for d in top)]
    units=[n*1000//total for n in buckets]
    remainder=1000-sum(units)
    order=sorted(range(len(buckets)),key=lambda i: (-(buckets[i]*1000%total),i))
    for i in order[:remainder]: units[i]+=1
    cards=[{"date":d,"percent":units[i]/10} for i,d in enumerate(top)]
    cards.sort(key=lambda c:c["date"])
    cards.append({"date":None,"percent":units[-1]/10})
    return cards

def next_call(rows,after,target=None):
    calls={}
    for r in rows:
        text=html.unescape(re.sub("<[^>]+>"," ",r["mensaje"])).lower()
        if "convocatoria" not in text: continue
        matches=list(re.finditer(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})",text))
        for i,m in enumerate(matches):
            try: day=datetime(int(m[3]),int(m[2]),int(m[1])).date().isoformat()
            except ValueError: continue
            segment=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
            bounds=re.search(r"del\s+n\s*[º°o.]?\s*(\d+)\s+al\s+n\s*[º°o.]?\s*(\d+)",segment)
            if not bounds: continue
            low,high=map(int,bounds.groups())
            if low>high: continue
            hour=re.search(r"(?:a las\s+)?(\d{1,2})[:.](\d{2})\s*(?:h|horas)",segment)
            calls[day]={"date":day,"from":low,"to":high,"time":f"{int(hour[1]):02d}:{hour[2]}" if hour else None}
    future=[day for day in calls if day>after]
    if not future: return None
    call=calls[min(future)]
    # Do not disclose a literal secret even if it coincides with a range endpoint.
    if target and int(target) in (call["from"],call["to"]):
        call["from"]=None;call["to"]=None
    return call

def build(source,out):
    rows=parse(source); a=analyze(rows); target=os.environ.get("TARGET_NUMBER")
    # La fecha del último parte es distinta de la última consulta realizada.
    # Ambas se generan en el servidor; nunca exponen el objetivo protegido.
    source_last_at=datetime.strptime(rows[-1]["fecha"],"%H:%M:%S %d-%m-%Y").replace(tzinfo=ZoneInfo("Europe/Madrid")).isoformat(timespec="seconds")
    checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds")
    public={"checked_at":checked_at,"source_last_at":source_last_at,"updated":a["latest"],"last":a["last_finished"],"last_entered":a["last_entered"],"complete":a["complete"],"means":a["means"],"recent":a["recent"],"forecast":"Reservada por privacidad", "mode":"Histórico importado","probabilities":[],"next_call":next_call(rows,a["latest"],target)}
    # A secret matching a public observation must never be emitted.
    if target and public["last"]==int(target): public["last"]=None
    if target and public["last_entered"]==int(target): public["last_entered"]=None
    if os.environ.get("LIVE_MODE")=="1": public["mode"]="Consulta oficial verificada"
    if target:
        private=forecast(a,int(target))
        if os.environ.get("PRIVATE_REPORT"): Path(os.environ["PRIVATE_REPORT"]).write_text(private)
        if os.environ.get("PUBLISH_COARSE_FORECAST")=="true":
            public["forecast"]=private
            public["probabilities"]=probability_cards(forecast_details(a,int(target)))
    out=Path(out); out.mkdir(exist_ok=True)
    payload=json.dumps(public,ensure_ascii=False)
    if target and target in payload: raise ValueError("Publicación bloqueada por privacidad")
    (out/"data.js").write_text("window.SHURMAN="+payload+";\n")
    return a

if __name__=="__main__":
    import sys
    build(Path(sys.argv[1]).read_text(),sys.argv[2])
