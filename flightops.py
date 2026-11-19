"""SimBrief integration and live flight tracking."""
import json
import math
import time
import urllib.parse
import urllib.request

SIMBRIEF_URL = "https://www.simbrief.com/api/xml.fetcher.php?json=1&"


def _wx(d):
    w = d.get("weather", {}) or {}
    return dict(orig_metar=w.get("orig_metar", ""), dest_metar=w.get("dest_metar", ""), altn_metar=w.get("altn_metar", ""),
                orig_taf=w.get("orig_taf", ""), dest_taf=w.get("dest_taf", ""))


def wx_flags(metar):
    """Very small METAR screen: returns list of adverse conditions."""
    m = (metar or "").upper()
    out = []
    import re as _re
    if _re.search(r"\bTS", m):
        out.append("thunderstorms")
    if _re.search(r"\b(FZ|SN|SHSN|PL)", m):
        out.append("freezing/snow")
    vis = _re.search(r"\s(\d{4})\s", m)
    if vis and int(vis.group(1)) < 1500:
        out.append(f"visibility {vis.group(1)} m")
    if _re.search(r"\s[0-9]/?[0-9]?SM\s", m) and _re.search(r"\s(1/4|1/2|3/4|1)SM\s", m):
        out.append("low visibility")
    c = _re.search(r"(BKN|OVC|VV)(\d{3})", m)
    if c and int(c.group(2)) <= 3:
        out.append(f"ceiling {int(c.group(2)) * 100} ft")
    w = _re.search(r"\d{3}(\d{2,3})G(\d{2,3})KT", m)
    if w and int(w.group(2)) >= 35:
        out.append(f"gusts {w.group(2)} kt")
    return out


SIMBRIEF_DISPATCH = "https://dispatch.simbrief.com/options/custom?"
# SimBrief airframe codes differ from ICAO for a few freighters/variants
SB_TYPE = {"B76F": "B763", "B77F": "B77L", "B744": "B744", "B748": "B748"}


def simbrief_prefill(f, company, crew, static_id, clock, units="lbs"):
    """crew: dict with optional 'cpt' and 'fo' names."""
    """Build the SimBrief dispatch URL pre-filled from a Operator flight dict."""
    r = f.get("restrictions") or {}
    rmk = []
    if f["kind"] == "ferry":
        rmk.append("FERRY FLIGHT NO PAX")
        if f.get("permit"):
            rmk.append(f["permit"].upper())
    for sn in f.get("snags") or []:
        rmk.append(f"{sn['code']} INOP - {sn['effect'].upper()}")
    if (r.get("no_oceanic") or not f.get("etops", True)) and not any(sn["code"] in ("ETOPS", "HF") for sn in f.get("snags") or []):
        rmk.append("NON ETOPS - REMAIN WITHIN 60 MIN OF ADEQUATE AIRPORT")
    if f.get("customer"):
        rmk.append(f"OPERATED FOR {f['customer'].upper()}")
    params = {
        "airline": company["code"], "fltnum": (f.get("flight_number") or "")[len(company["code"]):] if (f.get("flight_number") or "").startswith(company["code"]) else f.get("flight_number", ""),
        "type": SB_TYPE.get(f["type"], f["type"]), "reg": f.get("reg", ""), "orig": f["origin"], "dest": f["destination"],
        "date": clock[8:10] + ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"][int(clock[5:7]) - 1] + clock[2:4],
        "deph": (f.get("std") or clock[11:16])[:2], "depm": (f.get("std") or clock[11:16])[3:5],
        "units": units.upper(), "planformat": "lido", "static_id": static_id, "manualrmk": " / ".join(rmk)[:250],
        "callsign": (company.get("callsign") or company["code"]) + (f.get("flight_number") or "")[len(company["code"]):],
    }
    if f.get("alternate"):
        params["altn"] = f["alternate"]
    if f.get("route"):
        params["route"] = f["route"]
    if f["kind"] == "ferry":
        params["pax"] = "0"
        params["cargo"] = "0"
    else:
        if f.get("pax"):
            params["pax"] = str(f["pax"])
        if f.get("cargo_lbs"):
            params["cargo"] = str(round(f["cargo_lbs"] / 1000, 1))
    if r.get("max_alt"):
        params["fl"] = str(int(r["max_alt"]))
    elif f.get("cruise_alt"):
        params["fl"] = str(int(f["cruise_alt"]))
    if isinstance(crew, (list, tuple)):
        crew = dict(cpt=crew[0] if crew else "", fo=crew[1] if len(crew) > 1 else "")
    if (crew or {}).get("cpt"):
        params["cpt"] = crew["cpt"]
    if (crew or {}).get("fo"):
        params["fo"] = crew["fo"]
    params["dxname"] = company.get("name", "")[:30]
    return SIMBRIEF_DISPATCH + urllib.parse.urlencode({k: v for k, v in params.items() if v not in ("", None)})


