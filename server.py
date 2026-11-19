"""Operator local server. Run:  python server.py   then open http://127.0.0.1:8123"""
import csv
import glob
import io
import json
import os
import re
import sys
import threading
import time
import urllib.request
import webbrowser
from datetime import datetime, timezone

from flask import Flask, Response, jsonify, request, send_file, send_from_directory

from data import AIRCRAFT, AIRPORTS
from flightops import FlightTracker, fetch_simbrief, simbrief_prefill
from game import Game, GameError
from simbridge import SimBridge

def _base():
    """Directory holding bundled resources (differs inside a PyInstaller build)."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _home():
    """Writable directory for saves: next to the executable when frozen."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


HERE = _base()
SAVE_DIR = os.path.join(_home(), "save")
PORT = int(os.environ.get("OPERATOR_PORT", "8123"))
HOST = os.environ.get("OPERATOR_HOST", "127.0.0.1")
os.makedirs(SAVE_DIR, exist_ok=True)

app = Flask(__name__, static_folder=os.path.join(HERE, "static"), static_url_path="/static")
app.json.sort_keys = False
bridge = SimBridge()
tracker = None
lock = threading.Lock()


def _current_slot():
    p = os.path.join(SAVE_DIR, "current.txt")
    if os.path.exists(p):
        return open(p).read().strip()
    # keep opening a save made before the rename
    if not os.path.exists(os.path.join(SAVE_DIR, "operator.db")) and os.path.exists(os.path.join(SAVE_DIR, "ferryops.db")):
        return "ferryops"
    return "operator"


def _set_slot(name):
    with open(os.path.join(SAVE_DIR, "current.txt"), "w") as fh:
        fh.write(name)


game = Game(os.path.join(SAVE_DIR, _current_slot() + ".db"))


def _tracker_loop():
    global tracker
    ticks = 0
    while True:
        time.sleep(1.0)
        ticks += 1
        try:
            with lock:
                f = game.state and game.state.get("active_flight")
                if f and f.get("status") == "Tracking" and tracker is not None:
                    tracker.update(bridge.get())
                    # keep a snapshot in the save so a crash or restart mid-flight is recoverable
                    if ticks % 20 == 0:
                        f["tracker_state"] = tracker.serialize()
                        game.save()
        except Exception as e:
            print("tracker loop:", e)


def _restore_tracker():
    """Rebuild an interrupted flight's tracker from the save."""
    global tracker
    f = game.state and game.state.get("active_flight")
    if not f or f.get("status") != "Tracking" or tracker is not None:
        return
    st = f.get("tracker_state")
    if st:
        tracker = FlightTracker.restore(st, f, vmo=AIRCRAFT[f["type"]]["vmo"], restrictions=f.get("restrictions") or {},
                                        vref=((f.get("perf") or {}).get("landing") or {}).get("vref"))
        _log(f"resumed tracking {f['flight_number']} from the save ({st.get('samples', 0)} samples, phase {st.get('phase')})")
    else:
        f["status"] = "Planned"
        game.save()
        _log(f"{f['flight_number']} was tracking but no data survived the restart; returned to Planned")


threading.Thread(target=_tracker_loop, daemon=True).start()


def ok(**kw):
    return jsonify(dict(ok=True, **kw))


@app.errorhandler(GameError)
def _game_error(e):
    return jsonify(dict(ok=False, error=str(e))), 400


@app.errorhandler(Exception)
def _any_error(e):
    import traceback
    traceback.print_exc()
    return jsonify(dict(ok=False, error=f"{type(e).__name__}: {e}")), 500


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


_AIRPORTS_JSON = json.dumps({k: dict(name=a["name"], city=a["city"], country=a["country"], lat=a["lat"], lon=a["lon"], large=bool(a.get("large"))) for k, a in AIRPORTS.items()})


@app.get("/api/airports")
def airports():
    return Response(_AIRPORTS_JSON, mimetype="application/json", headers={"Cache-Control": "max-age=3600"})


@app.post("/api/inbox/read")
def inbox_read():
    with lock:
        game.mark_read(request.json.get("id"))
    return ok()


