"""Programador en horario de Madrid; cuatro oportunidades de ejecución por hora.
GitHub Actions no garantiza que cada trigger se produzca en hora.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
PUBLISHED_DATA = "https://elgrangelmini.github.io/007/data.js"

def local_hour(dt):
    return dt.astimezone(MADRID).replace(minute=0, second=0, microsecond=0)

def should_run(event_name, now, checked_at=None):
    if event_name != "schedule":
        return True, "Ejecución manual o modificación de código"
    if now.tzinfo is None:
        raise ValueError("Fecha sin zona horaria")
    local = now.astimezone(MADRID)
    if not 8 <= local.hour <= 21:
        return False, "Fuera de horario (08:00-21:59 Madrid)"
    if checked_at is not None and checked_at.tzinfo is not None:
        age=(now-checked_at).total_seconds()
        if 0 <= age < 3600 and local_hour(now)==local_hour(checked_at):
            return False, "Ya se ha publicado durante esta hora"
    return True, "Actualizar durante esta hora"

def previous_publication():
    try:
        url=PUBLISHED_DATA+"?gate="+str(int(datetime.now(timezone.utc).timestamp()))
        request=urllib.request.Request(url,headers={
            "User-Agent":"ShurmanScheduler/1.0","Cache-Control":"no-cache"})
        with urllib.request.urlopen(request,timeout=12) as response:
            data=response.read(100000).decode("utf-8")
        data=re.sub(r"^\s*window\.SHURMAN\s*=\s*","",data)
        data=re.sub(r";\s*$","",data)
        return datetime.fromisoformat(json.loads(data)["checked_at"])
    except (OSError, ValueError, KeyError) as error:
        print("No se puede consultar última publicación:",type(error).__name__)
        return None

def main():
    event=os.environ.get("GITHUB_EVENT_NAME","")
    now=datetime.now(timezone.utc)
    previous=previous_publication() if event=="schedule" else None
    execute,reason=should_run(event,now,previous)
    print("Hora Madrid:",now.astimezone(MADRID).isoformat(timespec="seconds"))
    print("Última publicación:",previous.isoformat() if previous else "Desconocida")
    print("Decisión:",execute,"-",reason)
    output=os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a",encoding="utf-8") as file:
            file.write("should_run="+str(execute).lower()+"\n")

if __name__=="__main__":
    main()