def fetch_simbrief(username=None, userid=None, static_id=None):
    """Fetch the latest OFP (or the one tagged static_id) from SimBrief."""
    q = {}
    if userid:
        q["userid"] = userid
    elif username:
        q["username"] = username
    else:
        raise ValueError("SimBrief username or pilot ID not set (Settings).")
    if static_id:
        q["static_id"] = static_id
    q = urllib.parse.urlencode(q)
    req = urllib.request.Request(SIMBRIEF_URL + q, headers={"User-Agent": "Operator/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    if "fetch" in d and d["fetch"].get("status", "").lower().startswith("error"):
        raise ValueError(d["fetch"]["status"])
    g = d.get("general", {})
    f = d.get("fuel", {})
    w = d.get("weights", {})
    a = d.get("aircraft", {})
    units = (d.get("params", {}) or {}).get("units", "lbs")
    to_lbs = 1.0 if str(units).lower().startswith("lb") else 2.20462

    def num(x, k=1.0):
        try:
            return float(x) * k
        except Exception:
            return 0.0

    alt = d.get("alternate", {})
    if isinstance(alt, list):
        alt = alt[0] if alt else {}
    return dict(
        origin=d.get("origin", {}).get("icao_code", ""),
        destination=d.get("destination", {}).get("icao_code", ""),
        alternate=alt.get("icao_code", "") if isinstance(alt, dict) else "",
        route=g.get("route", ""),
        cruise_alt=int(num(g.get("initial_altitude"))),
        distance_nm=int(num(g.get("air_distance") or g.get("route_distance"))),
        ete_min=int(num(g.get("est_time_enroute")) / 60),
        flight_number=(g.get("icao_airline", "") + g.get("flight_number", "")).strip(),
        aircraft_icao=a.get("icaocode", "") or a.get("icao_code", ""),
        reg=a.get("reg", ""),
        block_fuel_lbs=int(num(f.get("plan_ramp"), to_lbs)),
        trip_fuel_lbs=int(num(f.get("enroute_burn"), to_lbs)),
        reserve_fuel_lbs=int(num(f.get("reserve"), to_lbs)),
        zfw_lbs=int(num(w.get("est_zfw"), to_lbs)),
        tow_lbs=int(num(w.get("est_tow"), to_lbs)),
        pax=int(num(w.get("pax_count"))),
        cargo_lbs=int(num(w.get("cargo"), to_lbs)),
        cost_index=g.get("costindex", ""),
        ofp_id=d.get("params", {}).get("request_id", ""),
        generated=d.get("params", {}).get("time_generated", ""),
        weather=_wx(d),
        static_id=d.get("params", {}).get("static_id", ""),
        etops=str(d.get("etops", {}).get("rule", "")) if isinstance(d.get("etops"), dict) else "",
    )


def gc_nm_pts(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(math.radians, (lat1, lon1, lat2, lon2))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3440.065 * 2 * math.asin(math.sqrt(max(0.0, min(1.0, h))))


def simulate_sector(flight, ac, ctx, rng):
    """Fly the sector with the company crew: produce a summary in the tracker's shape.

    Quality follows crew experience, fatigue, weather and the aircraft's condition, with
    honest variance — a tired crew on a wet night will not grease it on.
    """
    ete = max(20, flight.get("planned_ete") or 60)
    dist = flight.get("planned_dist") or int(ete / 60 * ac["cruise"])
    skill = min(1.0, ctx.get("crew_hours_min", 6000) / 9000)
    fatigue = max(0.0, ctx.get("duty_h", 0) - 8) / 6
    wx = len(ctx.get("wx") or []) * 0.35 + (0.3 if ctx.get("surface_state") in ("wet", "contaminated") else 0)
    night = 0.15 if ctx.get("night") else 0.0
    quality = max(0.0, min(1.0, 0.45 + skill * 0.55 - fatigue * 0.5 - wx * 0.35 - night))
    block = ete + rng.randint(-4, 14) + int(fatigue * 6)
    burn = int(block / 60 * ac["burn"] * rng.uniform(0.93, 1.09))
    start = flight.get("block_fuel") or int(burn * 1.3)
    # touchdown rate: better crews land smoother, with a tail of firmer arrivals
    mean = -110 - (1 - quality) * 260
    vs = int(rng.gauss(mean, 70 + (1 - quality) * 140))
    vs = max(-1400, min(-25, vs))
    bounces = 1 if (vs < -520 and rng.random() < 0.25) else 0
    g = round(1.15 + abs(vs) / 1400 + rng.uniform(0, 0.12), 2)
    handling = 1.0 + max(0.0, (1 - quality) * 1.4) + (0.6 if vs < -700 else 0.0)
    cruise = int(round((flight.get("cruise_alt") or (35000 if ac["cat"] != "Turboprop" else 20000)) / 100) * 100)
    return dict(complete=True, phase="Arrived", block_min=block, air_min=max(1, block - 20), dist_nm=dist,
                fuel_start=start, fuel_end=max(0, start - burn), fuel_burn=burn, max_alt=cruise,
                max_ias=int(ac["vmo"] * rng.uniform(0.86, 0.97)), max_g=g, min_g=round(1 - rng.uniform(0, 0.15), 2),
                touchdown_vs=vs, touchdown_g=g, overspeed_s=0, taxi_overspeed_s=0, pause_s=0, cruise_alt=cruise,
                samples=block * 60, events=[], path=[], last=None, bounces=bounces,
                flare_vs=int(vs * rng.uniform(1.6, 3.2)), flare_ias=int(120 + rng.uniform(0, 30)),
                td_ias=int(130 + rng.uniform(-8, 14)), td_pitch=round(rng.uniform(2.5, 6.5), 1),
                td_bank=round(rng.gauss(0, 1.2 + (1 - quality) * 2.2), 1), td_xwind=ctx.get("xwind", 0), td_hdwind=ctx.get("hdwind", 0),
                violations=dict(max_alt=0, max_ias=0, gear_up=0), max_remote_nm=ctx.get("remote_nm", 0),
                td_lat=None, td_lon=None, td_hdg=None, simulated=True, quality=round(quality, 2), handling=round(handling, 2))


PHASES = ["Preflight", "Taxi out", "Takeoff", "Climb", "Cruise", "Descent", "Approach", "Landed", "Taxi in", "Arrived"]


class FlightTracker:
    """Consumes 1 Hz samples from the bridge and reconstructs the flight."""

    # A stabilised approach: the gates every operator's flight data monitoring watches.
    GATE_ALTS = (1000, 500)

    def __init__(self, flight, vmo=350, restrictions=None, vref=None):
        self.flight = flight
        self.vmo = vmo
        self.restr = restrictions or {}   # max_alt, max_ias, gear_down, no_oceanic
        self.vref = vref
        self.gates = {}                   # 1000 ft and 500 ft snapshots on final
        self.viol = dict(max_alt=0, max_ias=0, gear_up=0)
        self.bounces = 0
        self.flare_vs = None            # V/S at 50 ft
        self.flare_ias = None
        self.td_ias = self.td_pitch = self.td_bank = self.td_xwind = self.td_hdwind = None
        self.td_lat = self.td_lon = self.td_hdg = None
        self.max_remote = 0.0
        self.sim_clock = None
        self._last_agl = None
        self.agl_glitches = 0
        self.pos_glitches = 0
        self._approach_s = 0
        self.resumed = False
        self._airborne_after_td = 0
        self.phase = "Preflight"
        self.started = time.time()
        self.samples = 0
        self.path = []              # decimated lat/lon track for the UI
        self.events = []
        self.block_off = None
        self.takeoff = None
        self.landing = None
        self.block_on = None
        self.fuel_start = None
        self.fuel_end = None
        self.fuel_takeoff = None
        self.dist_nm = 0.0
        self.max_alt = 0
        self.max_ias = 0
        self.max_g = 1.0
        self.min_g = 1.0
        self.touchdown_vs = None
        self.touchdown_g = None
        self.overspeed_s = 0
        self.taxi_overspeed_s = 0
        self.pause_s = 0
        self.airborne_s = 0
        self.last = None
        self._prev = []
        self._level_s = 0
        self._desc_s = 0
        self.cruise_alt = 0
        self.last_pos = None

    def _log(self, text):
        self.events.append(dict(t=round(time.time() - self.started), phase=self.phase, text=text))

    def update(self, s):
        if s is None:
            return
        self.samples += 1
        if s.get("paused"):
            self.pause_s += 1
            return
        # AGL occasionally comes back wrong from the simulator (terrain not streamed,
        # over water, a scenery reload). Sanity-check it against the altitude trace
        # rather than letting one bad sample drive a phase change.
        agl = s.get("agl_ft")
        alt = s.get("alt_ft") or 0
        bad = agl is None or agl < -200 or agl > alt + 2000
        if not bad and self._last_agl is not None and abs(agl - self._last_agl) > 6000 and not s["on_ground"]:
            bad = True                      # a jump no aircraft could make in a second
        if bad:
            self.agl_glitches += 1
            s["agl_ft"] = self._last_agl if self._last_agl is not None else max(0.0, alt)
        else:
            self._last_agl = agl

        # Position can come back as null island (0, 0) or an implausible jump when the
        # simulator is loading or the link stutters. Neither belongs on the track.
        lat, lon = s.get("lat"), s.get("lon")
        pos_ok = (lat is not None and lon is not None
                  and abs(lat) <= 90 and abs(lon) <= 180
                  and not (abs(lat) < 0.02 and abs(lon) < 0.02))     # (0,0) in the Gulf of Guinea
        if pos_ok and self.last_pos:
            d = gc_nm_pts(self.last_pos[0], self.last_pos[1], lat, lon)
            if d > 60:                # no aircraft covers 60 nm between two samples
                pos_ok = False
            elif d < 5:               # ignore slew and small teleports in the distance total
                self.dist_nm += d
        if not pos_ok:
            self.pos_glitches += 1
            s["lat"], s["lon"] = (self.last_pos or (None, None))
        else:
            self.last_pos = (lat, lon)
            if self.samples % 5 == 0:
                self.path.append([round(lat, 4), round(lon, 4)])
        if pos_ok and self.samples % 20 == 0 and s.get("lat"):
            from data import nearest as _near
            self.max_remote = max(self.max_remote, _near(s["lat"], s["lon"])[1])
        self.max_alt = max(self.max_alt, s["alt_ft"])
        self.max_ias = max(self.max_ias, s["ias"])
        self.max_g = max(self.max_g, s["g"])
        self.min_g = min(self.min_g, s["g"])
        if self.fuel_start is None and s["fuel_lbs"] > 0:
            self.fuel_start = s["fuel_lbs"]
        self.fuel_end = s["fuel_lbs"] or self.fuel_end

        og = s["on_ground"]
        ph = self.phase
        if ph == "Preflight":
            if og and (s["gs"] > 2 and s["eng_on"]):
                self.phase = "Taxi out"
                self.block_off = time.time()
                self.fuel_start = s["fuel_lbs"]
                self._log("Block off — pushback/taxi commenced")
        elif ph == "Taxi out":
            if og and s["gs"] > 30:
                self.taxi_overspeed_s += 1
            if og and s["gs"] > 60:
                self.phase = "Takeoff"
                self._log("Takeoff roll")
            if not og and s["agl_ft"] > 50:
                self.phase = "Climb"
                self.takeoff = time.time()
                self.fuel_takeoff = s["fuel_lbs"]
                self._log("Airborne")
        elif ph == "Takeoff":
            if not og and s["agl_ft"] > 50:
                self.phase = "Climb"
                self.takeoff = time.time()
                self.fuel_takeoff = s["fuel_lbs"]
                self._log("Airborne")
            elif og and s["gs"] < 20:
                self.phase = "Taxi out"
                self._log("Rejected takeoff")
        elif ph in ("Climb", "Cruise", "Descent", "Approach"):
            self.airborne_s += 1
            if s["ias"] > self.vmo:
                self.overspeed_s += 1
                if self.overspeed_s == 1:
                    self._log(f"Overspeed — {int(s['ias'])} kias above VMO {self.vmo}")
            if self.restr.get("max_alt") and s["alt_ft"] > self.restr["max_alt"] + 300:
                self.viol["max_alt"] += 1
                if self.viol["max_alt"] == 1:
                    self._log(f"Above ferry-permit altitude limit {self.restr['max_alt']} ft")
            if self.restr.get("max_ias") and s["ias"] > self.restr["max_ias"] + 5:
                self.viol["max_ias"] += 1
                if self.viol["max_ias"] == 1:
                    self._log(f"Above ferry-permit speed limit {self.restr['max_ias']} kias")
            if self.restr.get("gear_down") and s["gear"] < 0.5:
                self.viol["gear_up"] += 1
                if self.viol["gear_up"] == 1:
                    self._log("Gear retracted on a gear-down ferry")
            if self.flare_vs is None and s["agl_ft"] < 60 and self.airborne_s > 60:
                self.flare_vs, self.flare_ias = int(s["vs"]), int(s["ias"])
            # stability gates: caught on the way down, once, below 2,000 ft
            for gate in self.GATE_ALTS:
                if gate not in self.gates and self.airborne_s > 120 and s["vs"] < -100 \
                        and gate - 120 < s["agl_ft"] <= gate + 60:
                    self.gates[gate] = dict(agl=int(s["agl_ft"]), ias=int(s["ias"]), vs=int(s["vs"]),
                                            gear=round(s["gear"], 2), bank=round(abs(s.get("bank") or 0), 1),
                                            pitch=round(s.get("pitch") or 0, 1))
            # tolerant counters: one bumpy sample should not undo a minute of evidence
            self._level_s = min(90, self._level_s + 1) if abs(s["vs"]) < 500 else max(0, self._level_s - 4)
            self._desc_s = min(90, self._desc_s + 1) if s["vs"] < -500 else max(0, self._desc_s - 4)
            if ph == "Climb" and self._level_s >= 45 and s["alt_ft"] > 8000 and s["alt_ft"] > self.max_alt - 700:
                self.phase = "Cruise"
                self.cruise_alt = int(round(s["alt_ft"] / 100) * 100)
                self._log(f"Top of climb — cruise {self.cruise_alt} ft")
            if ph in ("Climb", "Cruise") and self._desc_s >= 45 and s["alt_ft"] < self.max_alt - 1500:
                self.phase = "Descent"
                self._log("Top of descent")
            # Approach: low, descending and staying that way. A gear-down ferry has the
            # gear out for the whole sector, so the gear alone proves nothing.
            near_field = (s["agl_ft"] < 3500 and s["vs"] < -200
                          and s["alt_ft"] < max(self.max_alt - 3000, 14000)
                          and self.airborne_s > 120)
            self._approach_s = self._approach_s + 1 if near_field else 0
            if ph in ("Descent", "Cruise") and self._approach_s >= 15:
                self.phase = "Approach"
                self._log("On approach" + (" — gear down" if s["gear"] > 0.5 else ""))
            if og and self.airborne_s > 30:
                # touchdown: take the most negative VS from the last airborne samples
                prev_vs = [p["vs"] for p in self._prev[-1:]] or [s["vs"]]
                self.touchdown_vs = int(min(prev_vs + [s["vs"]]))
                self.touchdown_g = round(max([p["g"] for p in self._prev[-2:]] + [s["g"]]), 2)
                self.landing = time.time()
                self.phase = "Landed"
                p = self._prev[-1] if self._prev else s
                self.td_ias, self.td_pitch, self.td_bank = int(p["ias"]), round(p.get("pitch", 0), 1), round(p.get("bank", 0), 1)
                self.td_lat, self.td_lon, self.td_hdg = s["lat"], s["lon"], s["hdg"]
                if p.get("wind_kt") is not None:
                    rel = math.radians((p.get("wind_dir", 0) - p["hdg"] + 540) % 360 - 180)
                    self.td_xwind = round(p["wind_kt"] * math.sin(rel), 1)
                    self.td_hdwind = round(p["wind_kt"] * math.cos(rel), 1)
                self._log(f"Touchdown — {self.touchdown_vs} fpm, {self.touchdown_g} G, {self.td_ias} kias, pitch {self.td_pitch}°")
        elif ph == "Landed":
            if not og and s["gs"] > 60:
                self._airborne_after_td += 1
                if self._airborne_after_td == 1:
                    self.bounces += 1
                    self._log("Bounce")
                if self._airborne_after_td > 8:   # go-around
                    self.phase, self.airborne_s = "Climb", 0
                    self._log("Go-around")
            else:
                self._airborne_after_td = 0
            if og and s["gs"] < 40:
                self.phase = "Taxi in"
                self._log("Runway vacated")
        elif ph == "Taxi in":
            if og and s["gs"] > 30:
                self.taxi_overspeed_s += 1
            if s["gs"] < 1 and (s["park_brake"] or not s["eng_on"]):
                self.phase = "Arrived"
                self.block_on = time.time()
                self.fuel_end = s["fuel_lbs"]
                self._log("Block on — parking brake set / engines shut down")
            if not og and s["agl_ft"] > 50:   # touch and go / go around
                self.phase = "Climb"
                self.airborne_s = 0
                self._log("Airborne again")
        self._prev.append(s)
        if len(self._prev) > 8:
            self._prev.pop(0)
        self.last = s

    def stability(self):
        """Judge each gate against the usual criteria. Returns a list of findings."""
        out = []
        for gate in self.GATE_ALTS:
            g = self.gates.get(gate)
            if not g:
                continue
            bad = []
            if g["vs"] < -1000:
                bad.append(f"{g['vs']} fpm")
            if self.vref:
                if g["ias"] > self.vref + 20:
                    bad.append(f"{g['ias'] - self.vref:+d} kt over Vref")
                elif g["ias"] < self.vref - 5:
                    bad.append(f"{g['ias'] - self.vref:+d} kt below Vref")
            if g["gear"] < 0.9:
                bad.append("gear not down")
            if g["bank"] > 15:
                bad.append(f"{g['bank']}° of bank")
            out.append(dict(gate=gate, stable=not bad, issues=bad, **g))
        return out

    # ------------------------------------------------------------ persistence
    STATE_FIELDS = ("gates", "phase", "started", "samples", "path", "events", "block_off", "takeoff", "landing", "block_on",
                    "fuel_start", "fuel_end", "fuel_takeoff", "dist_nm", "max_alt", "max_ias", "max_g", "min_g",
                    "touchdown_vs", "touchdown_g", "overspeed_s", "taxi_overspeed_s", "pause_s", "airborne_s",
                    "last_pos", "cruise_alt", "bounces", "flare_vs", "flare_ias", "td_ias", "td_pitch", "td_bank",
                    "td_xwind", "td_hdwind", "td_lat", "td_lon", "td_hdg", "max_remote", "viol", "agl_glitches", "pos_glitches",
                    "_level_s", "_desc_s", "_approach_s", "_last_agl", "_airborne_after_td")

    def serialize(self):
        """A compact snapshot so a flight in progress survives the program closing."""
        return {k: getattr(self, k) for k in self.STATE_FIELDS}

    @classmethod
    def restore(cls, data, flight, vmo=350, restrictions=None, vref=None):
        t = cls(flight, vmo=vmo, restrictions=restrictions, vref=vref)
        for k, v in (data or {}).items():
            if k in cls.STATE_FIELDS:
                setattr(t, k, v)
        t.gates = {int(k): v for k, v in (t.gates or {}).items()}
        t.path = [p for p in (t.path or [])
                  if p and len(p) == 2 and abs(p[0]) <= 90 and abs(p[1]) <= 180
                  and not (abs(p[0]) < 0.02 and abs(p[1]) < 0.02)]
        t.last_pos = tuple(t.last_pos) if t.last_pos else None
        t.resumed = True
        return t

    # ------------------------------------------------------------ output
    def summary(self):
        now = time.time()
        block = ((self.block_on or now) - self.block_off) / 60 if self.block_off else 0
        air = ((self.landing or now) - self.takeoff) / 60 if self.takeoff else 0
        burn = (self.fuel_start - self.fuel_end) if (self.fuel_start and self.fuel_end is not None) else 0
        return dict(
            phase=self.phase, elapsed_s=int(now - self.started), samples=self.samples,
            block_min=round(block, 1), air_min=round(air, 1), dist_nm=round(self.dist_nm, 1),
            fuel_start=int(self.fuel_start or 0), fuel_end=int(self.fuel_end or 0), fuel_burn=int(max(0, burn)),
            max_alt=int(self.max_alt), max_ias=int(self.max_ias), max_g=round(self.max_g, 2), min_g=round(self.min_g, 2),
            touchdown_vs=self.touchdown_vs, touchdown_g=self.touchdown_g,
            overspeed_s=self.overspeed_s, taxi_overspeed_s=self.taxi_overspeed_s, pause_s=self.pause_s,
            cruise_alt=self.cruise_alt, block_off=self.block_off, block_on=self.block_on,
            complete=self.phase == "Arrived", events=self.events[-40:], path=self.path[-600:],
            last=self.last, bounces=self.bounces, agl_glitches=self.agl_glitches, pos_glitches=self.pos_glitches, flare_vs=self.flare_vs, flare_ias=self.flare_ias, td_ias=self.td_ias,
            td_pitch=self.td_pitch, td_bank=self.td_bank, td_xwind=self.td_xwind, td_hdwind=self.td_hdwind,
            td_lat=self.td_lat, td_lon=self.td_lon, td_hdg=self.td_hdg, gates=self.gates, vref=self.vref,
            stability=self.stability(),
            violations=self.viol, max_remote_nm=int(self.max_remote), resumed=self.resumed,
        )
