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
    def test_completed_current_day_call_not_marked_next(self):
        from engine import announced_calls
        rows=sample()+[
            {"fecha":"11:00:00 21-10-2026","idNotificacion":222,"idOposicion":6,
             "mensaje":"Convocatoria miércoles 21/10/2026 a las 09:30 horas del n º 385 al n º 411."},
            {"fecha":"12:00:00 21-10-2026","idNotificacion":223,"idOposicion":6,
             "mensaje":"Convocatoria lunes 26/10/2026 a las 10:00 horas del n º 412 al n º 450."}
        ]
        calls=announced_calls(rows,"2026-10-21",frontier=411)
        self.assertEqual([c["date"] for c in calls],["2026-10-26"])
        self.assertEqual(calls[0]["to"],450)
    def test_second_round_restart_and_phase_boundary(self):
        from second_round import second_round_data
        def row(i, when, msg):
            return {"fecha":when,"idNotificacion":i,"idOposicion":6,"mensaje":msg}
        records=[
            row(1,"10:00:00 17-11-2026","Entra n º 661"),
            row(2,"14:18:48 18-11-2026","Finaliza el primer llamamiento del primer ejercicio."),
            row(3,"15:34:52 18-11-2026","Comienza el segundo llamamiento del primer ejercicio."),
            row(4,"16:00:00 18-11-2026","Entra n º 7"),
            row(5,"16:20:00 18-11-2026","Se retira n º 7"),
            row(6,"21:22:50 18-11-2026","Finaliza la sesión."),
            row(7,"09:21:48 19-11-2026","Buenos días, comienza la sesión."),
            row(8,"09:22:59 19-11-2026","Entra n º 36 y se retira."),
            row(9,"11:55:25 19-11-2026","Entra n º 43 y se retira."),
            row(10,"12:28:29 19-11-2026","Finaliza la sesión.")
        ]
        second=second_round_data(records)
        self.assertEqual(second["frontier"],43)
        self.assertEqual([day["advance"] for day in second["days"]],[7,36])
        self.assertEqual(second["complete"],2)
        self.assertEqual(second["last_finished"],43)
    def test_second_round_simulation_respects_official_caps(self):
        from second_round import simulate, second_round_data, HISTORICAL_ADVANCES
        self.assertEqual(sum(HISTORICAL_ADVANCES),621)
        rows=[
            {"fecha":"15:34:52 18-11-2026","idNotificacion":1,"idOposicion":6,"mensaje":"Comienza el segundo llamamiento del primer ejercicio."},
            {"fecha":"18:00:00 18-11-2026","idNotificacion":2,"idOposicion":6,"mensaje":"Entra n º 27 y se retira."},
            {"fecha":"21:00:00 18-11-2026","idNotificacion":3,"idOposicion":6,"mensaje":"Finaliza la sesión."},
            {"fecha":"09:30:00 19-11-2026","idNotificacion":4,"idOposicion":6,"mensaje":"Buenos días, comienza la sesión."},
            {"fecha":"12:00:00 19-11-2026","idNotificacion":5,"idOposicion":6,"mensaje":"Entra n º 43 y se retira."},
            {"fecha":"12:20:00 19-11-2026","idNotificacion":6,"idOposicion":6,"mensaje":"Finaliza la sesión."}
        ]
        current=second_round_data(rows)
        simulated=simulate(current,600,announced=[{"date":"2026-11-23","to":96},
                                                    {"date":"2026-11-24","to":146},
                                                    {"date":"2026-11-25","to":207},
                                                    {"date":"2026-11-26","to":229}],simulations=800)
        self.assertTrue(simulated["central"])
        self.assertGreaterEqual(simulated["central"],"2026-11-27")
        self.assertGreaterEqual(simulated["coverage"],0.95)
if __name__=="__main__":unittest.main()
