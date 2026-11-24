"""Segundo llamamiento: modelo conservador con referencia histórica de 2024.

Los valores históricos son avances de numeración por jornada (no opositores examinados),
extraídos del JSON completo de la oposición 2024-2025, entre 18/11 y 11/12/2024.
No almacenar ni publicar el número secreto del usuario en este módulo.
"""
import re, html, random
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta

HISTORICAL_ADVANCES = (55,40,61,69,62,72,34,38,46,62,41,41)
MADRID_HOLIDAYS_2026 = {"2026-12-07","2026-12-08","2026-12-25"}
MADRID_HOLIDAYS_2027 = {"2027-01-01","2027-01-06"}
START_MARKERS = ("comienza el segundo llamamiento del primer ejercicio",
                 "comienza el llamamiento segundo del primer ejercicio")
NUMBER_RE = re.compile(r"(?:n\s*[º°o.]?\s*|número\s*)(\d{1,4})", re.I)

def clean(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).lower().split())

def second_round_start(rows):
    for row in rows:
        message=clean(row["mensaje"])
        if any(marker in message for marker in START_MARKERS):
            return datetime.strptime(row["fecha"], "%H:%M:%S %d-%m-%Y")
    return None

def second_round_data(rows):
    marker=second_round_start(rows)
    if marker is None:
        return None
    daily=defaultdict(lambda: {"entries":set(), "finished":set(), "withdrawn":set(),
                                "absent":set(), "excluded":set(), "observed":set(),
                                "started":False, "closed":False})
    last_entered=last_finished=None
    for row in rows:
        dt=datetime.strptime(row["fecha"], "%H:%M:%S %d-%m-%Y")
        if dt < marker: continue
        msg=clean(row["mensaje"])
        day=dt.date().isoformat()
        record=daily[day]
        if "comienza la sesión" in msg or "comienza el segundo llamamiento" in msg:
            record["started"]=True
        if "finaliza la sesión" in msg:
            record["closed"]=True
        if "convocatori" in msg or "el tribunal comunica" in msg or "opositores en la sala" in msg:
            continue
        numbers=[int(n) for n in NUMBER_RE.findall(msg)]
        numbers=[n for n in numbers if 1<=n<1000]
        if not numbers:
            continue
        begins=msg.startswith(("entra ", "han entrado ", "ha entrado "))
        finishes=msg.startswith("termina ")
        withdraws=("se retira" in msg or "se ha retirado" in msg)
        absent=("no presente" in msg and ("se nombra" in msg or "se llama" in msg))
        excluded="excluido" in msg or "excluida" in msg
        called=("se ha llamado hasta" in msg or "se llama hasta" in msg)
        if not (begins or finishes or withdraws or absent or excluded or called):
            continue
        record["observed"].update(numbers)
        if begins:
            record["entries"].update(numbers)
            last_entered=max(numbers)
        if finishes:
            record["finished"].update(numbers)
            last_finished=max(numbers)
        if withdraws:
            record["withdrawn"].update(numbers)
            last_finished=max(numbers)
        if absent:
            record["absent"].update(numbers)
        if excluded:
            record["excluded"].update(numbers)
            last_finished=max(numbers)
    daily_rows=[]
    previous=0
    for day, record in sorted(daily.items()):
        if not record["observed"]:
            continue
        high=max(record["observed"])
        next_high=max(previous, high)
        advance=next_high-previous
        entries_in_range=len({n for n in record["entries"] if previous<n<=next_high})
        daily_rows.append({"date":day,"frontier":next_high,"advance":advance,
                           "entries":len(record["entries"]),"finished":len(record["finished"]),
                           "withdrawn":len(record["withdrawn"]),"absent":len(record["absent"]),
                           "without_entry":max(0,advance-entries_in_range),
                           "closed":record["closed"]})
        previous=next_high
    if not daily_rows: return None
    closed=[d for d in daily_rows if d["closed"]]
    keys=("entries","finished","withdrawn","advance","without_entry")
    means={key:round(sum(d[key] for d in closed)/len(closed),2) if closed else None for key in keys}
    recent=dict(daily_rows[-1])
    return {"round":"second","start":marker.isoformat(),"frontier":previous,
            "latest":max(daily),"days":daily_rows,"recent":recent,
            "means":means,"complete":len(closed),
            "last_entered":last_entered,"last_finished":last_finished,
            "historical_reference_days":len(HISTORICAL_ADVANCES)}

# Calendario comunicado para la semana del 7 al 13 de diciembre:
# únicamente se celebrará sesión el miércoles 9.
# Evitar que la pauta habitual o una convocatoria anterior reabra esa semana.
EXCEPTIONAL_WEEK_2026 = {f"2026-12-{d:02d}" for d in range(7,14)}
EXCEPTIONAL_SESSION_2026 = "2026-12-09"

def active_day(day, explicit):
    key=day.isoformat()
    if key in EXCEPTIONAL_WEEK_2026:
        return key == EXCEPTIONAL_SESSION_2026
    if key in explicit: return True
    if key in MADRID_HOLIDAYS_2026 or key in MADRID_HOLIDAYS_2027: return False
    return day.weekday() in (0,1,2,3)

def simulate(data,target,announced=None,simulations=8000):
    if data is None or not target or target<=data["frontier"]:
        return None
    announced=announced or []
    caps={r["date"]:r["to"] for r in announced if r.get("to") is not None}
    explicit=set(caps)
    anchor=date.fromisoformat(data["latest"])
    until=anchor+timedelta(days=100)
    future=[]
    cur=anchor
    while cur<until:
        cur+=timedelta(days=1)
        if active_day(cur,explicit):future.append(cur)
    # La primera tarde fue parcial. Ignorarla al entrenar el ritmo actual.
    recent=[d["advance"] for d in data["days"][1:] if d["closed"] and d["advance"]>0]
    current_weight=min(.70, max(0, (len(recent)-2)/9))
    rng=random.Random(20261118)
    hits=Counter()
    for _ in range(simulations):
        pos=data["frontier"]
        drift=rng.triangular(.82,1.20,1)
        for day in future:
            if recent and rng.random()<current_weight:
                amount=rng.choice(recent)
            else:
                amount=rng.choice(HISTORICAL_ADVANCES)
            delta=max(0,round(amount*drift))
            cap=caps.get(day.isoformat())
            if cap is not None:
                delta=min(delta,max(0,cap-pos))
            pos+=delta
            if pos>=target:
                hits[day.isoformat()]+=1
                break
    if not hits:
        return None
    ordered=sorted(hits.items())
    def quantile(q):
        threshold=simulations*q
        count=0
        for key,n in ordered:
            count+=n
            if count>=threshold:return key
        return None
    return {"counts":dict(hits),"simulations":simulations,
            "early":quantile(.2),"central":quantile(.5),"late":quantile(.8),
            "current_weight":round(current_weight,2),"coverage":round(sum(hits.values())/simulations,3)}

def summarize(sim):
    if not sim or not sim["central"]:
        return "Estimación en elaboración · datos insuficientes"
    def fmt(day):
        return datetime.fromisoformat(day).strftime("%d/%m/%Y") if day else "sin fecha"
    return (fmt(sim["central"])+" · referencia central orientativa"
            +" · intervalo "+fmt(sim["early"])+" – "+fmt(sim["late"]))
