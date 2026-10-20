import urllib.request, urllib.parse, re, json, os
from engine import build
BASE="https://www.registradores.org/el-colegio/oposiciones/seguimiento-oposicion?idOposicion=6"
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ShurmanAggregate/1.0 (daily statistics)","Accept":"application/json,text/html"})
    with urllib.request.urlopen(req,timeout=30) as r:
        if urllib.parse.urlparse(r.url).hostname!="www.registradores.org": raise ValueError("Redirección inesperada")
        data=r.read(5000001)
        if len(data)>5000000: raise ValueError("Respuesta excesiva")
        return data.decode("utf-8")
if __name__=="__main__":
    try:
        page=get(BASE)
        endpoint=re.search(r"url: '(https:[^']+resource_id[^']+)'",page)[1]
        if urllib.parse.urlparse(endpoint).hostname!="www.registradores.org": raise ValueError()
        query=urllib.parse.urlencode({"draw":1,"start":0,"length":2000,"columns[0][data]":"fecha","columns[1][data]":"mensaje","order[0][column]":0,"order[0][dir]":"desc"})
        source=get(endpoint+"&"+query)
        os.environ["LIVE_MODE"]="1"
        report=build(source,"public")
        print("Parte oficial:", report["latest"],
              "última entrada:",report["last_entered"],
              "último desenlace:",report["last_finished"],
              "avance:",report["recent"]["advance"] if report["recent"] else None)
    except Exception:
        raise SystemExit("Actualización detenida; se conserva la publicación anterior. Revisar fuente y cobertura. Sin reintentos automáticos.")
