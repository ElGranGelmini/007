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
    def test_recent_session_excludes_incomplete_day_from_historical_means(self):
        rows=sample()+[
            {"fecha":"09:30:00 15-09-2026","idNotificacion":20,"idOposicion":6,"mensaje":"Comienza la sesión."},
            {"fecha":"10:00:00 15-09-2026","idNotificacion":21,"idOposicion":6,"mensaje":"Entra n º 9"},
            {"fecha":"10:10:00 15-09-2026","idNotificacion":22,"idOposicion":6,"mensaje":"Se retira n º 9."}
        ]
        data=analyze(rows)
        self.assertEqual(data["complete"],1)
        self.assertEqual(data["recent"]["date"],"2026-09-15")
        self.assertFalse(data["recent"]["closed"])
        self.assertEqual(data["recent"]["entries"],1)
        self.assertEqual(data["recent"]["withdrawn"],1)
        self.assertEqual(data["recent"]["advance"],4)
        self.assertEqual(data["means"]["entries"],1.0)
    def test_recent_session_closed(self):
        rows=sample()+[
            {"fecha":"09:30:00 15-09-2026","idNotificacion":20,"idOposicion":6,"mensaje":"Comienza la sesión."},
            {"fecha":"10:00:00 15-09-2026","idNotificacion":21,"idOposicion":6,"mensaje":"Entra n º 9"},
            {"fecha":"10:10:00 15-09-2026","idNotificacion":22,"idOposicion":6,"mensaje":"Se retira n º 9."},
            {"fecha":"17:00:00 15-09-2026","idNotificacion":23,"idOposicion":6,"mensaje":"Finaliza la sesión."}
        ]
        data=analyze(rows)
        self.assertEqual(data["complete"],2)
        self.assertTrue(data["recent"]["closed"])
        self.assertEqual(data["recent"]["withdrawn"],1)
    def test_open_session_before_first_entry(self):
        rows=sample()+[
            {"fecha":"09:30:00 15-09-2026","idNotificacion":20,"idOposicion":6,"mensaje":"Comienza la sesión."}
        ]
        data=analyze(rows)
        self.assertEqual(data["recent"]["entries"],0)
        self.assertEqual(data["recent"]["date"],"2026-09-15")
        self.assertEqual(data["complete"],1)
    def test_unrecorded_numbers_counted_in_progress_not_as_confirmed_absences(self):
        rows=sample()+[
            {"fecha":"09:30:00 15-09-2026","idNotificacion":20,"idOposicion":6,"mensaje":"Comienza la sesión."},
            {"fecha":"10:00:00 15-09-2026","idNotificacion":21,"idOposicion":6,"mensaje":"Entra n º 9"},
            {"fecha":"10:05:00 15-09-2026","idNotificacion":22,"idOposicion":6,"mensaje":"Se retira n º 9."},
            {"fecha":"10:30:00 15-09-2026","idNotificacion":23,"idOposicion":6,"mensaje":"Entra n º 14"},
            {"fecha":"11:30:00 15-09-2026","idNotificacion":24,"idOposicion":6,"mensaje":"Termina n º 14"},
            {"fecha":"18:00:00 15-09-2026","idNotificacion":25,"idOposicion":6,"mensaje":"Finaliza la sesión."}
        ]
        data=analyze(rows)
        self.assertEqual(data["last_entered"],14)
        self.assertEqual(data["last_finished"],14)
        self.assertEqual(data["recent"]["entries"],2)
        self.assertEqual(data["recent"]["advance"],9)
        self.assertEqual(data["recent"]["without_entry"],7)
        self.assertEqual(data["means"]["advance"],9)
        self.assertEqual(data["means"]["without_entry"],7)
    def test_explicit_absent_moves_frontier_without_exam(self):
        rows=sample()+[
            {"fecha":"09:30:00 15-09-2026","idNotificacion":20,"idOposicion":6,"mensaje":"Comienza la sesión."},
            {"fecha":"10:00:00 15-09-2026","idNotificacion":21,"idOposicion":6,"mensaje":"Se nombra al n º 12 no presente."},
            {"fecha":"11:00:00 15-09-2026","idNotificacion":22,"idOposicion":6,"mensaje":"Finaliza la sesión."}
        ]
        data=analyze(rows)
        self.assertEqual(data["frontier"],12)
        self.assertEqual(data["recent"]["entries"],0)
        self.assertEqual(data["recent"]["absent"],1)
        self.assertEqual(data["recent"]["advance"],7)
        self.assertEqual(data["recent"]["without_entry"],7)
    def test_metric_ids_match_client_rendering(self):
        root=Path(__file__).resolve().parents[1]
        webpage=(root/"public"/"index.html").read_text()
        client=(root/"public"/"app.js").read_text()
        self.assertIn('id="without-entry"',webpage)
        self.assertIn('key === "without_entry" ? "without-entry" : key',client)
        self.assertIn('put(elementId, typeof number === "number"',client)
    def test_multiday_next_week_calls(self):
        from engine import announced_calls
        rows=sample()+[
            {"fecha":"12:00:00 21-10-2026","idNotificacion":100,"idOposicion":6,
             "mensaje":"Convocatoria lunes 26/10/2026 a las 09:30 horas del n º 412 al n º 437. Martes 27/10/2026 a las 10:00 horas del n º 438 al n º 465."},
            {"fecha":"12:30:00 21-10-2026","idNotificacion":101,"idOposicion":6,
             "mensaje":"Convocatoria miércoles 28/10/2026 a las 09:30 horas del n º 466 al n º 490."}
        ]
        calls=announced_calls(rows,"2026-10-21")
        self.assertEqual([c["date"] for c in calls],["2026-10-26","2026-10-27","2026-10-28"])
        self.assertEqual((calls[0]["from"],calls[0]["to"],calls[0]["time"]),(412,437,"09:30"))
        self.assertEqual((calls[2]["from"],calls[2]["to"]),(466,490))
    def test_target_range_is_redacted(self):
        from engine import announced_calls
        rows=sample()+[{"fecha":"12:00:00 21-10-2026","idNotificacion":200,
                        "idOposicion":6,"mensaje":"Convocatoria lunes 26/10/2026 a las 9:30 horas del n º 600 al n º 620."}]
        call=announced_calls(rows,"2026-10-21",target="607")[0]
        self.assertIsNone(call["from"])
        self.assertIsNone(call["to"])
if __name__=="__main__":unittest.main()