@app.route("/flight")
def flight_window():
    return send_from_directory(app.static_folder, "flight.html")


@app.route("/api/state")
def state():
    with lock:
        if game.state and game.state["company"].get("clock_mode") == "real":
            now = datetime.utcnow().replace(second=0, microsecond=0)
            af = game.state.get("active_flight")
            if now > game.now() and not (af and af.get("status") == "Tracking"):
                game.advance_to(now)
        v = game.view()
    v["sim"] = dict(connected=bridge.connected, source=bridge.source, status=bridge.status)
    v["slot"] = _current_slot()
    return jsonify(v)


# ------------------------------------------------------------------ company / settings
@app.post("/api/company/new")
def company_new():
    d = request.json
    with lock:
        game.new_company(d["name"], d["code"], d["base"], d["capital"], d.get("simbrief_username", ""),
                         d.get("sim_source", "auto"), d.get("difficulty", "standard"), career=bool(d.get("career")),
                         aoc_types=d.get("aoc_types") or [])
    return ok()


@app.post("/api/company/logo")
def company_logo():
    with lock:
        game.set_logo(request.json.get("data"))
    return ok()


@app.post("/api/company/settings")
def company_settings():
    with lock:
        game.update_settings(request.json)
    return ok()


@app.post("/api/reset")
def reset():
    global tracker
    with lock:
        tracker = None
        game.reset()
    return ok()


# ------------------------------------------------------------------ save slots / backup
@app.get("/api/saves")
def saves_list():
    out = []
    for p in sorted(glob.glob(os.path.join(SAVE_DIR, "*.db"))):
        name = os.path.basename(p)[:-3]
        try:
            g = Game(p)
            co = g.state["company"]["name"] if g.state else "(empty)"
            clock = g.state["clock"] if g.state else ""
        except Exception:
            co, clock = "(unreadable)", ""
        out.append(dict(name=name, company=co, clock=clock, size=os.path.getsize(p), current=name == _current_slot()))
    return ok(saves=out)


@app.post("/api/saves/switch")
def saves_switch():
    global game, tracker
    name = re.sub(r"[^A-Za-z0-9_-]", "", request.json.get("name", ""))[:40]
    if not name:
        raise GameError("Slot name must be letters, digits, - or _.")
    with lock:
        tracker = None
        _set_slot(name)
        game = Game(os.path.join(SAVE_DIR, name + ".db"))
    return ok()


@app.get("/api/saves/backup")
def saves_backup():
    with lock:
        game.save() if game.state else None
        path = game.db_path
    if not os.path.exists(path):
        raise GameError("No save file yet.")
    return send_file(path, as_attachment=True, download_name=f"operator-{_current_slot()}-{datetime.utcnow():%Y%m%d-%H%M}.db")


@app.post("/api/saves/restore")
def saves_restore():
    global game, tracker
    f = request.files.get("file")
    if not f:
        raise GameError("No file uploaded.")
    data = f.read()
    if not data.startswith(b"SQLite format 3"):
        raise GameError("That is not a Operator save file.")
    with lock:
        tracker = None
        with open(game.db_path, "wb") as fh:
            fh.write(data)
        game = Game(game.db_path)
    return ok()


# ------------------------------------------------------------------ fleet / market / crew / staff
@app.post("/api/market/buy")
def market_buy():
    with lock:
        return ok(aircraft=game.buy(int(request.json["id"]), deliver=bool((request.json or {}).get("deliver"))))


@app.post("/api/market/lease")
def market_lease():
    with lock:
        return ok(aircraft=game.lease(int(request.json["id"]), deliver=bool((request.json or {}).get("deliver"))))


@app.get("/api/market/<int:lid>/delivery")
def market_delivery(lid):
    with lock:
        l = game.listing(lid)
        return ok(quote=game.delivery_quote(l["type"], l["location"]), listing=l)


@app.post("/api/fleet/rename")
def fleet_rename():
    d = request.json
    with lock:
        msg = game.rename_aircraft(int(d["id"]), d.get("reg"), d.get("name"), d.get("fleet_no"), d.get("sim_type"))
    return ok(message=msg)


