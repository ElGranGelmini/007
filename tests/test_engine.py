import unittest,sys,json,os,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"server"))
from engine import parse,analyze,build

def sample():
    events=["Comienza la sesión.","Entra nº 2 y se retira.","Termina el nº 3", "Se nombra al n º 5 no presente.","Finaliza la sesión."]
    return [{"fecha":f"10:0{i}:00 14-09-2026","idNotificacion":i,"idOposicion":6,"mensaje":s} for i,s in enumerate(events)]
class Tests(unittest.TestCase):
    def test_events(self):
        a=analyze(sample()+[{"fecha":"10:00:00 15-09-2026","idNotificacion":9,"idOposicion":6,"mensaje":"Entra nº 9"}]);d=a["days"][0]
        self.assertEqual((d["entries"],d["finished"],d["withdrawn"],d["absent"]),(1,1,1,1))
        self.assertEqual(a["complete"],1);self.assertEqual(a["frontier"],9)
    def test_duplicate(self):
        rows=sample(); self.assertEqual(len(parse(json.dumps({"data":{"data":rows+[rows[0]],"recordsFiltered":6}}))),5)
    def test_truncated(self):
        with self.assertRaises(ValueError): parse(json.dumps({"data":{"data":sample(),"recordsFiltered":99}}))
    def test_future_notice(self):
        rows=sample()+[{"fecha":"11:00:00 14-09-2026","idNotificacion":8,"idOposicion":6,"mensaje":"Cuando finalice su ejercicio nº 50 se suspenderá la sesión"}]
        self.assertEqual(analyze(rows)["days"][0]["finished"],1)
if __name__=="__main__":unittest.main()