@app.post("/api/fleet/dispose")
def fleet_dispose():
    with lock:
        game.dispose(int(request.json["id"]))
    return ok()


@app.post("/api/fleet/maintenance")
def fleet_mx():
    with lock:
        game.do_maintenance(int(request.json["id"]), request.json.get("check", "A"))
    return ok()


@app.post("/api/fleet/pbh")
def fleet_pbh():
    with lock:
        game.set_pbh(int(request.json["id"]), bool(request.json.get("on")))
    return ok()


@app.post("/api/crew/hire")
def crew_hire():
    with lock:
        game.hire(int(request.json["id"]))
    return ok()


@app.post("/api/crew/release")
def crew_release():
    with lock:
        game.release_pilot(int(request.json["id"]))
    return ok()


@app.post("/api/crew/rename")
def crew_rename():
    d = request.json or {}
    with lock:
        p = game.rename_pilot(int(d["id"]), name=d.get("name"), is_self=d.get("is_self"))
    return ok(pilot=p)


@app.post("/api/crew/train")
def crew_train():
    with lock:
        game.train(int(request.json["id"]), request.json["family"])
    return ok()


@app.get("/api/ferry/<int:jid>/document/<int:index>")
def ferry_document(jid, index):
    with lock:
        return ok(document=game.document(jid, index))


@app.post("/api/crew/rating/remove")
def crew_rating_remove():
    with lock:
        game.remove_rating(int(request.json["id"]), request.json["family"])
    return ok()


@app.post("/api/crew/recency")
def crew_recency():
    with lock:
        game.recency_training(int(request.json["id"]), request.json["family"])
    return ok()


@app.post("/api/crew/promote")
def crew_promote():
    with lock:
        game.promote(int(request.json["id"]))
    return ok()


@app.get("/api/credits")
def credits():
    path = os.path.join(HERE, "static", "operators", "sources.json")
    if not os.path.exists(path):
        return ok(credits=[])
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return ok(credits=[dict(operator=c.get("operator"), file=c.get("file"), license=c.get("license"), license_url=c.get("license_url"),
                            artist=c.get("artist"), source=c.get("source_page"), source_page=c.get("source_page"),
                            kind=c.get("kind"), note=c.get("note"), category=c.get("category")) for c in data])


@app.post("/api/staff")
def staff_change():
    with lock:
        game.staff_change(request.json["role"], int(request.json["delta"]))
    return ok()


# ------------------------------------------------------------------ contracts
@app.get("/api/charter/<int:qid>/fit")
def charter_fit(qid):
    with lock:
        q = next((x for x in game.state["charter_board"] if x["id"] == qid), None)
        if not q:
            raise GameError("Enquiry not found.")
        out = []
        group = bool(q.get("group"))
        for a in game.state["fleet"]:
            ac = AIRCRAFT[a["type"]]
            # a group charter is flown on an airliner, a private charter on a business aircraft
            if group and (ac.get("charter") or ac["seats"] < 45):
                continue
            if not group and not ac.get("charter"):
                continue
            f = game.charter_fit(q, a)
            out.append(dict(reg=a["reg"], type=a["type"], name=a["name"], location=a["location"],
                            status=a["status"], **f))
    return ok(fleet=out)


@app.post("/api/charter/quote")
def charter_quote():
    with lock:
        r = game.quote_charter(int(request.json["id"]), request.json["price"])
    return ok(**r)


@app.post("/api/ferry/accept")
def ferry_accept():
    d = request.json
    with lock:
        return ok(job=game.accept_ferry(int(d["id"]), int(d["captain_id"]), int(d["fo_id"])))


@app.post("/api/ferry/expedite")
def ferry_expedite():
    with lock:
        game.expedite_docs(int(request.json["id"]))
    return ok()


@app.post("/api/ferry/rectify")
def ferry_rectify():
    with lock:
        game.rectify_snags(int(request.json["id"]))
    return ok()


@app.post("/api/cargo/accept")
def cargo_accept():
    d = request.json
    with lock:
        return ok(job=game.accept_cargo(int(d["id"]), int(d["captain_id"]), int(d["fo_id"])))


@app.post("/api/acmi/accept")
def acmi_accept():
    d = request.json
    with lock:
        return ok(contract=game.accept_tender(int(d["id"]), int(d["aircraft_id"]), [int(x) for x in d["crew_ids"]], bool(d.get("livery", True))))


@app.get("/api/contract/<int:cid>/rotation")
def contract_rotation(cid):
    with lock:
        return ok(legs=game.rotation(cid))


# ------------------------------------------------------------------ flight ops
@app.get("/api/simbrief")
def simbrief():
    c = game.state["company"] if game.state else {}
    sid = request.args.get("static_id") or None
    strict = request.args.get("strict") == "1"
    try:
        ofp = fetch_simbrief(c.get("simbrief_username"), c.get("simbrief_userid"), sid)
        if strict and sid and ofp.get("static_id") and ofp["static_id"] != sid:
            raise GameError("The plan has not been generated yet.")
    except Exception as e:
        if not sid or strict:
            raise
        # nothing filed under that id yet: fall back to the latest OFP but say so
        ofp = fetch_simbrief(c.get("simbrief_username"), c.get("simbrief_userid"))
        ofp["static_mismatch"] = True
    return ok(ofp=ofp)


@app.post("/api/simbrief/prefill")
def simbrief_link():
    """Build a pre-filled SimBrief dispatch link from the (not yet dispatched) flight form."""
    d = request.json
    with lock:
        f = game.prefill_flight(d)
        co = game.state["company"]
        crew = {}
        for i in f.get("crew", []):
            p = next((x for x in game.state["pilots"] if x["id"] == i), None)
            if p and p["rank"] == "CPT" and "cpt" not in crew:
                crew["cpt"] = p["name"]
            elif p and p["rank"] == "FO" and "fo" not in crew:
                crew["fo"] = p["name"]
        sid = f"OPERATOR-{co['code']}-{game.nid('sb')}"
        url = simbrief_prefill(f, co, crew, sid, game.state["clock"],
                               units="kgs" if co.get("weight_units") == "kg" else "lbs")
    return ok(url=url, static_id=sid, remarks=f.get("_rmk", ""))


@app.post("/api/routeplan")
def routeplan():
    """Suggested routing with technical stops between two airports for a type or fleet aircraft."""
    d = request.json
    with lock:
        t = d.get("type")
        if not t and d.get("aircraft_id"):
            t = game.fleet_ac(int(d["aircraft_id"]))["type"]
        org, dst = (d.get("origin") or "").upper(), (d.get("destination") or "").upper()
        if not t or len(org) != 4 or len(dst) != 4:
            return ok(legs=[], range_nm=None)
        legs = game.route_legs(t, org, dst)
    return ok(legs=legs, range_nm=AIRCRAFT[t]["range_nm"], type=t)


@app.get("/api/loadsheet")
def loadsheet():
    with lock:
        return ok(loadsheet=game.loadsheet())


@app.post("/api/performance")
def performance():
    """Runway analysis and loadsheet for the current dispatch form, without dispatching."""
    d = request.json
    with lock:
        f = game.prefill_flight(d)
        f.update(block_fuel=int(float(d.get("block_fuel_lbs") or 0)), pax=int(float(d.get("pax") or 0)), cargo_lbs=int(float(d.get("cargo_lbs") or 0)),
                 planned_ete=int(float(d.get("ete_min") or 0)) or int(float(d.get("distance_nm") or 0) / max(1, AIRCRAFT[f["type"]]["cruise"]) * 60 + 25))
        an = game.analyse(f, d)
    return ok(analysis=an, runways=dict(origin=perf_runways(f["origin"]), destination=perf_runways(f["destination"])))


def perf_runways(icao):
    import perf as _p
    return [dict(length=r["l"], width=r["w"], surface="Hard" if r["s"] == "H" else "Unpaved", lit=r["lit"], ends=[e["id"] for e in r["e"]]) for r in _p.runways(icao)[:6]]


@app.post("/api/dispatch")
def dispatch():
    with lock:
        return ok(flight=game.dispatch(request.json))


@app.post("/api/flight/start")
def flight_start():
    global tracker
    with lock:
        f = game.state and game.state.get("active_flight")
        if not f:
            raise GameError("No dispatched flight.")
        if not bridge.connected:
            raise GameError("Simulator is not connected. Connect from the status bar or Settings first.")
        game.sync_sim_clock(bridge.get())
        vref = ((f.get("perf") or {}).get("landing") or {}).get("vref")
        tracker = FlightTracker(f, vmo=AIRCRAFT[f["type"]]["vmo"], restrictions=f.get("restrictions") or {}, vref=vref)
        game.set_flight_status("Tracking")
    return ok()


@app.post("/api/flight/cancel")
def flight_cancel():
    global tracker
    with lock:
        tracker = None
        game.cancel_flight(request.json.get("id") if request.json else None)
    return ok()


@app.get("/api/tracker")
def tracker_get():
    with lock:
        _restore_tracker()
        t = tracker.summary() if tracker else None
    return ok(tracker=t, sim=dict(connected=bridge.connected, source=bridge.source, status=bridge.status, sample=bridge.get()))


def _discord(url, rec):
    try:
        co = game.state["company"]
        land = f"{rec['touchdown_vs']} fpm ({rec['landing_desc']})" if rec.get("touchdown_vs") is not None else "n/a"
        body = json.dumps({"content": f"**{co['name']}** PIREP {rec['flight_number']}: {rec['origin']}→{rec['arrival']} · {rec['type']} {rec['reg']} · "
                                      f"block {int(rec['block_min'] // 60)}:{int(rec['block_min'] % 60):02d} · landing {land} · score {rec['score']}/100"}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "Operator/1.0"})
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:
        print("discord:", e)


@app.post("/api/flight/fly")
def flight_fly():
    global tracker
    with lock:
        out = game.fly_with_crew((request.json or {}).get("id"))
        tracker = None
        hook = game.state["company"].get("discord_webhook")
    if out.get("filed") and hook:
        threading.Thread(target=_discord, args=(hook, out["pirep"]), daemon=True).start()
    return ok(**out)


@app.get("/api/safety")
def safety_view():
    with lock:
        return ok(safety=game.safety_summary(), risk=game.current_risk())


@app.post("/api/flight/pirep")
def flight_pirep():
    global tracker
    manual = bool(request.json.get("manual"))
    with lock:
        summ = tracker.summary() if tracker else None
        if not manual and summ is None:
            raise GameError("Tracking was never started for this flight. Start tracking, or file a manual PIREP.")
        rec = game.file_pirep(summ, manual=manual)
        tracker = None
        hook = game.state["company"].get("discord_webhook")
    if hook:
        threading.Thread(target=_discord, args=(hook, rec), daemon=True).start()
    return ok(pirep=rec)


@app.get("/api/pirep/<int:fid>")
def pirep_get(fid):
    return ok(pirep=game.get_pirep(fid))


# ------------------------------------------------------------------ reports / exports
@app.post("/api/flight/track")
def flight_track():
    with lock:
        game.track_flight(int(request.json["id"]))
    return ok()


@app.post("/api/contract/rotation/operate")
def contract_rotation_operate():
    with lock:
        r = game.operate_rotation(int(request.json["id"]), sectors=request.json.get("sectors"))
    return ok(**r)


@app.post("/api/contract/cancel")
def contract_cancel():
    with lock:
        r = game.cancel_contract(int(request.json["id"]))
    return ok(**r)


@app.post("/api/company/area")
def company_area():
    with lock:
        r = game.apply_area(request.json["region"])
    return ok(**r)


@app.post("/api/company/type")
def company_type():
    with lock:
        r = game.apply_type(request.json["family"])
    return ok(**r)


@app.post("/api/dev")
def dev_action():
    with lock:
        msg = game.dev(request.json["action"], request.json.get("value"))
    return ok(message=msg)


@app.get("/api/record/pilot/<int:pid>")
def record_pilot(pid):
    with lock:
        return ok(record=game.pilot_record(pid))


@app.get("/api/record/aircraft/<int:ac_id>")
def record_aircraft(ac_id):
    with lock:
        return ok(record=game.aircraft_record(ac_id))


@app.get("/api/schedule")
def schedule():
    with lock:
        return ok(schedule=game.schedule(int(request.args.get("days", 14))))


@app.get("/api/analytics")
def analytics():
    with lock:
        return ok(**game.analytics())


@app.get("/print/annual/<int:year>")
def print_annual(year):
    with lock:
        s = game.state
        rep = next((r for r in s["years"] if r["year"] == year), None)
        if not rep:
            return Response("<p>No report for that year.</p>", mimetype="text/html")
        co = s["company"]
        rows = "".join(f"<tr><td>{k.title()}</td><td class=n>${v:,}</td></tr>" for k, v in rep["revenue"].items() if v)
        html = f"""<!doctype html><html><head><meta charset=utf-8><title>{co['name']} — {year} annual report</title>
<style>body{{font:13px/1.5 Segoe UI,Arial,sans-serif;margin:36px;max-width:820px}}h1{{font-size:20px;margin:0}}h2{{font-size:14px;margin:22px 0 6px;border-bottom:1px solid #ccc;padding-bottom:3px}}
table{{border-collapse:collapse;width:100%}}td,th{{padding:3px 6px;border-bottom:1px solid #e3e3e3;text-align:left}}.n{{text-align:right}}
.kpi{{display:flex;gap:26px;margin-top:10px}}.kpi div{{flex:1}}.kpi b{{display:block;font-size:19px}}@media print{{button{{display:none}}}}</style></head><body>
<button onclick="window.print()">Print / Save as PDF</button>
<h1>{co['name']}</h1><div>{co['code']} · base {co['base']} · annual report for {year}</div>
<div class=kpi><div><b>${rep['income']:,}</b>Income</div><div><b>${rep['expenses']:,}</b>Costs</div><div><b>${rep['net']:,}</b>Net result</div><div><b>${rep['closing_equity']:,}</b>Closing equity</div></div>
<h2>Operations</h2><table>
<tr><td>Sectors flown</td><td class=n>{rep['sectors']:,}</td></tr><tr><td>Block hours</td><td class=n>{rep['hours']:,.1f}</td></tr>
<tr><td>Distance</td><td class=n>{rep['nm']:,} nm</td></tr><tr><td>Average flight score</td><td class=n>{rep['avg_score']}</td></tr>
<tr><td>Fleet at year end</td><td class=n>{rep['fleet']}</td></tr><tr><td>Pilots at year end</td><td class=n>{rep['pilots']}</td></tr>
<tr><td>Reputation</td><td class=n>{rep['reputation']:.1f}</td></tr></table>
<h2>Revenue by line of business</h2><table>{rows}</table>
<h2>Best and worst month</h2><table><tr><td>{rep['best']['month']}</td><td class=n>${rep['best']['net']:,}</td></tr>
<tr><td>{rep['worst']['month']}</td><td class=n>${rep['worst']['net']:,}</td></tr></table>
<h2>Safety</h2><table><tr><td>Reportable occurrences</td><td class=n>{rep['occurrences']}</td></tr>
<tr><td>Accidents</td><td class=n>{rep['accidents']}</td></tr></table>
<h2>Customers flown for</h2><p>{', '.join(rep['customers']) or '—'}</p>
</body></html>"""
    return Response(html, mimetype="text/html")


@app.get("/api/statements")
def statements():
    with lock:
        return ok(**game.statements())


@app.get("/api/export/logbook.csv")
def export_logbook():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "flight", "kind", "customer", "type", "reg", "origin", "arrival", "block_min", "distance_nm", "fuel_burn_lb", "touchdown_fpm", "score", "revenue", "costs", "crew"])
    with lock:
        pilots = {p["id"]: p["name"] for p in game.state["pilots"]}
        for f in reversed(game.state["flights"]):
            w.writerow([f["filed"], f["flight_number"], f["kind"], f.get("customer", ""), f["type"], f["reg"], f["origin"], f["arrival"], f["block_min"],
                        f["dist_nm"], f["fuel_burn"], f["touchdown_vs"], f["score"], f["income"], f["costs"], "; ".join(pilots.get(i, "") for i in f["crew"])])
    return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=operator-logbook.csv"})


@app.get("/print/logbook")
def print_logbook():
    with lock:
        s = game.state
        rows = "".join(f"<tr><td>{f['filed'][:10]}</td><td>{f['flight_number']}</td><td>{f['kind']}</td><td>{f['type']} {f['reg']}</td><td>{f['origin']}–{f['arrival']}</td>"
                       f"<td class=n>{int(f['block_min'] // 60)}:{int(f['block_min'] % 60):02d}</td><td class=n>{f['dist_nm']}</td><td class=n>{f['touchdown_vs'] if f['touchdown_vs'] is not None else ''}</td><td class=n>{f['score']}</td></tr>"
                       for f in reversed(s["flights"]))
        total = sum(f["block_min"] for f in s["flights"]) / 60
        html = f"""<!doctype html><html><head><meta charset=utf-8><title>Logbook — {s['company']['name']}</title>
<style>body{{font:12px/1.4 Segoe UI,Arial,sans-serif;margin:24px}}h1{{font-size:18px;margin:0}}table{{border-collapse:collapse;width:100%;margin-top:14px}}
th,td{{border-bottom:1px solid #ccc;padding:3px 6px;text-align:left}}th{{background:#eee}}.n{{text-align:right}}@media print{{button{{display:none}}}}</style></head><body>
<button onclick="window.print()">Print / Save as PDF</button><h1>{s['company']['name']} — Company logbook</h1><div>{s['company']['code']} · base {s['company']['base']} · {len(s['flights'])} sectors · {total:.1f} block hours · printed {s['clock'][:10]}</div>
<table><tr><th>Date</th><th>Flight</th><th>Type</th><th>Aircraft</th><th>Sector</th><th class=n>Block</th><th class=n>nm</th><th class=n>TD fpm</th><th class=n>Score</th></tr>{rows}</table></body></html>"""
    return Response(html, mimetype="text/html")


# ------------------------------------------------------------------ sim / time / finance
@app.post("/api/sim/connect")
def sim_connect():
    c = game.state["company"] if game.state else {}
    d = request.json or {}
    bridge.connect(d.get("source") or c.get("sim_source", "auto"), c.get("xp_host", "127.0.0.1"), c.get("xp_port", 49000))
    time.sleep(1.2)
    return ok(sim=dict(connected=bridge.connected, source=bridge.source, status=bridge.status))


@app.post("/api/sim/disconnect")
def sim_disconnect():
    bridge.disconnect()
    return ok()


@app.post("/api/time/advance")
def time_advance():
    with lock:
        if game.state.get("active_flight") and game.state["active_flight"].get("status") == "Tracking":
            raise GameError("Cannot advance time while a flight is being tracked.")
        game.advance(days=int(request.json.get("days", 1)))
    return ok()


@app.post("/api/finance/loan")
def finance_loan():
    with lock:
        game.take_loan(request.json["amount"])
    return ok()


@app.post("/api/finance/repay")
def finance_repay():
    with lock:
        game.repay_loan(int(request.json["id"]))
    return ok()


def _log_path():
    return os.path.join(_home(), "operator-log.txt")


def _log(msg):
    line = f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    try:
        with open(_log_path(), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def _port_free(port):
    import socket as _s
    with _s.socket(_s.AF_INET, _s.SOCK_STREAM) as sock:
        sock.setsockopt(_s.SOL_SOCKET, _s.SO_REUSEADDR, 1)
        try:
            sock.bind((HOST, port))
            return True
        except OSError:
            return False


def _lan_address():
    """The address of this machine on the local network, for the banner."""
    import socket as _s
    try:
        with _s.socket(_s.AF_INET, _s.SOCK_DGRAM) as sock:
            sock.connect(("10.255.255.255", 1))      # no packet is sent
            return sock.getsockname()[0]
    except Exception:
        try:
            return _s.gethostbyname(_s.gethostname())
        except Exception:
            return None


def _already_running(port):
    """Another copy of Operator answering on this port?"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _serve_forever():
    from werkzeug.serving import make_server
    srv = make_server(HOST, PORT, app, threaded=True)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def _claim_mutex():
    """Named mutex so the Windows installer can tell whether Operator is running."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        return ctypes.windll.kernel32.CreateMutexW(None, False, "OperatorRunningMutex")
    except Exception:
        return None


def _switch_value(args, name):
    """--host 0.0.0.0 or --host=0.0.0.0; returns None when the switch is absent,
    and an empty string when it is present with nothing after it."""
    for i, a in enumerate(args):
        if a == name:
            return args[i + 1] if i + 1 < len(args) and not args[i + 1].startswith("-") else ""
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return None


def main():
    global PORT, HOST
    _claim_mutex()
    frozen = getattr(sys, "frozen", False)
    args = [a.lower() for a in sys.argv[1:]]

    # --- where to listen. Default is loopback only: nothing outside this PC can reach it.
    host = _switch_value(args, "--host")
    if "--lan" in args and host is None:
        host = "0.0.0.0"
    if host is not None:
        HOST = host.strip() or "0.0.0.0"
    port = _switch_value(args, "--port")
    if port:
        try:
            PORT = int(port)
        except ValueError:
            raise RuntimeError(f"--port wants a number, not {port!r}.")
    served_wide = HOST not in ("127.0.0.1", "localhost", "::1")

    mode = "window"
    if "--browser" in args or "--no-browser" in args:
        mode = "browser"
    elif "--app" in args:
        mode = "app"
    elif "--console" in args:
        mode = "browser"
    elif served_wide and "--window" not in args:
        # a machine serving the network is usually headless: no window, no browser
        mode = "browser"
        if "--no-browser" not in args:
            args.append("--no-browser")
            sys.argv.append("--no-browser")
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        _log(f"Operator starting (frozen={frozen}, python {sys.version.split()[0]})")
        _log(f"resources: {HERE}")
        _log(f"saves:     {SAVE_DIR}")

        if not served_wide and _already_running(PORT):
            url = f"http://127.0.0.1:{PORT}"
            _log(f"Operator is already running; opening {url}")
            webbrowser.open(url)
            return

        if not _port_free(PORT):
            for alt in range(PORT + 1, PORT + 12):
                if _port_free(alt):
                    _log(f"Port {PORT} is in use; using {alt} instead.")
                    PORT = alt
                    break
            else:
                raise RuntimeError(f"Ports {PORT}-{PORT + 11} are all in use. Close the other program and try again.")

        url = f"http://127.0.0.1:{PORT}"
        print()
        print("  ==========================================================")
        print("   Operator - Ferry, Cargo & ACMI")
        print(f"   Running at {url}")
        if served_wide:
            lan = _lan_address()
            if lan:
                print(f"   On this network: http://{lan}:{PORT}")
            print(f"   Listening on {HOST}:{PORT} - anyone who can reach this")
            print("   machine can open your company. There is no password.")
        print("   Your saves are in:")
        print(f"   {SAVE_DIR}")
        print("  ==========================================================")
        print()

        if mode == "browser":
            print("  Leave this window open while you play; closing it stops the program.")
            print()
            if "--no-browser" not in sys.argv:
                threading.Timer(1.2, lambda: webbrowser.open(url)).start()
            app.run(host=HOST, port=PORT, debug=False, threaded=True)
            return

        # desktop window: serve in the background, then own the main thread with the window
        with lock:
            _restore_tracker()
        srv = _serve_forever()
        _log(f"serving in the background on {PORT}; opening the desktop window")
        try:
            import desktop
            desktop.run(PORT, prefer="auto" if mode == "window" else mode)
        finally:
            _log("window closed; shutting down")
            try:
                srv.shutdown()
            except Exception:
                pass
    except Exception as e:
        import traceback
        _log("STARTUP FAILED: " + repr(e))
        try:
            with open(_log_path(), "a", encoding="utf-8") as fh:
                traceback.print_exc(file=fh)
        except Exception:
            pass
        traceback.print_exc()
        print()
        print("  Operator could not start. The details above were also written to:")
        print(f"  {_log_path()}")
        if frozen:
            try:
                input("\n  Press Enter to close this window. ")
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
