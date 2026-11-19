"""Operator business model v2. Money in USD, fuel in lbs, game clock in UTC."""
import glob
import json
import math
import os
import random
import re
import sqlite3
import string
from datetime import datetime, timedelta

import perf

VERSION = "1.8.0"
import safety
from data import (AIRCRAFT, AIRPORTS, elevation, LESSORS, MROS, STORAGE, DELIVERY_CENTERS, ACMI_CUSTOMERS, OPERATORS, OPERATOR_BASES,
                  REG_PREFIXES, FIRST_NAMES, LAST_NAMES, PERMIT_COUNTRIES, COMPETITORS, CARGO_COMPETITORS, CARGO_OPERATORS, CARGO_CARRIERS_WITH_AIRCRAFT, OPERATOR_FLEETS, OPERATOR_TYPES, operators_for, types_for, BROKERS, CHARTER_CLIENTS, CHARTER_HUBS, CHARTER_EXTRAS, CHARTER_TRIPS, GROUP_CLIENTS, GROUP_HOURLY, aerodrome_code, REGIONS, region_of, ADJACENT_REGIONS, AREA_APPLICATION, TYPE_APPLICATION, SAME_MFR_DISCOUNT, REGION_OF_COUNTRY, CHARTER_EVENTS, CHARTER_COMPETITORS, SHORT_FIELDS, BIZ_SERVICE, BIZ_CLIENTS, BIZ_BROKERS, build_year_range, SNAGS, snags_for, ENGINES, ENGINE_OEM, STAFF,
                  CABIN_PER_SET, MAJOR, FERRY_STOPS, register_for, FAMILY_TYPES, FAMILY_COVERS, substitutes, crew_name, CURRENCIES, CURRENCY_BY_COUNTRY, CARGO_CARRIERS, CARGO_LOADS, OPERATOR_LOGOS, LOGO_TONE, gc_nm, fuel_factor, nearest, route_countries, max_remoteness)

perf.set_mtow({k: v["mtow_kg"] for k, v in AIRCRAFT.items()})
FUEL_LBS_PER_USG = 6.7
KG_PER_LB = 0.453592
A_CHECK_FH = 600
C_CHECK_MONTHS = 24
MAX_FDP_H = 13.0
REST_H = 12
ETOPS_NM = 420          # ~60 min single-engine at 420 kt
NO_PERMIT = {"GB", "IE", "FR", "NL", "BE", "DE", "AT", "CH", "IT", "ES", "PT", "DK", "SE", "NO", "FI", "IS", "PL", "CZ", "SK", "HU",
             "HR", "RS", "BG", "RO", "GR", "CY", "MT", "EE", "LV", "LT", "LU", "SI"}


DIFFICULTY = {
    "relaxed": dict(label="Relaxed", permit=0.5, delay=0.5, fuel=0.85, rep=55.0, fee=1.15, terms=14,
                    desc="Shorter permit lead times, fewer technical delays, cheaper fuel, higher fees, customers pay in 14 days. Widebody work from the start."),
    "standard": dict(label="Standard", permit=1.0, delay=1.0, fuel=1.0, rep=45.0, fee=1.0, terms=30,
                     desc="Balanced economics and lead times; customers pay in 30 days."),
    "realistic": dict(label="Realistic", permit=1.5, delay=1.6, fuel=1.15, rep=35.0, fee=0.9, terms=45,
                      desc="Longer permit lead times, more technical delays, dearer fuel, thinner margins, 45-day payment terms and a reputation to build."),
}

RECENCY_DAYS = 90          # three takeoffs and landings on type within this window
RECENCY_NEEDED = 3

ACHIEVEMENTS = [
    ("first_delivery", "First delivery", "Complete a ferry job."),
    ("paperwork", "Clean paperwork", "Complete a ferry job that needed three or more permits."),
    ("atlantic", "Pond crossing", "File a sector with a farthest-diversion distance over 420 nm."),
    ("permit_ferry", "On a permit", "Deliver an aircraft that flew on a special flight permit without breaching its limits."),
    ("greaser", "Greaser", "Touch down at better than -60 fpm on a tracked flight."),
    ("tdz", "In the zone", "Touch down 500–1,500 ft down the runway within 25 ft of the centreline."),
    ("short_field", "Short field", "Operate from a runway with under 1,000 ft of takeoff margin."),
    ("widebody", "Heavy metal", "Fly a widebody sector."),
    ("first_acmi", "Wet lease", "Sign an ACMI contract."),
    ("first_cargo", "Night freight", "Complete a cargo contract-flying pairing."),
    ("cargo_long", "Long haul freight", "Fly a cargo pairing sector over 3,000 nm."),
    ("cargo_dg", "Dangerous goods", "Carry a dangerous-goods or outsized load."),
    ("cargo_regular", "On the roster", "Complete five cargo pairings."),
    ("acmi_month", "Guarantee met", "Fly the full minimum guarantee in one month on an ACMI contract."),
    ("otp", "Right on time", "Close a month on an ACMI contract with 100% on-time performance and at least 20 legs."),
    ("extension", "They came back", "Receive a contract extension offer."),
    ("hours_100", "100 block hours", "Reach 100 company block hours."),
    ("hours_1000", "1,000 block hours", "Reach 1,000 company block hours."),
    ("fleet_3", "Fleet operator", "Operate three aircraft at once."),
    ("profit", "In the black", "Close a month with a positive net result."),
    ("rep_70", "Trusted operator", "Reach reputation 70."),
    ("safe_100", "One hundred clean", "Fly 100 sectors with no incident or accident."),
    ("first_command", "Left seat", "Promote a first officer to captain."),
    ("five_captains", "Command pool", "Have five captains on the roster."),
]


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M")


def parse(s):
    return datetime.strptime(s[:16], "%Y-%m-%dT%H:%M")


def money(x):
    return int(round(x))


def season(month, cargo):
    if cargo:
        return 1.3 if month in (10, 11, 12) else 0.85 if month in (1, 2) else 1.0
    return 1.25 if month in (5, 6, 7, 8, 9) else 0.9 if month in (11, 1, 2) else 1.0


class GameError(Exception):
    pass


class Game:
    def __init__(self, db_path):
        self.db_path = db_path
        self.state = None
        self.rng = random.Random()
        self._load()

    # ================================================================ persistence
    def _conn(self):
        c = sqlite3.connect(self.db_path)
        c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS pireps (id INTEGER PRIMARY KEY, flight_id INTEGER, data TEXT)")
        return c

    def _load(self):
        c = self._conn()
        r = c.execute("SELECT v FROM kv WHERE k='state'").fetchone()
        c.close()
        self.state = json.loads(r[0]) if r else None
        if self.state:
            self._migrate()

    def _backup_before_migrate(self):
        """Keep a dated copy of the save the first time a new build opens it."""
        try:
            import shutil
            stamp = self.s.get("build")
            if stamp == VERSION:
                return
            if os.path.exists(self.db_path):
                folder = os.path.join(os.path.dirname(self.db_path), "backups")
                os.makedirs(folder, exist_ok=True)
                name = os.path.basename(self.db_path).replace(".db", "")
                dest = os.path.join(folder, f"{name}-{stamp or 'pre-1.0'}-{datetime.now():%Y%m%d-%H%M%S}.db")
                shutil.copy2(self.db_path, dest)
                kept = sorted(glob.glob(os.path.join(folder, f"{name}-*.db")))
                for old in kept[:-10]:            # keep the ten most recent
                    try:
                        os.remove(old)
                    except OSError:
                        pass
            self.s["build"] = VERSION
        except Exception as e:
            print("save backup skipped:", e)

    def _migrate(self):
        self._backup_before_migrate()
        self._market_topup_pending = True
        s = self.state
        s.setdefault("staff", dict(dispatcher=0, mx_controller=0, cabin_crew=0))
        s.setdefault("inbox", []); s.setdefault("achievements", {}); s.setdefault("cargo_board", [])
        s.setdefault("snapshots", []); s.setdefault("timeline", []); s.setdefault("years", []); s.setdefault("receivables", [])
        s.setdefault("charter_board", []); s.setdefault("charter_jobs", [])
        s.setdefault("career", dict(enabled=False, done={}, seen_chapter=0))
        # areas of operation: a company that has been flying keeps what it has been
        # using, so an established save is not suddenly grounded outside its home region
        co = s.get("company") or {}
        if co and not co.get("aoc_areas"):
            areas = {region_of(co.get("base"))}
            for f in s.get("flights", []):
                areas.add(region_of(f.get("origin")))
                areas.add(region_of(f.get("arrival") or f.get("destination")))
            for c in s.get("contracts", []):
                areas.add(region_of(c.get("hub")))
            co["aoc_areas"] = sorted(a for a in areas if a)
            co.setdefault("aoc_pending", [])
        # a single dispatched flight became a list of them
        s.setdefault("dispatched", [])
        if s.get("active_flight") and not any(x["id"] == s["active_flight"]["id"] for x in s["dispatched"]):
            s["dispatched"].append(s["active_flight"])
        if getattr(self, "_market_topup_pending", False) and s.get("market") is not None:
            self._market_topup_pending = False
            if self.top_up_market():
                self.notice("New aircraft have been listed on the market, business aircraft among them.")
        for p in s["pilots"] + s["hire_pool"]:
            p.setdefault("recency", {})
        s.setdefault("safety", dict(enabled=True, occurrences=[], since_incident=0, hull_losses=0, fatalities=0, injuries=0,
                                    premium_factor=1.0, grounded_until=None, investigation=None))
        s["company"].setdefault("difficulty", "standard")
        s.setdefault("events", [])
        s["company"].setdefault("clock_mode", "game")
        s["company"].setdefault("discord_webhook", "")
        s["company"].setdefault("weight_units", "lb")
        s["company"].setdefault("currency", CURRENCY_BY_COUNTRY.get((AIRPORTS.get(s["company"]["base"]) or {}).get("country"), "USD"))
        s["company"].setdefault("kpi", dict(otp=100.0, completion=100.0))
        # 1.8.0: types on the operations specifications. An existing certificate was
        # issued without a type restriction and stays that way.
        s["company"].setdefault("aoc_types", [])
        s["company"].setdefault("aoc_types_pending", [])
        self._atc_key = None
        for a in s["fleet"]:
            self._init_engines(a)
            a.setdefault("snags", []); a.setdefault("livery", None); a.setdefault("mx_log", []); a.setdefault("etops", AIRCRAFT[a["type"]]["cat"] in ("Widebody", "Narrowbody"))
        for p in s["pilots"] + s["hire_pool"]:
            p.setdefault("duty_h", 0.0); p.setdefault("duty_date", ""); p.setdefault("rest_until", None)
        for c in s["contracts"]:
            c.setdefault("kpi", dict(legs_scheduled=0, legs_flown=0, late=0, delay_min=0, satisfaction=80.0)); c.setdefault("cabin_crew", 0)
        for j in s["ferry_board"]:
            j.setdefault("docs", []); j.setdefault("snags", []); j.setdefault("countries", []); j.setdefault("etops", True); j.setdefault("permit", "Standard CofA"); j.setdefault("oceanic", False); j.setdefault("rejected", False)
            if not j.get("routing"):
                try:
                    j["routing"] = self.plan_route(j["type"], j["current"], j["destination"])
                except Exception:
                    j["routing"] = [j["destination"]]
                j["stops"] = len(j["routing"]) - 1
            if j.get("crew_days") is None or j.get("block_h") is None:
                ac = AIRCRAFT.get(j["type"])
                legs_n = max(1, len(j.get("routing") or [j["destination"]]))
                dist = j.get("distance") or 0
                bh = (dist / ac["cruise"] + 0.55 * legs_n) if ac else legs_n * 2.0
                j["block_h"] = round(bh, 1)
                j["crew_days"] = max(2, round(bh / 9 + (legs_n - 1) * 0.6))
            if not j.get("fee_parts"):
                cat = AIRCRAFT[j["type"]]["cat"] if j["type"] in AIRCRAFT else "Narrowbody"
                base, per, day_rate = {"Turboprop": (6000, 9, 900), "Regional": (8000, 12, 1100),
                                       "Narrowbody": (12000, 18, 1400), "Widebody": (22000, 32, 1900)}[cat]
                legs_n = max(1, len(j.get("routing") or [j["destination"]]))
                parts = [("Mobilisation and handling", base), (f"Sector fee, {int(j.get('distance') or 0):,} nm", money(per * (j.get("distance") or 0))),
                         (f"Crew day rate, 2 crew x {j['crew_days']} days", 2 * day_rate * j["crew_days"])]
                if legs_n > 1:
                    parts.append((f"Technical stops ({legs_n - 1})", 1800 * (legs_n - 1)))
                j["fee_parts"] = parts
                j["fee_scale"] = round(j["fee"] / max(1, sum(v for _, v in parts)), 2)
            j.setdefault("permits_needed", [c for c in (j.get("countries") or []) if c not in NO_PERMIT])
            if j.get("snags") and j.get("type") in AIRCRAFT:
                allowed = {x["code"] for x in snags_for(j["type"])}
                kept = [x for x in j["snags"] if x.get("code") in allowed]
                if len(kept) != len(j["snags"]):
                    j["snags"] = kept
                    j["restrictions"] = self._restrictions(kept)
        for t in s["acmi_tenders"]:
            t.setdefault("competitors", []); t.setdefault("renewal", False)

    def save(self, check=True):
        if check and self.s and self.s.get("career", {}).get("enabled"):
            try:
                self.check_objectives()
            except Exception:
                pass
        return self._save_raw()

    def _save_raw(self):
        c = self._conn()
        c.execute("INSERT OR REPLACE INTO kv (k, v) VALUES ('state', ?)", (json.dumps(self.state),))
        c.commit()
        c.close()

    def reset(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.state = None

    def store_pirep(self, flight_id, data):
        c = self._conn()
        c.execute("INSERT INTO pireps (flight_id, data) VALUES (?, ?)", (flight_id, json.dumps(data)))
        c.commit()
        c.close()

    def get_pirep(self, flight_id):
        c = self._conn()
        r = c.execute("SELECT data FROM pireps WHERE flight_id=? ORDER BY id DESC LIMIT 1", (flight_id,)).fetchone()
        c.close()
        return json.loads(r[0]) if r else None

    # ================================================================ helpers
    @property
    def s(self):
        if not self.state:
            raise GameError("No company exists yet.")
        return self.state

    def now(self):
        return parse(self.s["clock"])

    def nid(self, key):
        self.s["ids"][key] = self.s["ids"].get(key, 0) + 1
        return self.s["ids"][key]

    def post(self, category, desc, amount, ref=None):
        self.s["cash"] += amount
        self.s["ledger"].append(dict(id=self.nid("ledger"), date=self.s["clock"], category=category, desc=desc,
                                     amount=money(amount), balance=money(self.s["cash"]), ref=ref))
        if len(self.s["ledger"]) > 4000:
            self.s["ledger"] = self.s["ledger"][-4000:]

    REVENUE_CATEGORY = {"ferry": "Ferry revenue", "cargo": "Cargo flying", "acmi": "ACMI revenue",
                        "charter": "Charter revenue", "other": "Flight revenue"}

    def invoice(self, customer, desc, amount, ref=None, days=None, kind="other"):
        """Revenue is billed, not banked: customers pay on terms."""
        days = self.diff().get("terms", 30) if days is None else days
        due = self.now() + timedelta(days=days)
        r = dict(id=self.nid("inv"), customer=customer, desc=desc, amount=money(amount), issued=self.s["clock"],
                 due=iso(due), days=days, ref=ref, paid=False, kind=kind)
        self.s["receivables"].append(r)
        self.s["ledger"].append(dict(id=self.nid("ledger"), date=self.s["clock"], category="Invoiced",
                                     desc=f"{desc} — invoiced to {customer}, due {iso(due)[:10]}", amount=0,
                                     balance=money(self.s["cash"]), ref=ref))
        return r

    def _settle_invoices(self):
        now = self.now()
        for r in self.s["receivables"]:
            if r["paid"] or parse(r["due"]) > now:
                continue
            r["paid"] = True
            r["paid_on"] = self.s["clock"]
            self.post(self.REVENUE_CATEGORY.get(r.get("kind"), "Flight revenue"),
                      f"{r['desc']} — payment from {r['customer']}", r["amount"], ref=r.get("ref"))
        self.s["receivables"] = [r for r in self.s["receivables"] if not r["paid"] or (now - parse(r.get("paid_on", r["due"]))).days < 90]

    def outstanding(self):
        return sum(r["amount"] for r in self.s["receivables"] if not r["paid"])

    def rep(self, delta, why):
        r = self.s["company"]["reputation"]
        self.s["company"]["reputation"] = max(0, min(100, round(r + delta, 1)))
        self.notice(f"Reputation {'+' if delta >= 0 else ''}{delta}: {why}")

    def diff(self):
        return DIFFICULTY.get(self.s["company"].get("difficulty", "standard"), DIFFICULTY["standard"])

    def event(self, kind, text, detail=""):
        """A dated entry for the company history."""
        self.s["timeline"].insert(0, dict(id=self.nid("evt"), date=self.s["clock"], kind=kind, text=text, detail=detail))
        self.s["timeline"] = self.s["timeline"][:500]

    def mail(self, sender, subject, body, action=None, pin=False):
        self.s["inbox"].insert(0, dict(id=self.nid("mail"), date=self.s["clock"], sender=sender, subject=subject, body=body, action=action, pin=pin, read=False))
        self.s["inbox"] = self.s["inbox"][:150]

    def mark_read(self, mid=None):
        for m in self.s["inbox"]:
            if mid is None or m["id"] == mid:
                m["read"], m["pin"] = True, False
        self.save()

    def award(self, key):
        if key in self.s["achievements"]:
            return
        a = next((x for x in ACHIEVEMENTS if x[0] == key), None)
        if not a:
            return
        self.s["achievements"][key] = self.s["clock"]
        self.event("milestone", a[1], a[2])
        self.mail("Operator", f"Milestone: {a[1]}", a[2], action="company")
        self.notice(f"Milestone reached: {a[1]}")

    def check_achievements(self):
        st = self.s["stats"]
        if st["hours"] >= 100: self.award("hours_100")
        if st["hours"] >= 1000: self.award("hours_1000")
        if len(self.s["fleet"]) >= 3: self.award("fleet_3")
        if sum(1 for p in self.s["pilots"] if p["rank"] == "CPT") >= 5: self.award("five_captains")
        if self.s["company"]["reputation"] >= 70: self.award("rep_70")
        if self.s["contracts"]: self.award("first_acmi")

    def notice(self, text):
        self.s["notices"].insert(0, dict(date=self.s["clock"], text=text))
        self.s["notices"] = self.s["notices"][:80]

    def fleet_ac(self, ac_id):
        for a in self.s["fleet"]:
            if a["id"] == ac_id:
                return a
        raise GameError("Aircraft not found in fleet.")

    def pilot(self, pid):
        for p in self.s["pilots"]:
            if p["id"] == pid:
                return p
        raise GameError("Pilot not found.")

    def contract(self, cid):
        for c in self.s["contracts"]:
            if c["id"] == cid:
                return c
        raise GameError("Contract not found.")

    def job(self, jid):
        for j in self.s["ferry_board"]:
            if j["id"] == jid:
                return j
        raise GameError("Ferry job not found.")

    def fuel_price(self, icao):
        return self.s["company"]["fuel_price_usg"] * fuel_factor(icao)

    def _reg(self):
        while True:
            pre = self.rng.choice(REG_PREFIXES)
            if pre == "N":
                r = "N" + str(self.rng.randint(100, 999)) + "".join(self.rng.choice(string.ascii_uppercase) for _ in range(2))
            else:
                r = pre + "".join(self.rng.choice(string.ascii_uppercase) for _ in range(3))
            if not any(a["reg"] == r for a in self.s["fleet"] + self.s["market"]):
                return r

    @staticmethod
    def nearest_airport(lat, lon):
        a, d = nearest(lat, lon)
        return (a["icao"] if a else None), d

    def _market_cycle(self):
        m = (self.now().year - 2026) * 12 + self.now().month
        return 1 + 0.12 * math.sin(2 * math.pi * m / 48)

    # ================================================================ company
    def new_company(self, name, code, base, capital, simbrief_username="", sim_source="auto", difficulty="standard",
                    career=False, aoc_types=None):
        diff = DIFFICULTY.get(difficulty, DIFFICULTY["standard"])
        base = base.upper().strip()
        if base not in AIRPORTS:
            raise GameError(f"Base airport {base} is not in the airport database.")
        if not name.strip() or len(code.strip()) < 2:
            raise GameError("Company name and a 2–3 letter code are required.")
        fams = {a["family"] for a in AIRCRAFT.values()}
        types = [t for t in (aoc_types or []) if t in fams]
        if aoc_types and not types:
            raise GameError("That type rating is not one Operator knows about.")
        if len(types) > 3:
            raise GameError("A new certificate is issued for at most three types. Add the rest later by amendment.")
        now = datetime.utcnow().replace(second=0, microsecond=0)
        self.state = dict(
            company=dict(name=name.strip(), code=code.strip().upper()[:3], base=base, founded=iso(now), logo=None, reputation=diff["rep"],
                         simbrief_username=simbrief_username.strip(), simbrief_userid="", sim_source=sim_source, xp_host="127.0.0.1",
                         xp_port=49000, fuel_price_usg=round(2.35 * diff["fuel"], 2), clock_mode="game", discord_webhook="",
                         weight_units="lb", currency=CURRENCY_BY_COUNTRY.get((AIRPORTS.get(base) or {}).get("country"), "USD"),
                         kpi=dict(otp=100.0, completion=100.0),
                         difficulty=difficulty if difficulty in DIFFICULTY else "standard",
                         aoc_types=types, aoc_types_pending=[]),
            inbox=[], achievements={}, career=dict(enabled=bool(career), done={}, seen_chapter=0),
            clock=iso(now), cash=0.0, ledger=[], loans=[], ids={}, fleet=[], market=[], pilots=[], hire_pool=[], ferry_board=[], cargo_board=[],
            acmi_tenders=[], contracts=[], flights=[], active_flight=None, dispatched=[], notices=[], month_reports=[], events=[],
            staff=dict(dispatcher=0, mx_controller=0, cabin_crew=0),
            safety=dict(enabled=True, occurrences=[], since_incident=0, hull_losses=0, fatalities=0, injuries=0,
                        premium_factor=1.0, grounded_until=None, investigation=None),
            snapshots=[], timeline=[], years=[], receivables=[], charter_board=[], charter_jobs=[],
            last_day=iso(now)[:10], last_month=iso(now)[:7], stats=dict(flights=0, hours=0.0, nm=0.0),
        )
        self.post("Capital", "Founding capital", float(capital))
        self._atc_key = None
        self.refresh_market(full=True)
        self.refresh_hire_pool(full=True)
        self.refresh_ferry_board(full=True)
        self.refresh_cargo_board(full=True)
        self.refresh_tenders(full=True)
        self.notice(f"{name} established at {base} ({AIRPORTS[base]['name']}).")
        self.event("company", f"{name.strip()} founded at {base}", f"Air operator certificate issued; founding capital ${float(capital):,.0f}.")
        self.mail("Civil aviation authority", "Air operator certificate issued",
                  f"{name} is approved for ferry and ACMI operations from {base}. "
                  + (f"The certificate is issued for the {', '.join(types)}; no other type may be operated under it "
                     "until the operations specifications are amended, which you apply for from your company profile. "
                     if types else "")
                  + "You must have a licensed flight dispatcher on duty before any flight is released, and a "
                    "maintenance controller once you operate aircraft of your own. Welcome aboard.",
                  action="crew", pin=True)
        self.save()

    def set_logo(self, data_url):
        if data_url and len(data_url) > 6_000_000:
            raise GameError("Logo file is too large (max ~4 MB).")
        self.s["company"]["logo"] = data_url
        self.save()

    def update_settings(self, d):
        c = self.s["company"]
        if d.get("currency") in CURRENCIES:
            self.s["company"]["currency"] = d["currency"]
        if d.get("weight_units") in ("kg", "lb"):
            self.s["company"]["weight_units"] = d["weight_units"]
        if "dev_tools" in d:
            self.s["company"]["dev_tools"] = bool(d["dev_tools"])
        if "safety_enabled" in d:
            self.s["safety"]["enabled"] = bool(d["safety_enabled"])
        if "tutorial_hidden" in d:
            c["tutorial_hidden"] = bool(d["tutorial_hidden"])
        for k in ("simbrief_username", "simbrief_userid", "sim_source", "xp_host", "clock_mode", "discord_webhook"):
            if k in d:
                c[k] = str(d[k]).strip()
        if "xp_port" in d:
            c["xp_port"] = int(d["xp_port"])
        if "fuel_price_usg" in d:
            c["fuel_price_usg"] = max(0.5, float(d["fuel_price_usg"]))
        self.save()

    # ================================================================ market / fleet
    def _init_engines(self, a):
        n, cost, interval = ENGINES[a["family"]]
        if "engines" not in a:
            a["engines"] = [dict(pos=i + 1, hours_to_sv=self.rng.randint(int(interval * 0.15), interval)) for i in range(n)]
        a.setdefault("pbh", False)
        a.setdefault("pbh_rate", money(cost * n / interval * 1.15))

    def _listing(self, code=None):
        code = code or self.rng.choice(list(AIRCRAFT))
        ac = AIRCRAFT[code]
        yr = self.now().year
        lo, hi = build_year_range(code, yr)
        if code in ("B752", "B763", "B744", "A332", "B772"):
            want = (yr - 26, yr - 10)
        elif ac["value"][1] > 50:
            want = (yr - 9, yr - 1)
        else:
            want = (yr - 20, yr - 4)
        # a listing can only be as old as the type: no 2009 Falcon 8X
        year = self.rng.randint(max(lo, min(want[0], hi)), max(lo, min(want[1], hi)))
        age = yr - year
        cond = max(0.05, min(1.0, 1 - age / 26 + self.rng.uniform(-0.1, 0.1)))
        value = (ac["value"][0] + (ac["value"][1] - ac["value"][0]) * cond) * 1e6 * self._market_cycle()
        # business aircraft fly a few hundred hours a year, airliners a few thousand
        annual = self.rng.uniform(260, 520) if ac.get("charter") else self.rng.uniform(2200, 3600)
        hours = int(age * annual)
        leg_len = self.rng.uniform(1.6, 2.6) if ac.get("charter") else (
            self.rng.uniform(1.4, 2.6) if ac["cat"] != "Turboprop" else 0.9)
        cycles = int(hours / leg_len)
        lessor = self.rng.choice(LESSORS)
        loc = self.rng.choice([lessor["hq"], self.rng.choice(STORAGE)["icao"], self.rng.choice(list(OPERATOR_BASES.values()))])
        l = dict(id=self.nid("listing"), type=code, name=ac["name"], reg=self._reg(), year=year, hours=hours, cycles=cycles, lessor=lessor["name"],
                 price=money(value), lease=money(ac["lease"] * (0.7 + 0.5 * cond) * self.rng.uniform(0.92, 1.08) * self._market_cycle()),
                 deposit_months=3, min_term=self.rng.choice([12, 24, 36]), location=loc, cat=ac["cat"], family=ac["family"],
                 fh_since_a=self.rng.randint(0, 500), c_check_months=self.rng.randint(1, 20), config="Freighter" if ac["cargo"] else (f"{ac['seats']} seats" if ac.get("charter") else f"{ac['seats']}Y"),
                 etops=(ac["cat"] in ("Widebody", "Narrowbody")) and self.rng.random() > (0.5 if loc in [x["icao"] for x in STORAGE] else 0.1),
                 listed=self.s["clock"])
        self._init_engines(l)
        return l

    MARKET_SIZE = 18
    MARKET_BIZJETS = 4          # brokers always have business aircraft on their books

    def top_up_market(self):
        """Make sure the standing stock is there without waiting for the weekly cycle.
        Adds only; never removes a listing the player may be considering."""
        m = self.s["market"]
        biz = [t for t, a in AIRCRAFT.items() if a.get("charter")]
        airline = [t for t, a in AIRCRAFT.items() if not a.get("charter")]
        added = 0
        guard = 0
        while guard < 40:
            guard += 1
            have_biz = sum(1 for x in m if AIRCRAFT.get(x["type"], {}).get("charter"))
            if have_biz >= self.MARKET_BIZJETS:
                break
            m.append(self._listing(self.rng.choice(biz)))
            added += 1
        while len(m) < self.MARKET_SIZE and guard < 80:
            guard += 1
            m.append(self._listing(self.rng.choice(airline)))
            added += 1
        return added

    def refresh_market(self, full=False):
        m = self.s["market"]
        if full:
            m.clear()
        else:
            self.s["market"] = m = [x for x in m if self.rng.random() > 0.15]
        biz = [t for t, a in AIRCRAFT.items() if a.get("charter")]
        airline = [t for t, a in AIRCRAFT.items() if not a.get("charter")]
        guard = 0
        while len(m) < self.MARKET_SIZE and guard < 60:
            guard += 1
            have_biz = sum(1 for x in m if AIRCRAFT.get(x["type"], {}).get("charter"))
            pool = biz if have_biz < self.MARKET_BIZJETS else airline
            m.append(self._listing(self.rng.choice(pool)))

    # ---------------------------------------------------------------- delivery
    # Two pilots away from home for the trip. Ferry crews are contractors and charge
    # by the day; the seller or the lessor arranges it and adds a margin.
    DELIVERY_CREW_DAY = {"Turboprop": 1100, "Light jet": 1250, "Midsize jet": 1400,
                         "Super-midsize jet": 1600, "Heavy jet": 1900, "Regional": 1500,
                         "Narrowbody": 1800, "Widebody": 2400}

    def delivery_quote(self, type_code, frm, to=None):
        """What it costs to have an aircraft positioned to your base, and how long it
        takes. Priced as the positioning flight it is: fuel, fees at every stop, a
        contract crew for the days it takes and their way home, plus the seller's margin."""
        to = to or self.s["company"]["base"]
        ac = AIRCRAFT[type_code]
        if frm == to:
            return dict(needed=False, fee=0, days=0, legs=[], distance=0, hours=0.0)
        legs, dist, prev = [], 0.0, frm
        for stop in self.plan_route(type_code, frm, to):
            d = gc_nm(prev, stop) if prev in AIRPORTS and stop in AIRPORTS else 0.0
            legs.append(dict(origin=prev, destination=stop, nm=int(d)))
            dist += d
            prev = stop
        hours = dist / ac["cruise"] + 0.4 * len(legs)
        fuel_lb = hours * ac["burn"]
        fuel = fuel_lb / FUEL_LBS_PER_USG * self.fuel_price(frm)
        fees = len(legs) * (ac["mtow_kg"] / 1000 * 6.5 + 900)
        nav = ac["mtow_kg"] / 1000 * 0.9 * max(1, dist / 100)
        # a crew day is a sector day: nobody flies four long legs between two sunrises
        days = max(1, math.ceil(hours / 9) + (1 if len(legs) > 1 else 0))
        crew = 2 * days * self.DELIVERY_CREW_DAY.get(ac["cat"], 1500)
        expenses = 2 * (days * 240 + 1400)              # hotels, per diem and tickets home
        insurance = max(2500, dist * 1.8)
        fee = (fuel + fees + nav + crew + expenses + insurance) * 1.12
        return dict(needed=True, fee=money(fee), days=days + 1, legs=legs, distance=int(dist),
                    hours=round(hours, 1), origin=frm, destination=to,
                    parts=[("Fuel", money(fuel)), ("Landing, handling and parking", money(fees)),
                           ("Navigation and overflight", money(nav)),
                           (f"Delivery crew — two pilots, {days} day(s)", money(crew)),
                           ("Crew expenses and positioning", money(expenses)),
                           ("Ferry insurance cover", money(insurance)),
                           ("Arrangement fee", money(fee - fuel - fees - nav - crew - expenses - insurance))])

    def _begin_delivery(self, a, q, by):
        """The aircraft is on its way: unavailable, and at its old field until it lands."""
        eta = self.now() + timedelta(days=q["days"])
        a["status"] = "Delivery"
        a["delivery"] = dict(origin=q["origin"], destination=q["destination"], eta=iso(eta),
                             fee=q["fee"], legs=q["legs"], distance=q["distance"], by=by)
        a["mx_log"].append(dict(date=self.s["clock"],
                                text=f"Positioning {q['origin']} to {q['destination']} by {by}, {q['distance']:,} nm"))
        self.mail(by, f"Delivery arranged — {a['reg']}",
                  f"Our crew will position {a['reg']} from {q['origin']} to {q['destination']}, "
                  f"{q['distance']:,} nm in {len(q['legs'])} sector(s). Expect arrival on {eta:%d %B %Y}. "
                  "The aircraft is not available for your own operations until it lands.", action="fleet")
        return eta

    def _settle_deliveries(self):
        now = self.now()
        for a in self.s["fleet"]:
            d = a.get("delivery")
            if not d or a["status"] != "Delivery" or parse(d["eta"]) > now:
                continue
            a["location"], a["status"] = d["destination"], "Available"
            a["mx_log"].append(dict(date=self.s["clock"], text=f"Arrived {d['destination']} on delivery"))
            a.pop("delivery", None)
            self.event("fleet", f"{a['reg']} delivered to {d['destination']}",
                       f"Positioned {d['distance']:,} nm from {d['origin']} by {d['by']}.")
            self.mail(d["by"], f"{a['reg']} delivered — {d['destination']}",
                      f"{a['reg']} is on the ground at {d['destination']} and has been handed over. "
                      "The technical log and delivery documents are with your maintenance control.",
                      action="fleet", pin=True)
            self.notice(f"{a['reg']} has arrived at {d['destination']}.")

    def _add_to_fleet(self, l, owned, lease_end=None):
        ac = AIRCRAFT[l["type"]]
        a = dict(id=self.nid("ac"), type=l["type"], name=l["name"], reg=l["reg"], year=l["year"], hours=l["hours"], cycles=l["cycles"],
                 owned=owned, lessor=None if owned else l["lessor"], lease=0 if owned else l["lease"], lease_end=lease_end, value=l["price"],
                 location=l["location"], status="Available", contract_id=None, config=l["config"], fh_since_a=l["fh_since_a"],
                 c_check_due=iso(self.now() + timedelta(days=30 * (C_CHECK_MONTHS - l["c_check_months"]))), mx_until=None,
                 family=ac["family"], cat=ac["cat"], acquired=self.s["clock"], engines=l["engines"], pbh=False, pbh_rate=l["pbh_rate"],
                 etops=l["etops"], snags=[], livery=None, mx_log=[dict(date=self.s["clock"], text="Delivered to fleet")])
        self.s["fleet"].append(a)
        self.refresh_hire_pool()
        return a

    def listing(self, listing_id):
        l = next((x for x in self.s["market"] if x["id"] == int(listing_id)), None)
        if not l:
            raise GameError("Listing no longer available.")
        return l

    def buy(self, listing_id, deliver=False):
        l = self.listing(listing_id)
        q = self.delivery_quote(l["type"], l["location"]) if deliver else dict(needed=False, fee=0)
        need = l["price"] + (q["fee"] if q["needed"] else 0)
        if self.s["cash"] < need:
            raise GameError(f"Insufficient funds: purchase price is ${l['price']:,}"
                            + (f" plus ${q['fee']:,} delivery." if q["needed"] else "."))
        self.post("Aircraft purchase", f"Purchase {l['name']} {l['reg']} from {l['lessor']}", -l["price"])
        self.s["market"].remove(l)
        a = self._add_to_fleet(l, owned=True)
        self.event("fleet", f"{a['reg']} purchased — {a['name']}", f"{l['year']} build, {l['hours']:,} hours, ${l['price']:,} from {l['lessor']}.")
        if q["needed"]:
            self.post("Aircraft delivery", f"Positioning {a['reg']} {q['origin']} to {q['destination']}", -q["fee"], ref=a["id"])
            eta = self._begin_delivery(a, q, l["lessor"])
            self.notice(f"{a['reg']} ({a['name']}) purchased. Being delivered to {q['destination']}, arriving {eta:%d %b}.")
        else:
            self.notice(f"{a['reg']} ({a['name']}) purchased. Aircraft is at {a['location']}.")
        self.save()
        return a

    def lease(self, listing_id, deliver=False):
        l = self.listing(listing_id)
        dep = l["lease"] * l["deposit_months"]
        q = self.delivery_quote(l["type"], l["location"]) if deliver else dict(needed=False, fee=0)
        need = dep + l["lease"] + (q["fee"] if q["needed"] else 0)
        if self.s["cash"] < need:
            raise GameError(f"Insufficient funds: deposit ${dep:,} plus first month ${l['lease']:,}"
                            + (f" plus ${q['fee']:,} delivery" if q["needed"] else "") + " required.")
        self.post("Lease deposit", f"Security deposit {l['reg']} ({l['lessor']})", -dep)
        self.post("Lease", f"First month lease {l['reg']} ({l['lessor']})", -l["lease"])
        self.s["market"].remove(l)
        a = self._add_to_fleet(l, owned=False, lease_end=iso(self.now() + timedelta(days=30 * l["min_term"])))
        a["deposit"] = dep
        self.event("fleet", f"{a['reg']} leased — {a['name']}", f"{l['min_term']}-month operating lease from {l['lessor']} at ${l['lease']:,}/month.")
        if q["needed"]:
            self.post("Aircraft delivery", f"Positioning {a['reg']} {q['origin']} to {q['destination']}", -q["fee"], ref=a["id"])
            eta = self._begin_delivery(a, q, l["lessor"])
            self.notice(f"{a['reg']} ({a['name']}) leased from {l['lessor']}. Delivery to {q['destination']} arriving {eta:%d %b}.")
        else:
            self.notice(f"{a['reg']} ({a['name']}) delivered on {l['min_term']}-month operating lease from {l['lessor']}.")
        self.save()
        return a

    REREG_FEE = {"Turboprop": 4200, "Light jet": 5200, "Midsize jet": 5800, "Super-midsize jet": 6600,
                 "Heavy jet": 9500, "Regional": 7500, "Narrowbody": 12000, "Widebody": 26000}

    def rename_aircraft(self, ac_id, reg=None, name=None, fleet_no=None, sim_type=None):
        """Re-register a tail, and optionally give it a name and a fleet number.
        Re-registration is paperwork with a fee and a day out of service."""
        a = self.fleet_ac(ac_id)
        out = []
        if name is not None:
            a["nickname"] = str(name).strip()[:40] or None
            out.append(f"named {a['nickname']}" if a["nickname"] else "name removed")
        if fleet_no is not None:
            a["fleet_no"] = str(fleet_no).strip()[:6] or None
            out.append(f"fleet number {a['fleet_no']}" if a["fleet_no"] else "fleet number removed")
        if sim_type is not None:
            a["sim_type"] = str(sim_type).strip()[:60] or None
            out.append(f"flown in the simulator as {a['sim_type']}" if a["sim_type"] else "simulator aircraft cleared")

        if reg:
            new = str(reg).upper().strip()
            if new != a["reg"]:
                if not re.fullmatch(r"[A-Z0-9]{1,2}-?[A-Z0-9]{2,5}", new):
                    raise GameError("A registration looks like G-PAGA, N772PA, 9H-XYZ or PH-BXA: "
                                    "letters and digits, with an optional hyphen, up to seven characters.")
                taken = ({x["reg"] for x in self.s["fleet"] if x["id"] != a["id"]}
                         | {x["reg"] for x in self.s["market"]}
                         | {j["reg"] for j in self.s["ferry_board"] if j.get("reg")}
                         | {j["reg"] for j in self.s["cargo_board"] if j.get("reg")})
                if new in taken:
                    raise GameError(f"{new} is already carried by another aircraft.")
                af = self.s.get("active_flight")
                if af and af.get("aircraft_id") == a["id"] and af.get("status") in ("Dispatched", "Tracking"):
                    raise GameError("The aircraft is on a flight. Re-register it once the sector is filed.")
                if a["status"] not in ("Available", "Parked"):
                    raise GameError(f"{a['reg']} is {a['status'].lower()}; re-registration needs it on the ground and free.")
                fee = self.REREG_FEE.get(AIRCRAFT[a["type"]]["cat"], 12000)
                if not a["owned"]:
                    fee = int(fee * 1.5)          # the lessor's consent and their lawyers
                if self.s["cash"] < fee:
                    raise GameError(f"Re-registration costs ${fee:,} in fees and paint.")
                old, (country, authority) = a["reg"], register_for(new)
                self.post("Aircraft admin", f"Re-registration {old} to {new} — {authority} fees, paint and documents", -fee)
                a["reg"] = new
                a["reregistered"] = dict(previous=old, date=self.s["clock"], authority=authority, country=country)
                a["status"] = "Maintenance" if False else a["status"]
                for j in self.s["charter_jobs"]:
                    if j.get("aircraft_id") == a["id"]:
                        j["reg"] = new
                for c in self.s["contracts"]:
                    if c.get("aircraft_id") == a["id"]:
                        c["reg"] = new
                self.event("fleet", f"{old} re-registered as {new}",
                           f"Entered on the {country} register with the {authority}.")
                self.notice(f"{old} is now {new} — ${fee:,} in fees, paint and documents.")
                out.append(f"re-registered as {new} with the {authority}")
        self.save()
        if not out:
            return "Nothing changed."
        msg = "; ".join(out)
        return msg[0].upper() + msg[1:]

    def dispose(self, ac_id):
        a = self.fleet_ac(ac_id)
        if a["status"] != "Available":
            raise GameError("Aircraft must be available (not on contract, in maintenance or in flight).")
        if a["owned"]:
            price = money(a["value"] * self.rng.uniform(0.82, 0.95) * self._market_cycle())
            self.post("Aircraft sale", f"Sale of {a['name']} {a['reg']}", price)
            self.event("fleet", f"{a['reg']} sold", f"{a['name']} sold for ${price:,}.")
            self.notice(f"{a['reg']} sold for ${price:,}.")
        else:
            early = self.now() < parse(a["lease_end"])
            pen = money(a["lease"] * 3) if early else 0
            if pen:
                self.post("Lease termination", f"Early return penalty {a['reg']} ({a['lessor']})", -pen)
            self.post("Lease deposit", f"Deposit returned {a['reg']}", a.get("deposit", 0))
            self.event("fleet", f"{a['reg']} returned to {a['lessor']}", f"{a['name']} off lease.")
            self.notice(f"{a['reg']} returned to {a['lessor']}." + (f" Early termination penalty ${pen:,}." if pen else ""))
        self.s["fleet"].remove(a)
        self.save()

    def _ground(self, a, days, why, prev=None):
        a["prev_status"] = prev or (a["status"] if a["status"] != "Maintenance" else a.get("prev_status", "Available"))
        a["status"] = "Maintenance"
        a["mx_until"] = iso(self.now() + timedelta(days=days))
        a["mx_reason"] = why
        a["mx_log"].insert(0, dict(date=self.s["clock"], text=f"{why} ({days} days)"))

    def do_maintenance(self, ac_id, check):
        a = self.fleet_ac(ac_id)
        if a["status"] not in ("Available", "ACMI"):
            raise GameError("Aircraft is not on the ground and available.")
        ac = AIRCRAFT[a["type"]]
        mro = self.rng.choice(MROS)["name"]
        if check == "A":
            cost, days, why = ac["mx_fh"] * 110, 2, f"A-check at {mro}"
            a["fh_since_a"] = 0
        elif check == "C":
            cost, days, why = ac["mx_fh"] * 900, 14, f"C-check at {mro}"
            a["fh_since_a"] = 0
            a["c_check_due"] = iso(self.now() + timedelta(days=30 * C_CHECK_MONTHS))
        elif check == "ESV":
            n, ecost, interval = ENGINES[a["family"]]
            due = [e for e in a["engines"] if e["hours_to_sv"] <= 500]
            if not due:
                raise GameError("No engine is due a shop visit.")
            cost, days, why = ecost * len(due) * (0.0 if a["pbh"] else 1.0), 25, f"Engine shop visit x{len(due)} ({ENGINE_OEM[a['family']]})"
            for e in due:
                e["hours_to_sv"] = interval
        elif check == "SNAGS":
            if not a["snags"]:
                raise GameError("No open defects.")
            cost, days, why = sum(x["cost"] for x in a["snags"]) * 0.6, 2, f"Defect rectification: {', '.join(x['code'] for x in a['snags'])}"
            a["snags"] = []
        else:
            raise GameError("Unknown check.")
        if self.s["cash"] < cost:
            raise GameError(f"Insufficient funds (${cost:,.0f}).")
        if cost:
            self.post("Maintenance", f"{why} — {a['reg']}", -cost)
        self._ground(a, days, why)
        self.notice(f"{a['reg']}: {why}; {days} days downtime.")
        self.save()

    def set_pbh(self, ac_id, on):
        a = self.fleet_ac(ac_id)
        a["pbh"] = bool(on)
        if on:
            self.notice(f"{a['reg']} enrolled in {ENGINE_OEM[a['family']]} power-by-the-hour at ${a['pbh_rate']:,}/FH.")
        self.save()

    def _check_airworthy(self, a):
        if a["status"] == "Maintenance":
            raise GameError(f"{a['reg']} is unavailable: {a.get('mx_reason', 'maintenance')} until {a['mx_until'][:10]}.")
        if a["fh_since_a"] >= A_CHECK_FH:
            raise GameError(f"{a['reg']} is overdue an A-check ({int(a['fh_since_a'])} FH since last).")
        if self.now() > parse(a["c_check_due"]):
            raise GameError(f"{a['reg']} C-check is overdue.")
        if not a["pbh"] and any(e["hours_to_sv"] <= 0 for e in a["engines"]):
            raise GameError(f"{a['reg']} has an engine at shop-visit limit. Schedule an engine shop visit or enrol in PBH.")
        if not self.s["staff"]["mx_controller"] * STAFF["mx_controller"]["per_aircraft"] >= len(self.s["fleet"]):
            raise GameError(f"Not enough maintenance controllers for {len(self.s['fleet'])} aircraft (one per {STAFF['mx_controller']['per_aircraft']}).")

    # ================================================================ staff & crew
    def staff_change(self, role, delta):
        if role not in STAFF:
            raise GameError("Unknown role.")
        st = self.s["staff"]
        new = st[role] + int(delta)
        if new < 0:
            raise GameError("Cannot go below zero.")
        if role == "cabin_crew" and new < self._cabin_assigned():
            raise GameError("Cabin crew are assigned to active contracts.")
        if delta > 0:
            self.post("Crew", f"Recruitment {STAFF[role]['title']} x{delta}", -1200 * delta)
        else:
            self.post("Crew", f"Severance {STAFF[role]['title']} x{-delta}", STAFF[role]["salary"] * delta)
        st[role] = new
        self.save()

    def _cabin_assigned(self):
        return sum(c.get("cabin_crew", 0) for c in self.s["contracts"] if c["status"] in ("Active", "Pending start"))

    @staticmethod
    def rank_salary(rank, family):
        wide = family in ("A330/A350", "B777/787", "B747", "B757/767")
        small = family in ("ATR", "Q400", "CRJ", "E-Jet")
        return (15000 if wide else 8500 if small else 11500) if rank == "CPT" else (8000 if wide else 4500 if small else 6200)

    def upgrade_check(self, p):
        """Command upgrade eligibility for a first officer."""
        need_total, need_company = 2500, 250
        reasons = []
        if p["rank"] != "FO":
            return dict(eligible=False, reasons=["Already a captain."])
        if p["status"] != "Available":
            reasons.append("Pilot must be available (not on a job, contract, medical or training).")
        if p["hours"] < need_total:
            reasons.append(f"{need_total - p['hours']:,.0f} more total hours required ({p['hours']:,.0f} of {need_total:,}).")
        if p.get("company_hours", 0) < need_company:
            reasons.append(f"{need_company - p.get('company_hours', 0):,.0f} more hours with this company required ({p.get('company_hours', 0):,.0f} of {need_company}).")
        cost = 34000 if any(f in ("A330/A350", "B777/787", "B747") for f in p["ratings"]) else 26000
        new_sal = money(max(self.rank_salary("CPT", f) for f in p["ratings"]) * (p["salary"] / max(1, max(self.rank_salary("FO", f) for f in p["ratings"]))))
        return dict(eligible=not reasons, reasons=reasons, cost=cost, days=28, new_salary=new_sal,
                    total_hours=p["hours"], company_hours=p.get("company_hours", 0), need_total=need_total, need_company=need_company)

    def promote(self, pid):
        p = self.pilot(pid)
        chk = self.upgrade_check(p)
        if not chk["eligible"]:
            raise GameError(" ".join(chk["reasons"]))
        if self.s["cash"] < chk["cost"]:
            raise GameError(f"The command upgrade course costs ${chk['cost']:,}.")
        self.post("Crew training", f"Command upgrade course — {p['name']}", -chk["cost"])
        p["rank"] = "CPT"
        p["salary"] = chk["new_salary"]
        p["status"], p["training_until"] = "Training", iso(self.now() + timedelta(days=chk["days"]))
        p["upgraded"] = self.s["clock"]
        self.event("crew", f"{p['name']} upgraded to captain", f"Command course under way; {p['hours']:,.0f} total hours, {p.get('company_hours', 0):,.0f} with the company.")
        self.mail("Crew training", f"Command upgrade — {p['name']}", f"{p['name']} has started the command course: simulator details, line training and a line check over {chk['days']} days. Salary rises to ${chk['new_salary']:,} per month on completion.", action="crew")
        self.notice(f"{p['name']} promoted to captain; command course under way.")
        self.award("first_command")
        self.save()

    def _candidate(self, fam=None, rank=None):
        rank = rank or self.rng.choice(["CPT", "CPT", "FO", "FO", "FO"])
        # a type-restricted certificate draws from a smaller world: half the people on
        # the market are rated on something you are actually approved to operate
        pool = sorted(set(a["family"] for a in AIRCRAFT.values()))
        mine = self.aoc_types()
        if mine and self.rng.random() < 0.55:
            pool = list(mine)
        fam = fam or self.rng.choice(pool)
        base_sal = self.rank_salary(rank, fam)
        hours = self.rng.randint(4000, 16000) if rank == "CPT" else self.rng.randint(400, 4500)
        country = (AIRPORTS.get(self.s["company"]["base"]) or {}).get("country")
        name, origin = crew_name(self.rng, country)
        # two people on a roster should not share a surname by accident
        taken = {p["name"] for p in self.s["pilots"]} | {c["name"] for c in self.s["hire_pool"]}
        firsts = {t.split()[0] for t in taken}
        surnames = {t.split()[-1] for t in taken}
        for _ in range(10):
            if name.split()[0] not in firsts and name.split()[-1] not in surnames:
                break
            name, origin = crew_name(self.rng, country)
        return dict(id=self.nid("pilot"), name=name, origin=origin, rank=rank, ratings=[fam],
                    hours=hours, salary=money(base_sal * self.rng.uniform(0.92, 1.1)), status="Available", contract_id=None, job_id=None,
                    training_until=None, location=self.s["company"]["base"], duty_h=0.0, duty_date="", rest_until=None,
                    company_hours=0.0, recency={})

    def needed_ratings(self):
        """What the company needs crews for: the aircraft it owns and the work it has taken on."""
        want = {AIRCRAFT[a["type"]]["family"] for a in self.s["fleet"] if a["type"] in AIRCRAFT}
        want |= {j["family"] for j in self.s["ferry_board"] if j["status"] == "Accepted"}
        want |= {j["family"] for j in self.s["cargo_board"] if j["status"] == "Accepted"}
        want |= {c["family"] for c in self.s["contracts"] if c["status"] in ("Active", "Pending start")}
        # a certificate issued for one type should put crews for it on the market from
        # day one, otherwise the first job has nobody to fly it
        want |= set(self.aoc_types())
        return want

    def refresh_hire_pool(self, full=False):
        p = self.s["hire_pool"]
        if full:
            p.clear()
        else:
            self.s["hire_pool"] = p = [x for x in p if self.rng.random() > 0.3]
        while len(p) < 12:
            p.append(self._candidate())
        # There is always somebody on the market for what you actually operate: buying a
        # Saab 340 and finding nobody in the world rated on it is not a puzzle worth having.
        for fam in self.needed_ratings():
            have_cpt = sum(1 for x in p if x["rank"] == "CPT" and fam in x["ratings"])
            have_fo = sum(1 for x in p if x["rank"] == "FO" and fam in x["ratings"])
            employed_cpt = sum(1 for x in self.s["pilots"] if x["rank"] == "CPT" and fam in x["ratings"])
            employed_fo = sum(1 for x in self.s["pilots"] if x["rank"] == "FO" and fam in x["ratings"])
            for _ in range(max(0, 2 - have_cpt - employed_cpt)):
                p.insert(0, self._candidate(fam=fam, rank="CPT"))
            for _ in range(max(0, 2 - have_fo - employed_fo)):
                p.insert(0, self._candidate(fam=fam, rank="FO"))

    def hire(self, pid):
        c = next((x for x in self.s["hire_pool"] if x["id"] == pid), None)
        if not c:
            raise GameError("Candidate no longer available.")
        if self.s["cash"] < 3500:
            raise GameError("Insufficient funds for recruitment fee.")
        self.post("Crew", f"Recruitment {c['rank']} {c['name']}", -3500)
        self.s["hire_pool"].remove(c)
        c["hired"] = self.s["clock"]
        for f in c["ratings"]:
            c.setdefault("recency", {}).setdefault(f, {})["trained"] = self.s["clock"]
        self.s["pilots"].append(c)
        self.save()

    def rename_pilot(self, pid, name=None, is_self=None):
        """Change the name on a crew file, and optionally mark that file as yours.
        Plenty of people want their own name on the roster rather than a generated
        one. The flag is cosmetic: duty, currency and payroll work the same either
        way, and the crew file records that the name was changed."""
        p = self.pilot(pid)
        if name is not None:
            new = " ".join(str(name).split())[:40]
            if not new:
                raise GameError("A crew file needs a name.")
            if not re.fullmatch(r"[^\d<>{}\[\]\\/|@#$%^*_=+~`]{2,40}", new):
                raise GameError("Names are letters, spaces, hyphens and apostrophes — no digits or symbols.")
            if any(x["name"].lower() == new.lower() and x["id"] != p["id"]
                   for x in self.s["pilots"] + self.s["hire_pool"]):
                raise GameError(f"{new} is already on the roster. Two crew files cannot share a name.")
            if new != p["name"]:
                was = p["name"]
                p.setdefault("former_names", []).append(was)
                p["name"] = new
                p["renamed"] = self.s["clock"]
                self.event("crew", f"Crew file amended — {p['rank']} {new}",
                           f"Name changed from {was}. Licence, ratings and record unaffected.")
        if is_self is not None:
            if is_self:
                for x in self.s["pilots"]:
                    x.pop("is_self", None)
                p["is_self"] = True
            else:
                p.pop("is_self", None)
        self.save()
        return p

    def me(self):
        """The crew file the player has claimed as their own, if any."""
        return next((p for p in self.s["pilots"] if p.get("is_self")), None)

    def release_pilot(self, pid):
        p = self.pilot(pid)
        if p["status"] != "Available":
            raise GameError("Pilot is assigned; release from contract or job first.")
        self.post("Crew", f"Severance {p['name']}", -p["salary"])
        self.s["pilots"].remove(p)
        self.save()

    def train(self, pid, family):
        p = self.pilot(pid)
        if p["status"] != "Available":
            raise GameError("Pilot must be available.")
        if family in p["ratings"]:
            raise GameError("Pilot already holds that rating.")
        cost = 32000 if family in ("A330/A350", "B777/787", "B747") else 26000
        if self.s["cash"] < cost:
            raise GameError(f"Type rating course costs ${cost:,}.")
        self.post("Crew training", f"Type rating {family} — {p['name']}", -cost)
        p["ratings"].append(family)
        self._grant_recency(p, family)
        p["status"], p["training_until"] = "Training", iso(self.now() + timedelta(days=21))
        self.save()

    def is_current(self, p, family):
        """Three takeoffs and landings on type in the last 90 days, or recent training."""
        rec = (p.get("recency") or {}).get(family) or {}
        dates = rec.get("landings") or []
        cutoff = self.now() - timedelta(days=RECENCY_DAYS)
        recent = [d for d in dates if parse(d) > cutoff]
        if len(recent) >= RECENCY_NEEDED:
            return True, len(recent)
        if rec.get("trained") and parse(rec["trained"]) > cutoff:
            return True, len(recent)
        return False, len(recent)

    def _log_landing(self, p, family):
        rec = p.setdefault("recency", {}).setdefault(family, {})
        rec.setdefault("landings", []).append(self.s["clock"])
        rec["landings"] = rec["landings"][-12:]

    def _grant_recency(self, p, family):
        p.setdefault("recency", {}).setdefault(family, {})["trained"] = self.s["clock"]

    def recency_training(self, pid, family):
        """A simulator detail to regain currency on type."""
        p = self.pilot(pid)
        if family not in p["ratings"]:
            raise GameError(f"{p['name']} does not hold a {family} rating.")
        if p["status"] != "Available":
            raise GameError("Pilot must be available.")
        ok, _ = self.is_current(p, family)
        if ok:
            raise GameError(f"{p['name']} is already current on {family}.")
        cost = 4200 if family in ("A330/A350", "B777/787", "B747") else 3200
        if self.s["cash"] < cost:
            raise GameError(f"A recency detail costs ${cost:,}.")
        self.post("Crew training", f"Recency simulator detail {family} — {p['name']}", -cost)
        self._grant_recency(p, family)
        p["status"], p["training_until"] = "Training", iso(self.now() + timedelta(days=1))
        self.notice(f"{p['name']} completed a recency detail on {family}.")
        self.save()

    def _duty_today(self, p):
        return p["duty_h"] if p.get("duty_date") == self.s["clock"][:10] else 0.0

    def crew_legal(self, p, planned_h):
        if p.get("rest_until") and parse(p["rest_until"]) > self.now():
            return False, f"in rest until {p['rest_until'][11:]}Z {p['rest_until'][:10]}"
        if self._duty_today(p) + planned_h + 1.5 > MAX_FDP_H:
            return False, f"would exceed {MAX_FDP_H:.0f} h FDP ({self._duty_today(p):.1f} h duty today)"
        return True, ""

    def _log_duty(self, p, block_h):
        today = self.s["clock"][:10]
        if p.get("duty_date") != today:
            p["duty_h"], p["duty_date"] = 0.0, today
        p["duty_h"] += block_h + 1.5
        if p["duty_h"] >= 9:
            p["rest_until"] = iso(self.now() + timedelta(hours=REST_H))

    def remove_rating(self, pid, family):
        p = self.pilot(pid)
        if family not in p["ratings"]:
            raise GameError("The pilot does not hold that rating.")
        if len(p["ratings"]) <= 1:
            raise GameError("A pilot must hold at least one type rating.")
        if p["status"] not in ("Available", "Training"):
            raise GameError("Pilot must be available.")
        if p["status"] == "Training" and p["training_until"] and p["ratings"][-1] == family:
            refund = money((32000 if family in ("A330/A350", "B777/787", "B747") else 26000) * 0.5)
            self.post("Crew training", f"Course cancelled, partial refund — {p['name']} ({family})", refund)
            p["status"], p["training_until"] = "Available", None
            self.notice(f"Type rating course for {p['name']} on {family} cancelled; 50% of the course fee refunded.")
        else:
            self.notice(f"{family} rating removed from {p['name']}'s licence; it will lapse without recurrent training.")
        p["ratings"].remove(family)
        self.save()

    def _free_pilots(self, family, rank):
        return [p for p in self.s["pilots"] if p["status"] == "Available" and family in p["ratings"] and p["rank"] == rank]

    # ================================================================ routing
    MIN_RWY = {"Turboprop": 4500, "Regional": 5500, "Narrowbody": 7000, "Widebody": 8500,
               "Light jet": 4000, "Midsize jet": 4500, "Super-midsize jet": 5000, "Heavy jet": 6000}

    def plan_route(self, type_code, origin, destination, reserve=0.82):
        """Great-circle routing with technical stops the type can actually make.

        Returns the list of waypoints after the origin, ending at the destination.
        Stops must have a runway long enough for the type and are chosen to make the
        most progress per leg while staying inside the still-air range less reserves.
        """
        ac = AIRCRAFT[type_code]
        legmax = ac["range_nm"] * reserve
        need = self.MIN_RWY[ac["cat"]]
        if origin not in AIRPORTS or destination not in AIRPORTS:
            return [destination]
        # the set of fields long enough for a category never changes, so work it out
        # once instead of walking every runway on every route
        cache = getattr(self, "_stop_cache", None)
        if cache is None:
            cache = self._stop_cache = {}
        if need not in cache:
            cache[need] = [k for k in set(MAJOR) | set(FERRY_STOPS)
                           if k in AIRPORTS and (perf.longest(k) or 0) >= need]
        cand = [k for k in cache[need] if k not in (origin, destination)]
        route, cur, guard = [], origin, 0
        while gc_nm(cur, destination) > legmax and guard < 12:
            guard += 1
            remaining = gc_nm(cur, destination)
            best, bs = None, -1e9
            for k in cand:
                if k in route:
                    continue
                d = gc_nm(cur, k)
                if d > legmax or d < 200:
                    continue
                left = gc_nm(k, destination)
                if left >= remaining:          # must make progress
                    continue
                detour = d + left - remaining
                score = (remaining - left) - detour * 1.5 + FERRY_STOPS.get(k, 0) * 520
                if score > bs:
                    best, bs = k, score
            if not best:
                break
            route.append(best)
            cur = best
        route.append(destination)
        return route

    def route_legs(self, type_code, origin, destination):
        pts = [origin] + self.plan_route(type_code, origin, destination)
        legmax = AIRCRAFT[type_code]["range_nm"] * 0.9
        out = []
        for i in range(len(pts) - 1):
            d = gc_nm(pts[i], pts[i + 1])
            out.append(dict(seq=i + 1, origin=pts[i], destination=pts[i + 1],
                            distance=int(d), over_range=d > legmax))
        return out

    def route_feasible(self, type_code, origin, destination):
        """Composing a job tries this far more often than it keeps the answer, and the
        route behind it is already cached, so the verdict is kept too."""
        key = (type_code, origin, destination)
        cache = getattr(self, "_feas", None)
        if cache is None:
            cache = self._feas = {}
        got = cache.get(key)
        if got is None:
            got = cache[key] = not any(l["over_range"] for l in self.route_legs(type_code, origin, destination))
            if len(cache) > 60000:
                cache.clear()
        return got

    # ================================================================ career
    CAREER_CAPITAL = 2_400_000

    CHAPTERS = [
        dict(key="start", title="Getting started",
             blurb="A dispatcher, two pilots and a phone. You do not own an aircraft and you do not need one: "
                   "ferry work pays you to fly somebody else's.",
             goals=[
                 dict(id="dispatcher", text="Hire a flight dispatcher",
                      why="No flight can be released without one on duty. It is the first thing an AOC requires.",
                      go="crew", check=lambda s, g: s["staff"].get("dispatcher", 0) >= 1),
                 dict(id="crew2", text="Hire a captain and a first officer on the same type rating",
                      why="A flight needs a commander and a second pilot, both rated on the aircraft.",
                      go="crew", check=lambda s, g: any(
                          any(p["rank"] == "CPT" and f in p["ratings"] for p in s["pilots"])
                          and any(p["rank"] == "FO" and f in p["ratings"] for p in s["pilots"])
                          for f in {r for p in s["pilots"] for r in p["ratings"]})),
                 dict(id="accept", text="Accept a ferry job your crew is rated for",
                      why="The board is refreshed constantly. Match the rating to the crew you just hired.",
                      go="ferry", check=lambda s, g: any(j["status"] in ("Accepted", "Completed") for j in s["ferry_board"])
                                                    or g.ferries_done() > 0),
                 dict(id="firstflight", text="File your first PIREP",
                      why="Dispatch the leg, fly it in the simulator or hand it to the crew, then file.",
                      go="dispatch", check=lambda s, g: len(s["flights"]) >= 1),
             ]),
        dict(key="paperwork", title="Learning the paperwork",
             blurb="Ferry work is paperwork with flying attached. Permits take time, defects carry limits, "
                   "and the client is paying for the aircraft to arrive legally.",
             goals=[
                 dict(id="delivered", text="Deliver a ferry job and get paid",
                      why="Payment lands when the aircraft reaches its destination, on the terms agreed.",
                      go="ferry", check=lambda s, g: g.ferries_done() >= 1),
                 dict(id="permit", text="Fly a sector on a special flight permit",
                      why="An aircraft out of storage carries defects and restrictions. Open the permit and read it.",
                      go="ferry", check=lambda s, g: any(f.get("snags") for f in s["flights"])),
                 dict(id="three", text="Complete three ferry jobs",
                      why="Reputation builds with delivery. Better work follows.",
                      go="ferry", check=lambda s, g: g.ferries_done() >= 3),
                 dict(id="rep50", text="Reach 50 reputation",
                      why="Widebody work opens at 55, and better-paying clients come with standing.",
                      go="dashboard", check=lambda s, g: s["company"]["reputation"] >= 50),
             ]),
        dict(key="crewing", title="Crewing for the carriers",
             blurb="Freight carriers are short of crews. They provide the aircraft, the fuel and the load; "
                   "you provide rated pilots and fly their schedule.",
             goals=[
                 dict(id="cargo1", text="Accept a cargo pairing",
                      why="Their aircraft, their fuel. The cheapest way to earn while you build a fleet.",
                      go="cargo", check=lambda s, g: any(j["status"] in ("Accepted", "Completed") for j in s["cargo_board"])
                                                    or g.pairings_done() > 0),
                 dict(id="cargo_done", text="Complete a pairing and collect the block-hour pay",
                      why="Every sector in order, then payment on completion.",
                      go="cargo", check=lambda s, g: g.pairings_done() >= 1),
                 dict(id="cash5", text="Bank $5 million",
                      why="Enough for a deposit on your first aircraft.",
                      go="finance", check=lambda s, g: s["cash"] >= 5_000_000),
             ]),
        dict(key="metal", title="Metal of your own",
             blurb="An aircraft on your own certificate changes the business: you can wet-lease it out, fly charter, "
                   "and carry the cost of it whether it flies or not.",
             goals=[
                 dict(id="fleet1", text="Lease or buy your first aircraft",
                      why="A lease needs three months' deposit; buying ties up cash but puts an asset on the books.",
                      go="market", check=lambda s, g: len(s["fleet"]) >= 1),
                 dict(id="ownflight", text="Fly a sector on your own aircraft",
                      why="Positioning, charter or ACMI — anything on your own metal.",
                      go="dispatch", check=lambda s, g: any(f.get("aircraft_id") for f in s["flights"])),
                 dict(id="mxplan", text="Put an aircraft through an A-check",
                      why="Checks come due on hours. Plan them or they will interrupt something that matters.",
                      go="fleet", check=lambda s, g: any(a.get("mx_log") for a in s["fleet"])),
                 dict(id="profit", text="Close a month in profit",
                      why="Leases, salaries and maintenance post monthly whether you fly or not.",
                      go="statements", check=lambda s, g: any(m.get("net", 0) > 0 for m in s["month_reports"])),
             ]),
        dict(key="contracts", title="Contracts and clients",
             blurb="Steady work under contract is what turns a company into an operation: an airline paying by "
                   "the block hour, or a broker calling you first.",
             goals=[
                 dict(id="acmi_or_charter", text="Sign an ACMI contract or win a charter trip",
                      why="ACMI pays a guaranteed minimum monthly; charter pays per trip at a price you set.",
                      go="tenders", check=lambda s, g: any(c["status"] == "Active" for c in s["contracts"])
                                                     or any(j["status"] in ("Booked", "Flying", "Completed") for j in s["charter_jobs"])),
                 dict(id="satisfied", text="Finish a contract or trip with the customer satisfied",
                      why="Satisfaction brings extensions and repeat business.",
                      go="contracts", check=lambda s, g: any(j.get("satisfaction", 0) and j["satisfaction"] >= 80 for j in s["charter_jobs"])
                                                       or any(c.get("satisfaction", 0) >= 70 for c in s["contracts"])),
                 dict(id="fleet3", text="Operate three aircraft",
                      why="Three tails means a schedule, and a schedule means conflicts to plan around.",
                      go="fleet", check=lambda s, g: len(s["fleet"]) >= 3),
             ]),
        dict(key="widebody", title="The long haul",
             blurb="Widebody work opens at 55 reputation: long ferries, oceanic crossings and the operators "
                   "who move aircraft between continents.",
             goals=[
                 dict(id="rep55", text="Reach 55 reputation and unlock widebody work",
                      why="Lessors will not hand a 777 to an operator without a record.",
                      go="dashboard", check=lambda s, g: s["company"]["reputation"] >= 55),
                 dict(id="oceanic", text="Fly an oceanic sector",
                      why="Beyond 60 minutes from a diversion airport, with the paperwork that requires.",
                      go="ferry", check=lambda s, g: any(f.get("oceanic") or (f.get("remote_nm") or 0) > 400 for f in s["flights"])),
                 dict(id="wide", text="Operate a widebody",
                      why="Ferry one, crew one, or put one on your own certificate.",
                      go="ferry", check=lambda s, g: any(AIRCRAFT.get(f["type"], {}).get("cat") == "Widebody" for f in s["flights"])),
                 dict(id="equity", text="Build $25 million of equity",
                      why="Cash, aircraft and receivables less what you owe.",
                      go="finance", check=lambda s, g: g.equity() >= 25_000_000),
             ]),
    ]

    def equity(self):
        """Cash plus owned aircraft and lease deposits, less what is owed."""
        fleet_val = sum(a["value"] for a in self.s["fleet"] if a["owned"])
        deposits = sum(a.get("deposit", 0) for a in self.s["fleet"] if not a["owned"])
        loans = sum(l["balance"] for l in self.s["loans"])
        return money(self.s["cash"] + fleet_val + deposits - loans)

    def ferries_done(self):
        """Ferry deliveries, counted from the record rather than a running total, so the
        figure is right even after a job has dropped off the board."""
        n = sum(1 for j in self.s["ferry_board"] if j["status"] == "Completed")
        return max(n, self.s["stats"].get("ferry_done", 0))

    def pairings_done(self):
        n = sum(1 for j in self.s["cargo_board"] if j["status"] == "Completed")
        return max(n, self.s["stats"].get("cargo_done", 0))

    def career_state(self):
        c = self.s.setdefault("career", dict(enabled=False, done={}, seen_chapter=0))
        c.setdefault("done", {})
        return c

    def check_objectives(self):
        """Tick off anything now satisfied. Cheap enough to call after any action."""
        c = self.career_state()
        newly = []
        for ch in self.CHAPTERS:
            for goal in ch["goals"]:
                if goal["id"] in c["done"]:
                    continue
                try:
                    if goal["check"](self.s, self):
                        c["done"][goal["id"]] = self.s["clock"]
                        newly.append((ch, goal))
                except Exception:
                    pass
        for ch, goal in newly:
            self.notice(f"Objective complete: {goal['text']}.")
            done_ids = {g["id"] for g in ch["goals"]}
            if done_ids <= set(c["done"]):
                self.event("company", f"{ch['title']} — chapter complete", ch["blurb"])
                self.notice(f"Chapter complete: {ch['title']}.")
        return newly

    def career_view(self):
        c = self.career_state()
        out, current = [], None
        for ch in self.CHAPTERS:
            goals = [dict(id=g["id"], text=g["text"], why=g["why"], go=g["go"], done=c["done"].get(g["id"]))
                     for g in ch["goals"]]
            complete = all(g["done"] for g in goals)
            out.append(dict(key=ch["key"], title=ch["title"], blurb=ch["blurb"], goals=goals, complete=complete))
            if not complete and current is None:
                current = dict(chapter=ch["title"], **next(g for g in goals if not g["done"]))
        return dict(enabled=c["enabled"], chapters=out, current=current,
                    done=len(c["done"]), total=sum(len(ch["goals"]) for ch in self.CHAPTERS))

    # ================================================================ records
    def pilot_record(self, pid):
        """Everything the company knows about one pilot."""
        p = self.pilot(pid)
        fl = [f for f in self.s["flights"] if pid in (f.get("crew") or [])]
        lands = [f["landing"] for f in fl if f.get("landing") and f["landing"].get("vs")]
        vs = [l["vs"] for l in lands]
        scores = [f["score"] for f in fl if f.get("score") is not None]
        occ = [o for o in self.s["safety"]["occurrences"] if o.get("flight_id") in {f["id"] for f in fl}]
        hours = sum(f["block_min"] for f in fl) / 60
        by_type = {}
        for f in fl:
            t = by_type.setdefault(f["type"], dict(sectors=0, hours=0.0))
            t["sectors"] += 1
            t["hours"] += f["block_min"] / 60
        cur = {fam: dict(zip(("current", "landings"), self.is_current(p, fam))) for fam in p["ratings"]}
        known = [p["name"]] + list(p.get("former_names") or [])
        history = [e for e in self.s["timeline"]
                   if any(n in (e.get("title", "") + e.get("detail", "")) for n in known)]
        return dict(
            pilot=p, sectors=len(fl), hours=round(hours, 1), company_hours=p.get("company_hours", 0),
            total_hours=p["hours"], by_type=by_type, currency=cur,
            avg_score=round(sum(scores) / len(scores)) if scores else None,
            best_score=max(scores) if scores else None, worst_score=min(scores) if scores else None,
            landings=len(vs), avg_vs=round(sum(vs) / len(vs)) if vs else None,
            best_vs=max(vs) if vs else None, worst_vs=min(vs) if vs else None,
            greasers=sum(1 for v in vs if v > -200), firm=sum(1 for v in vs if v < -400),
            occurrences=occ, upgrade=self.upgrade_check(p) if p["rank"] == "FO" else None,
            recent=[dict(id=f["id"], filed=f["filed"], flight_number=f["flight_number"], origin=f["origin"],
                         destination=f["arrival"] or f["destination"], type=f["type"], reg=f["reg"],
                         block_min=f["block_min"], score=f["score"],
                         vs=(f.get("landing") or {}).get("vs")) for f in fl[-25:]][::-1],
            history=history[-12:][::-1],
        )

    def aircraft_record(self, ac_id):
        """The airframe record: what it has flown, earned and cost."""
        a = self.fleet_ac(ac_id)
        fl = [f for f in self.s["flights"] if f.get("aircraft_id") == ac_id]
        income = sum(f.get("income", 0) or 0 for f in fl)
        costs = sum(f.get("costs", 0) or 0 for f in fl)
        scores = [f["score"] for f in fl if f.get("score") is not None]
        vs = [(f.get("landing") or {}).get("vs") for f in fl]
        vs = [v for v in vs if v]
        ledger = [l for l in self.s["ledger"] if l.get("ref") == f"ac{ac_id}" or a["reg"] in (l.get("desc") or "")]
        spend = sum(l["amount"] for l in ledger if l["amount"] < 0)
        ports = {}
        for f in fl:
            ports[f["arrival"] or f["destination"]] = ports.get(f["arrival"] or f["destination"], 0) + 1
        months = {}
        for f in fl:
            months[f["filed"][:7]] = months.get(f["filed"][:7], 0) + f["block_min"] / 60
        return dict(
            aircraft=a, sectors=len(fl), hours_flown=round(sum(f["block_min"] for f in fl) / 60, 1),
            income=money(income), direct_costs=money(costs), other_spend=money(-spend),
            avg_score=round(sum(scores) / len(scores)) if scores else None,
            avg_vs=round(sum(vs) / len(vs)) if vs else None,
            utilisation=[dict(month=k, hours=round(v, 1)) for k, v in sorted(months.items())][-12:],
            ports=sorted(ports.items(), key=lambda kv: -kv[1])[:8],
            mx_log=list(reversed(a.get("mx_log") or []))[:12],
            engines=a["engines"], snags=a["snags"],
            ledger=[dict(date=l["date"], desc=l["desc"], amount=l["amount"], category=l["category"])
                    for l in ledger[-15:]][::-1],
            recent=[dict(id=f["id"], filed=f["filed"], flight_number=f["flight_number"], origin=f["origin"],
                         destination=f["arrival"] or f["destination"], kind=f["kind"], customer=f.get("customer"),
                         block_min=f["block_min"], score=f["score"], income=f.get("income"),
                         vs=(f.get("landing") or {}).get("vs")) for f in fl[-25:]][::-1],
        )

    # ================================================================ area of operations
    def aoc_areas(self):
        """The regions this AOC authorises. A new certificate covers the area it was
        issued in; the rest are amendments to the operations specifications."""
        co = self.s["company"]
        if not co.get("aoc_areas"):
            home = region_of(co["base"]) or "EU"
            co["aoc_areas"] = [home]
        return co["aoc_areas"]

    def area_pending(self):
        return self.s["company"].setdefault("aoc_pending", [])

    def area_allowed(self, *icaos):
        """Is every field on this sector inside the certificate?"""
        areas = set(self.aoc_areas())
        out = []
        for f in icaos:
            r = region_of(f)
            if r and r not in areas:
                out.append((f, r))
        return out

    def area_cost(self, region):
        home = region_of(self.s["company"]["base"]) or "EU"
        near = region in ADJACENT_REGIONS.get(home, []) or any(
            region in ADJACENT_REGIONS.get(a, []) for a in self.aoc_areas())
        band = AREA_APPLICATION["near" if near else "far"]
        return dict(region=region, near=near, **band)

    def apply_area(self, region):
        """Apply to add an area to the operations specifications."""
        if region not in REGIONS:
            raise GameError("Unknown area.")
        if region in self.aoc_areas():
            raise GameError(f"{REGIONS[region]['name']} is already on your certificate.")
        if any(p["region"] == region for p in self.area_pending()):
            raise GameError(f"An application for {REGIONS[region]['name']} is already with the authority.")
        c = self.area_cost(region)
        if self.s["company"]["reputation"] < c["rep"]:
            raise GameError(f"The authority will not consider {REGIONS[region]['name']} below {c['rep']} reputation: "
                            "they want a record before they will extend a certificate that far.")
        if self.s["cash"] < c["fee"]:
            raise GameError(f"The application fee is ${c['fee']:,}.")
        self.post("Regulatory", f"AOC amendment — {REGIONS[region]['name']} area of operations", -c["fee"])
        ready = self.now() + timedelta(days=c["days"])
        self.area_pending().append(dict(region=region, applied=self.s["clock"], ready=iso(ready), fee=c["fee"]))
        self.mail("Civil aviation authority", f"Application received — {REGIONS[region]['name']}",
                  f"Your application to add {REGIONS[region]['name']} to the areas of operation on your air operator "
                  f"certificate has been received. We will review your procedures, crew licensing and maintenance "
                  f"arrangements for the area and expect to respond by {ready:%d %B %Y}.", action="company")
        self.notice(f"Applied to add {REGIONS[region]['name']} to the AOC — ${c['fee']:,}, decision by {ready:%d %b %Y}.")
        self.save()
        return dict(message=f"Application lodged. The authority will respond by {ready:%d %B %Y}.")

    # ---------------------------------------------------------- type ratings on the AOC
    def aoc_types(self):
        """The type ratings listed on the operations specifications.

        An empty list means the certificate carries no type restriction, which is how
        every company issued before 1.8.0 was written — so existing saves are unaffected
        and anyone who would rather fly everything can leave it that way."""
        return self.s["company"].setdefault("aoc_types", [])

    def type_pending(self):
        return self.s["company"].setdefault("aoc_types_pending", [])

    def restricted_by_type(self):
        return bool(self.aoc_types())

    def family_allowed(self, family):
        fams = self.aoc_types()
        return not fams or family in fams

    def type_allowed(self, code):
        ac = AIRCRAFT.get(code)
        return not ac or self.family_allowed(ac["family"])

    def allowed_type_codes(self):
        """Every aircraft code the certificate authorises, cached on the OpSpecs."""
        key = tuple(sorted(self.aoc_types()))
        if getattr(self, "_atc_key", None) != key:
            self._atc_key = key
            self._atc = ({t for t, a in AIRCRAFT.items() if a["family"] in key} if key
                         else set(AIRCRAFT))
        return self._atc

    @staticmethod
    def family_cat(family):
        for a in AIRCRAFT.values():
            if a["family"] == family:
                return a["cat"]
        return "Narrowbody"

    @staticmethod
    def family_mfr(family):
        for a in AIRCRAFT.values():
            if a["family"] == family:
                return a["mfr"]
        return ""

    def type_cost(self, family):
        band = dict(TYPE_APPLICATION.get(self.family_cat(family), TYPE_APPLICATION["Narrowbody"]))
        mfr = self.family_mfr(family)
        same = any(self.family_mfr(f) == mfr for f in self.aoc_types())
        if same:
            band["fee"] = money(band["fee"] * SAME_MFR_DISCOUNT)
            band["days"] = max(14, int(band["days"] * SAME_MFR_DISCOUNT))
        return dict(family=family, cat=self.family_cat(family), mfr=mfr, same_mfr=same, **band)

    def apply_type(self, family):
        """Apply to add a type rating to the operations specifications."""
        fams = {a["family"] for a in AIRCRAFT.values()}
        if family not in fams:
            raise GameError("Unknown type rating.")
        if not self.restricted_by_type():
            raise GameError("Your certificate carries no type restriction, so every type is already approved.")
        if family in self.aoc_types():
            raise GameError(f"{family} is already on your operations specifications.")
        if any(p["family"] == family for p in self.type_pending()):
            raise GameError(f"An application for {family} is already with the authority.")
        c = self.type_cost(family)
        if self.s["company"]["reputation"] < c["rep"]:
            raise GameError(f"The authority will not add {family} below {c['rep']} reputation: an operator asking to "
                            f"put {c['cat'].lower()} aircraft on its certificate needs a record behind it first.")
        if self.s["cash"] < c["fee"]:
            raise GameError(f"The application costs ${c['fee']:,} in manuals, training programme approval and the proving flight.")
        self.post("Regulatory", f"AOC amendment — {family} added to operations specifications", -c["fee"])
        ready = self.now() + timedelta(days=c["days"])
        self.type_pending().append(dict(family=family, applied=self.s["clock"], ready=iso(ready), fee=c["fee"]))
        self.mail("Civil aviation authority", f"Application received — {family} type rating",
                  f"Your application to add the {family} to the types on your air operator certificate has been "
                  f"received. We will review your training programme, maintenance programme and operations manual "
                  f"for the type, and a proving flight will be required. We expect to respond by {ready:%d %B %Y}."
                  + (f" Your existing {c['mfr']} approval shortens the review." if c["same_mfr"] else ""),
                  action="company")
        self.notice(f"Applied to add {family} to the AOC — ${c['fee']:,}, decision by {ready:%d %b %Y}.")
        self.save()
        return dict(message=f"Application lodged. The authority will respond by {ready:%d %B %Y}.")

    def _settle_type_applications(self):
        now = self.now()
        for p in list(self.type_pending()):
            if parse(p["ready"]) <= now:
                self.type_pending().remove(p)
                self.aoc_types().append(p["family"])
                self._atc_key = None
                self.mail("Civil aviation authority", f"Operations specifications amended — {p['family']}",
                          f"The {p['family']} is now listed on your air operator certificate. Proving flight "
                          "accepted and the training and maintenance programmes approved. Work on the type will "
                          "begin to appear on your boards.", action="company", pin=True)
                self.notice(f"AOC now covers the {p['family']}.")
                self.refresh_hire_pool()

    def _settle_area_applications(self):
        now = self.now()
        for p in list(self.area_pending()):
            if parse(p["ready"]) <= now:
                self.area_pending().remove(p)
                self.aoc_areas().append(p["region"])
                name = REGIONS[p["region"]]["name"]
                self.mail("Civil aviation authority", f"Operations specifications amended — {name}",
                          f"Your air operator certificate now authorises operations in {name}. "
                          "Work in the area will begin to appear on your boards.", action="company", pin=True)
                self.notice(f"AOC now covers {name}.")

    # ================================================================ developer tools
    def dev(self, action, value=None):
        """Testing shortcuts. Off unless switched on in Settings, and the save records
        that they were used so a company's figures can be taken at face value or not."""
        if not self.s["company"].get("dev_tools"):
            raise GameError("Developer tools are switched off. Settings → Developer tools.")
        self.s["company"]["dev_used"] = True
        out = ""
        if action == "reputation":
            v = max(0.0, min(100.0, float(value)))
            self.s["company"]["reputation"] = v
            out = f"Reputation set to {v:.0f}." + (" Widebody work is open." if v >= 55 else "")
        elif action == "cash":
            v = float(value)
            delta = v - self.s["cash"]
            self.post("Developer", "Cash adjusted with developer tools", delta)
            out = f"Cash set to ${v:,.0f}."
        elif action == "advance":
            self.advance(days=int(value))
            out = f"Clock advanced {int(value)} day(s)."
        elif action == "refresh":
            self.refresh_market(full=bool(value))
            self.refresh_charter()
            out = "Market and charter board refreshed."
        elif action == "job":
            kind = str(value)
            if kind == "ferry":
                j = self._ferry_job()
                if not j:
                    raise GameError("Could not compose a ferry job your certificate covers.")
                self.s["ferry_board"].insert(0, j)
                out = f"Ferry job #{j['id']} added: {j['name']} {j['origin']}–{j['destination']}."
            elif kind == "cargo":
                j = self._cargo_pairing()
                if not j:
                    raise GameError("No cargo carrier hires crews for the types on your certificate.")
                self.s["cargo_board"].insert(0, j)
                out = f"Cargo pairing #{j['id']} added for {j['carrier']}."
            elif kind == "charter":
                q = self._charter_enquiry()
                if not q:
                    raise GameError("Could not compose a charter enquiry.")
                self.s["charter_board"].insert(0, q)
                out = f"Charter enquiry added: {q['trip_label']} for {q['client']}, market ${q['market']:,.0f}."
            elif kind == "acmi":
                t = self._tender()
                if not t:
                    raise GameError("No airline is tendering for capacity on the types on your certificate.")
                self.s["acmi_tenders"].insert(0, t)
                out = f"ACMI tender added: {t['customer']} {t['type']}."
            else:
                raise GameError("Unknown job type.")
        elif action == "crew":
            n = int(value or 2)
            fams = sorted({AIRCRAFT[a["type"]]["family"] for a in self.s["fleet"]}) or ["B737"]
            for i in range(n):
                c = self._candidate()
                c.update(rank="CPT" if i % 2 == 0 else "FO", ratings=[self.rng.choice(fams)])
                self.s["hire_pool"].append(c)
                self.hire(c["id"])
            out = f"Hired {n} pilot(s) rated on {', '.join(fams)}."
        elif action == "current":
            for p in self.s["pilots"]:
                for f in p["ratings"]:
                    self._grant_recency(p, f)
                p["duty_h"], p["rest_until"] = 0.0, None
                if p["status"] in ("Resting",):
                    p["status"] = "Available"
            out = "All pilots made current and rested."
        elif action == "position":
            reg, where = (value or "").split(":", 1)
            a = next((x for x in self.s["fleet"] if x["reg"] == reg.strip()), None)
            if not a:
                raise GameError(f"No aircraft {reg}.")
            where = where.strip().upper()
            if where not in AIRPORTS:
                raise GameError(f"{where} is not in the airport database.")
            a["location"] = where
            out = f"{a['reg']} moved to {where}."
        else:
            raise GameError("Unknown developer action.")
        self.save()
        return out

    # ================================================================ schedule
    def schedule(self, days=14):
        """Everything committed over the coming fortnight, by aircraft, with the clashes
        called out. This is the planning view: what each tail is doing and what will not fit."""
        now = self.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=days)
        rows, unassigned, conflicts, later = [], [], [], []

        def span(a_start, hours):
            return iso(a_start), iso(a_start + timedelta(hours=max(0.5, hours)))

        for a in self.s["fleet"]:
            items = []

            # maintenance, whether under way or falling due
            if a.get("mx_until") and parse(a["mx_until"]) > now:
                items.append(dict(kind="maintenance", label=f"{a['status']}", start=iso(now),
                                  end=a["mx_until"], origin=a["location"], destination=a["location"],
                                  note="in the shop", firm=True))
            fh_left = A_CHECK_FH - a["fh_since_a"]
            if fh_left < 40:
                items.append(dict(kind="due", label=f"A-check due in {int(fh_left)} FH", start=iso(now + timedelta(days=1)),
                                  end=iso(now + timedelta(days=1, hours=8)), origin=a["location"],
                                  destination=a["location"], note="two days in the hangar", firm=False))
            if a.get("c_check_due") and start < parse(a["c_check_due"]) < end:
                items.append(dict(kind="due", label="C-check due", start=a["c_check_due"],
                                  end=iso(parse(a["c_check_due"]) + timedelta(days=14)), origin=a["location"],
                                  destination=a["location"], note="fourteen days out of service", firm=False))
            if a.get("lease_end") and start < parse(a["lease_end"]) < end:
                items.append(dict(kind="due", label="Lease ends", start=a["lease_end"],
                                  end=iso(parse(a["lease_end"]) + timedelta(hours=6)), origin=a["location"],
                                  destination=a["location"], note="redelivery due", firm=True))

            # sectors the crews are flying right now: the aeroplane is genuinely away
            for f in self.s["dispatched"]:
                cf = f.get("crew_flight")
                if f.get("aircraft_id") != a["id"] or f.get("status") != "En route" or not cf:
                    continue
                items.append(dict(kind="active", label=f"{f['flight_number']} {f['origin']}–{f['destination']}",
                                  start=cf["off"], end=cf["eta"], origin=f["origin"], destination=f["destination"],
                                  note=f"airborne with the crew, ETA {parse(cf['eta']):%H:%M}Z", firm=True))

            # the flight on the go
            f = self.s.get("active_flight")
            if f and f.get("aircraft_id") == a["id"] and f.get("status") != "En route":
                items.append(dict(kind="active", label=f"{f['flight_number']} {f['origin']}–{f['destination']}",
                                  **dict(zip(("start", "end"), span(now, (f.get("ete_min") or 90) / 60))),
                                  origin=f["origin"], destination=f["destination"], note="dispatched", firm=True))

            # charter trips
            for j in self.s["charter_jobs"]:
                if j["aircraft_id"] != a["id"] or j["status"] not in ("Booked", "Flying"):
                    continue
                dep = parse(j["depart"])
                legs = self.charter_legs(j)
                hours = sum(gc_nm(l["origin"], l["destination"]) for l in legs) / AIRCRAFT[a["type"]]["cruise"] + 0.5 * len(legs)
                item = dict(kind="charter", label=f"#{j['id']} {j['client']}", start=iso(dep),
                            end=iso(dep + timedelta(hours=hours + 24 * (j.get("nights") or 0))),
                            origin=legs[0]["origin"] if legs else j["origin"], destination=j["destination"],
                            note=f"{len(legs)} sector(s) to fly, from {legs[0]['origin'] if legs else j['origin']}",
                            firm=True, job=j["id"], reg=a["reg"])
                if dep > end:
                    later.append(item)
                else:
                    items.append(item)
                client = self.client_legs(j)
                first = client[j.get("done", 0)] if j.get("done", 0) < len(client) else None
                if first and a["location"] != first["origin"]:
                    reposition_nm = gc_nm(a["location"], first["origin"])
                    hours = reposition_nm / AIRCRAFT[a["type"]]["cruise"] + 1.0
                    slack = (dep - now).total_seconds() / 3600
                    conflicts.append(dict(
                        reg=a["reg"], job=j["id"], severity="bad" if slack < hours else "warn",
                        text=(f"Charter #{j['id']} lifts from {first['origin']} at {j['depart'][11:16]}Z on "
                              f"{j['depart'][:10]}; {a['reg']} is at {a['location']}, "
                              f"{int(reposition_nm):,} nm away — about {hours:.1f} h of positioning"
                              + (f", and only {slack:.0f} h remain." if slack < hours else "."))))
                if j.get("nights") and any(i["kind"] == "maintenance" for i in items):
                    conflicts.append(dict(reg=a["reg"], severity="bad",
                                          text=f"Charter #{j['id']} overlaps maintenance on {a['reg']}."))

            # ACMI rotations
            for c in self.s["contracts"]:
                if c.get("aircraft_id") != a["id"] or c["status"] != "Active":
                    continue
                items.append(dict(kind="acmi", label=f"{c['customer']} ACMI", start=iso(max(start, parse(c['start']))),
                                  end=c["end"], origin=c["hub"], destination=c["hub"],
                                  note=f"{c['rate']:,}/BH, minimum {c['min_hours']} h a month", firm=True))
            rows.append(dict(reg=a["reg"], type=a["type"], name=a["name"], location=a["location"],
                             status=a["status"], items=sorted(items, key=lambda x: x["start"])))

        # work you have taken on that has no aircraft of yours attached
        for j in self.s["ferry_board"]:
            if j["status"] != "Accepted":
                continue
            unassigned.append(dict(kind="ferry", label=f"Ferry #{j['id']} {j['name']}", start=iso(now),
                                   end=j["deadline"], origin=j.get("current") or j["origin"],
                                   destination=j["destination"], note=f"{j['reg']}, client's aircraft",
                                   deadline=j["deadline"], id=j["id"]))
            if parse(j["deadline"]) < now + timedelta(days=2):
                conflicts.append(dict(reg=j["reg"], severity="bad",
                                      text=f"Ferry #{j['id']} to {j['destination']} is due by {j['deadline'][:10]}."))
        for c in self.s["cargo_board"]:
            if c["status"] != "Accepted":
                continue
            left = [l for l in c["legs"] if not l.get("flown")]
            unassigned.append(dict(kind="cargo", label=f"{c['carrier']} pairing #{c['id']}", start=iso(now),
                                   end=c["deadline"], origin=c.get("current") or c["base"],
                                   destination=left[-1]["destination"] if left else c["base"],
                                   note=f"{len(left)} of {len(c['legs'])} sectors left, {c['reg']}",
                                   deadline=c["deadline"], id=c["id"]))
            if parse(c["deadline"]) < now + timedelta(days=2) and left:
                conflicts.append(dict(reg=c["reg"], severity="bad",
                                      text=f"{c['carrier']} pairing #{c['id']} has {len(left)} sector(s) left "
                                           f"and is due by {c['deadline'][:10]}."))

        # crew: who is off the line, and whether anyone is left
        crew = []
        for p in self.s["pilots"]:
            until = p.get("training_until") if p["status"] == "Training" else p.get("rest_until")
            if p["status"] != "Available" or (until and parse(until) > now):
                crew.append(dict(name=p["name"], rank=p["rank"], status=p["status"], until=until,
                                 ratings=p["ratings"]))
        for row in rows:
            fam = AIRCRAFT[row["type"]]["family"]
            able = [p for p in self.s["pilots"] if fam in p["ratings"] and p["status"] == "Available"]
            if row["items"] and len([p for p in able if p["rank"] == "CPT"]) < 1:
                conflicts.append(dict(reg=row["reg"], severity="bad",
                                      text=f"No available captain rated on {fam} for {row['reg']}."))
            elif row["items"] and len(able) < 2:
                conflicts.append(dict(reg=row["reg"], severity="warn",
                                      text=f"Only {len(able)} pilot(s) rated on {fam} are available for {row['reg']}."))

        # two firm commitments on one tail at the same time
        for row in rows:
            firm = [i for i in row["items"] if i.get("firm")]
            for x, y in zip(firm, firm[1:]):
                if parse(y["start"]) < parse(x["end"]):
                    conflicts.append(dict(reg=row["reg"], severity="bad",
                                          text=f"{row['reg']}: {x['label']} overlaps {y['label']}."))
        return dict(start=iso(start), days=days, rows=rows, unassigned=unassigned, later=sorted(later, key=lambda x: x["start"]),
                    conflicts=conflicts, crew=crew, clock=self.s["clock"])

    # ================================================================ charter
    # cabin size as a charter client judges it; airliners sit above every business jet
    CABIN_CLASS = {"Turboprop": 1, "Light jet": 2, "Midsize jet": 3, "Super-midsize jet": 4,
                   "Heavy jet": 5, "Regional": 5, "Narrowbody": 6, "Widebody": 7}

    def _group_enquiry(self):
        """A whole airliner hired by one party: the holiday series, the team, the troops.
        Priced by the hour for the aircraft, not by the seat."""
        own = [a for a in self.s["fleet"] if a["status"] == "Available"
               and AIRCRAFT[a["type"]]["seats"] >= 45 and not AIRCRAFT[a["type"]].get("charter")]
        pool = [t for t, a in AIRCRAFT.items() if a["seats"] >= 45 and not a.get("charter")]
        types = sorted({a["type"] for a in own}) or pool
        if self.restricted_by_type():
            ok = self.allowed_type_codes()
            types = [t for t in types if t in ok] or [t for t in pool if t in ok]
            if not types:
                return None
        code = self.rng.choice(types)
        ac = AIRCRAFT[code]
        client = self.rng.choice([c for c in GROUP_CLIENTS if c["min_pax"] <= ac["seats"]] or GROUP_CLIENTS[:1])
        base = (own and self.rng.choice(own)["location"]) or self.s["company"]["base"]

        trip = self.rng.choices(CHARTER_TRIPS, weights=[t["weight"] for t in CHARTER_TRIPS])[0]
        broker = self.rng.choices(BROKERS, weights=[b["weight"] for b in BROKERS])[0]
        # a broker does not offer a 737 charter out of London City: the fields have to
        # take the aeroplane
        need_rwy = perf.PERF.get(code, {}).get("tofl", 6000) * 0.85
        def usable(icao):
            have = perf.longest(icao) or 0
            return have >= need_rwy
        near = [h for h in sorted(CHARTER_HUBS + MAJOR[:300], key=lambda h: gc_nm(base, h))[:80]
                if usable(h) and self.in_area(h)][:40]
        if not near:
            return None
        o = self.rng.choice(near)
        pool_d = [h for h in self.area_majors()[:600]
                  if h != o and 250 < gc_nm(o, h) < ac["range_nm"] * 0.85 and usable(h)]
        if not pool_d:
            return None
        d = self.rng.choice(pool_d)
        dist = gc_nm(o, d)
        pax = self.rng.randint(client["min_pax"], ac["seats"])
        block_h = dist / ac["cruise"] + 0.6
        hourly = GROUP_HOURLY[ac["cat"]]
        lead_days = self.rng.randint(1, 3) if trip.get("urgent") else self.rng.randint(5, 40)
        surge = 1.0 + (0.22 if trip.get("urgent") else 0)
        # hours flown for the client, plus an allowance for positioning the aircraft in
        # and home again, which on a group charter the customer effectively pays for
        sectors_paid = block_h * (1.85 if trip.get("same_day") else 1.0)
        # charter is quoted against a minimum block time, as it is in the trade: nobody
        # rolls an airliner out of the hangar for forty minutes' pay
        min_hours = {"Turboprop": 1.5, "Regional": 2.0, "Narrowbody": 2.5, "Widebody": 3.0}[ac["cat"]]
        sectors_paid = max(sectors_paid, min_hours)
        market = (hourly * sectors_paid * 1.12 + hourly * 0.35) * client["price"] * surge \
            * self.rng.uniform(0.95, 1.07)
        depart = self.now() + timedelta(days=lead_days, hours=self.rng.randint(5, 20))
        attendants = max(1, -(-pax // 50))
        needs = dict(seats=pax, cabin=1, range_nm=int(dist), attendant=True, attendants=attendants,
                     customs=AIRPORTS[o]["country"] != AIRPORTS[d]["country"],
                     short_field=client["kind"] == "Mining rotation", curfew=False, wifi=False,
                     baggage=True, code=aerodrome_code(code))
        return dict(id=self.nid("chq"), group=True, broker=broker["name"], broker_note=broker["note"],
                    fussy=broker["fussy"], client=client["kind"], story=client["story"],
                    cares=client["cares"], tolerance=client["tolerance"], trip=trip["key"],
                    trip_label=trip["label"], trip_desc=trip["desc"], event=None,
                    extra="; ".join(client["needs"]), needs=needs, type=code, name=ac["name"],
                    family=ac["family"], cat=ac["cat"], code_letter=aerodrome_code(code),
                    origin=o, destination=d, stops=[], distance=int(dist),
                    block_h=round(block_h, 1), pax=pax, same_day=bool(trip.get("same_day")),
                    nights=trip.get("days", 0), urgent=bool(trip.get("urgent")),
                    market=money(market), depart=iso(depart), lead_days=lead_days,
                    expires=iso(self.now() + timedelta(days=max(1, min(6, lead_days - 1)))),
                    status="Open", quoted=None)

    def _charter_enquiry(self):
        """A broker asks what you would charge. Every enquiry has a shape, a client and
        requirements the aircraft has to meet."""
        own = [a for a in self.s["fleet"] if AIRCRAFT[a["type"]].get("charter")]
        types = sorted({a["type"] for a in own}) or [t for t, a in AIRCRAFT.items() if a.get("charter")]
        if self.restricted_by_type():
            ok = self.allowed_type_codes()
            types = [t for t in types if t in ok] or [t for t in ok if AIRCRAFT[t].get("charter")]
            if not types:
                return None
        code = self.rng.choice(types)
        ac = AIRCRAFT[code]
        base = (own and self.rng.choice(own)["location"]) or self.s["company"]["base"]

        trip = self.rng.choices(CHARTER_TRIPS, weights=[t["weight"] for t in CHARTER_TRIPS])[0]
        broker = self.rng.choices(BROKERS, weights=[b["weight"] for b in BROKERS])[0]
        client = self.rng.choice(CHARTER_CLIENTS)
        req = self.rng.choice(CHARTER_EXTRAS)

        # where it goes: near the aircraft, unless the trip is an event or long range
        near = sorted(CHARTER_HUBS, key=lambda h: gc_nm(base, h))[:10]
        event = None
        if trip.get("event"):
            event, fields = self.rng.choice(CHARTER_EVENTS)
            o = self.rng.choice(near)
            d = self.rng.choice([f for f in fields if f in AIRPORTS] or near)
        elif trip["key"] == "long_range":
            o = self.rng.choice(near)
            far = [h for h in CHARTER_HUBS if 2200 < gc_nm(o, h) < ac["range_nm"] * 0.9 and self.in_area(h)]
            if not far:
                return None
            d = self.rng.choice(far)
        else:
            o = self.rng.choice(near)
            pool = [h for h in CHARTER_HUBS + self.area_majors()[:500]
                    if h != o and 120 < gc_nm(o, h) < ac["range_nm"] * 0.85 and self.in_area(h)]
            if not pool:
                return None
            d = self.rng.choice(pool)
        if req["need"] == "short_field":
            alt = [f for f in SHORT_FIELDS if f in AIRPORTS and f != o and gc_nm(o, f) < ac["range_nm"] * 0.85]
            if alt:
                d = self.rng.choice(alt)

        dist = gc_nm(o, d)
        stops = []
        for _ in range(trip.get("stops", 0)):
            last = stops[-1] if stops else d
            nxt = [h for h in CHARTER_HUBS if h not in (o, d, *stops) and 120 < gc_nm(last, h) < ac["range_nm"] * 0.8]
            if nxt:
                stops.append(self.rng.choice(nxt))

        # a group charter needs a cabin that can take one; never ask for more seats
        # than the aircraft has
        cap = max(2, ac["seats"] - 1)
        pax_min = min({"group": 8}.get(trip["key"], 1), cap)
        pax = self.rng.randint(max(2, pax_min), cap)
        if trip["key"] == "group":
            pax = max(pax, min(cap, 8))
        block_h = (dist + sum(gc_nm(a, b) for a, b in zip([d] + stops, stops))) / ac["cruise"] + 0.4 * (1 + len(stops))

        hourly = {"Turboprop": 2400, "Light jet": 3300, "Midsize jet": 4200,
                  "Super-midsize jet": 5600, "Heavy jet": 9500}[ac["cat"]]
        lead_days = self.rng.randint(1, 3) if trip.get("urgent") else self.rng.randint(3, 21)
        surge = 1.0 + (0.18 if trip.get("urgent") else 0) + (0.25 if event else 0)
        market = (hourly * (block_h * 1.35 + 0.6) * trip["mult"] * client["price"] * req["mult"] * surge
                  * self.rng.uniform(0.94, 1.08))
        depart = self.now() + timedelta(days=lead_days, hours=self.rng.randint(6, 19))

        needs = dict(seats=pax + 1, cabin=self.CABIN_CLASS[ac["cat"]], range_nm=int(dist),
                     attendant=req["need"] == "attendant" or pax >= 8 or block_h > 5,
                     customs=req["need"] == "customs" or AIRPORTS[o]["country"] != AIRPORTS[d]["country"],
                     short_field=req["need"] == "short_field", curfew=req["need"] == "curfew",
                     wifi=req["need"] == "wifi", baggage=req["need"] == "baggage")
        return dict(id=self.nid("chq"), broker=broker["name"], broker_note=broker["note"], fussy=broker["fussy"],
                    client=client["kind"], story=client["story"], cares=client["cares"], tolerance=client["tolerance"],
                    trip=trip["key"], trip_label=trip["label"], trip_desc=trip["desc"], event=event,
                    extra=req["text"], needs=needs, type=code, name=ac["name"], family=ac["family"],
                    cat=ac["cat"], origin=o, destination=d, stops=stops, distance=int(dist),
                    block_h=round(block_h, 1), pax=pax, same_day=bool(trip.get("same_day")),
                    nights=trip.get("days", 0), urgent=bool(trip.get("urgent")),
                    market=money(market), depart=iso(depart), lead_days=lead_days,
                    expires=iso(self.now() + timedelta(days=max(1, min(4, lead_days - 1)))),
                    status="Open", quoted=None)

    def refresh_charter(self):
        b = self.s["charter_board"]
        b[:] = [q for q in b if q["status"] != "Open" or parse(q["expires"]) > self.now()]
        has_biz = any(AIRCRAFT[a["type"]].get("charter") for a in self.s["fleet"])
        has_pax = any(AIRCRAFT[a["type"]]["seats"] >= 45 and not AIRCRAFT[a["type"]].get("charter")
                      for a in self.s["fleet"])
        want = 4 if has_biz else 2
        want_group = 4 if has_pax else 2
        guard, dry = 0, {"group": 0, "biz": 0}
        while guard < 40:
            guard += 1
            biz_open = len([q for q in b if q["status"] == "Open" and not q.get("group")])
            grp_open = len([q for q in b if q["status"] == "Open" and q.get("group")])
            want_g = grp_open < want_group and dry["group"] < 8
            want_b = biz_open < want and dry["biz"] < 8
            if not want_g and not want_b:
                break
            # a certificate issued only for business aircraft has no airliner to charter
            # out, and the reverse; stop asking for the one that cannot be built
            which = "group" if want_g else "biz"
            q = self._group_enquiry() if which == "group" else self._charter_enquiry()
            if q and self.in_area(q["origin"], q["destination"], *(q.get("stops") or [])):
                b.append(q)
            else:
                dry[which] += 1

    def charter_fit(self, q, a):
        """What stops you bidding, and what the client will hold against you."""
        ac = AIRCRAFT[a["type"]]
        n = q.get("needs") or {}
        blocking, notes = [], []
        if q.get("group") and (ac.get("charter") or ac["seats"] < 45):
            blocking.append(f"{ac['name']} is not an airliner; this is a group charter for {n.get('seats')} passengers.")
        if not q.get("group") and not ac.get("charter"):
            blocking.append(f"{ac['name']} is an airliner; this client wants a business aircraft.")
        if ac["seats"] < n.get("seats", 1):
            blocking.append(f"{ac['name']} seats {ac['seats']}; the trip needs {n['seats']}.")
        legs = [q["origin"], *q.get("stops", []), q["destination"]]
        longest = max((gc_nm(x, y) for x, y in zip(legs, legs[1:])), default=0)
        if longest > ac["range_nm"] * 0.85:
            blocking.append(f"The longest sector is {int(longest):,} nm; the {ac['name']} does about "
                            f"{int(ac['range_nm'] * 0.85):,} nm with reserves.")
        need_rwy = perf.PERF.get(a["type"], {}).get("tofl", 5000)
        for f in legs:
            have = perf.longest(f) or 0
            if have and have < need_rwy * 0.8:
                blocking.append(f"{f} has {have:,} ft; the {ac['name']} wants about {int(need_rwy * 0.8):,} ft.")
                break
        need_cc = n.get("attendants") or (1 if n.get("attendant") else 0)
        have_cc = self.s["staff"].get("cabin_crew", 0)
        if need_cc:
            committed = sum(c.get("cabin_crew", 0) for c in self.s["contracts"] if c["status"] == "Active")
            spare = have_cc - committed
            if spare < need_cc:
                msg = (f"{need_cc} cabin crew are required for {n.get('seats')} passengers and you have "
                       f"{max(0, spare)} free.")
                if q.get("group"):
                    blocking.append(msg + " A group charter cannot be operated without them.")
                else:
                    notes.append(msg)
        if n.get("wifi") and self.CABIN_CLASS[ac["cat"]] < 4:
            notes.append(f"A {ac['cat'].lower()} is unlikely to have the connectivity asked for.")
        if n.get("baggage") and self.CABIN_CLASS[ac["cat"]] < 2:
            notes.append("Baggage volume will be tight.")
        if self.CABIN_CLASS[ac["cat"]] < q.get("needs", {}).get("cabin", 1):
            notes.append("A smaller cabin than the client had in mind.")
        # flight time limitations: a single crew cannot fly an unlimited day
        legs = [q["origin"], *q.get("stops", []), q["destination"]]
        sectors = len(legs) - 1 + (1 if q.get("same_day") else 0)
        if q.get("block_h", 0) > 11 and not q.get("nights"):
            notes.append(f"About {q['block_h']:.1f} block hours in a day: one crew is limited to a 13-hour "
                         f"duty period, so this needs a night stop or a second crew.")
        elif sectors >= 4 and not q.get("nights"):
            notes.append(f"{sectors} sectors in a day will use most of a crew's duty period.")
        return dict(ok=not blocking, blocking=blocking, notes=notes)

    def quote_charter(self, qid, price):
        """Name your price. The broker compares it against the market and decides."""
        q = next((x for x in self.s["charter_board"] if x["id"] == qid), None)
        if not q or q["status"] != "Open":
            raise GameError("That enquiry is no longer open.")
        price = money(max(0, float(price)))
        if price <= 0:
            raise GameError("Quote a price.")
        if q.get("group"):
            own = [a for a in self.s["fleet"]
                   if a["status"] == "Available" and AIRCRAFT[a["type"]]["seats"] >= 45
                   and not AIRCRAFT[a["type"]].get("charter")]
        else:
            own = [a for a in self.s["fleet"] if AIRCRAFT[a["type"]].get("charter") and a["status"] == "Available"]
        fits = [(a, self.charter_fit(q, a)) for a in own]
        usable = [(a, fit) for a, fit in fits if fit["ok"]]
        if not usable:
            why = (fits[0][1]["blocking"][0] if fits else
                   ("You have no airliner available for group work." if q.get("group")
                    else "You have no business aircraft available."))
            raise GameError(f"No aircraft in your fleet can fly this trip. {why}")
        # the best fit is the smallest cabin that still meets the brief
        usable.sort(key=lambda t: (len(t[1]["notes"]), self.CABIN_CLASS[AIRCRAFT[t[0]["type"]]["cat"]]))
        own = [usable[0][0]]
        fit = usable[0][1]
        rep = self.s["company"]["reputation"]
        ratio = price / max(1.0, q["market"])
        # cheaper wins, reputation and a young cabin help, a fussy broker is harder
        odds = 1 / (1 + math.exp((ratio - 1.0) * 9 * q["fussy"]))
        odds *= 0.75 + rep / 200
        age = self.now().year - min(a["year"] for a in own)
        odds *= 1.12 if age < 6 else 1.0 if age < 15 else 0.88
        odds *= max(0.55, 1 - 0.12 * len(fit["notes"]))          # every shortcoming costs you
        if q.get("urgent"):
            odds *= 1.15                                          # fewer operators can cover it
        odds = max(0.02, min(0.96, odds))
        q["quoted"] = price
        q["odds"] = round(odds, 2)
        if self.rng.random() < odds:
            q["status"] = "Won"
            job = dict(id=self.nid("chj"), enquiry=q["id"], broker=q["broker"], client=q["client"], story=q["story"],
                       extra=q["extra"], type=q["type"], name=q["name"], family=q["family"],
                       origin=q["origin"], destination=q["destination"], stops=q.get("stops", []),
                       distance=q["distance"], pax=q["pax"], trip_label=q.get("trip_label"),
                       cares=q.get("cares"), tolerance=q.get("tolerance", 1.0), needs=q.get("needs"),
                       fit_notes=fit["notes"], nights=q.get("nights", 0),
                       fee=price, depart=q["depart"], same_day=q["same_day"], status="Booked",
                       aircraft_id=own[0]["id"], reg=own[0]["reg"], legs=[], flown=[], satisfaction=None)
            job["done"] = 0
            self.client_legs(job)                     # fix the client's sectors now
            self.s["charter_jobs"].append(job)
            self.mail(q["broker"], f"Trip confirmed — {q['origin']} to {q['destination']}",
                      f"Your quote of ${price:,.0f} is accepted for {q['client'].lower()}, {q['pax']} passengers, "
                      f"departing {q['depart'][:10]} at {q['depart'][11:16]}Z. {q['story'].capitalize()}; {q['extra']}. "
                      f"Position the aircraft to {q['origin']} in time.", action="charter", pin=True)
            self.notice(f"Charter won: {q['origin']}–{q['destination']} for {q['client'].lower()}, ${price:,.0f}.")
            self.save()
            return dict(won=True, odds=odds, job=job)
        q["status"] = "Lost"
        q["placed_at"] = money(q["market"] * self.rng.uniform(0.88, 1.02))
        q["placed_with"] = self.rng.choice(CHARTER_COMPETITORS)
        self.mail(q["broker"], f"Not this time — {q['origin']} to {q['destination']}",
                  f"Thank you for quoting. The trip went to {q['placed_with']} at about ${q['placed_at']:,.0f}."
                  + (" " + fit["notes"][0] if fit["notes"] else ""), action="charter")
        self.save()
        return dict(won=False, odds=odds, placed_at=q["placed_at"])

    def _offer_empty_leg(self, job, where):
        """The aircraft is away from base; someone may want the leg home at a discount."""
        base = self.s["company"]["base"]
        if where == base or self.rng.random() > 0.45:
            return
        dist = gc_nm(where, base)
        if dist < 150:
            return
        price = money(job["fee"] * self.rng.uniform(0.22, 0.45) * min(1.4, dist / max(120, job["distance"])))
        self.s["charter_board"].append(dict(
            id=self.nid("chq"), broker="Empty leg listing", broker_note="someone taking your positioning leg at a discount",
            fussy=0.7, client="Empty leg buyer", story=f"a passenger willing to take your empty leg back to {base}",
            cares=dict(punctual=0.35, comfort=0.45, cabin=0.20), tolerance=1.3, trip="empty_leg",
            trip_label="Empty leg", trip_desc="Your aircraft is going home anyway; this pays for part of it.",
            event=None, extra="flexible timing, hand luggage only",
            needs=dict(seats=3, cabin=1, range_nm=int(dist), attendant=False, customs=False,
                       short_field=False, curfew=False, wifi=False, baggage=False),
            type=job["type"], name=job["name"], family=job["family"], cat=AIRCRAFT[job["type"]]["cat"],
            origin=where, destination=base, stops=[], distance=int(dist),
            block_h=round(dist / AIRCRAFT[job["type"]]["cruise"] + 0.4, 1), pax=self.rng.randint(1, 3),
            same_day=False, nights=0, urgent=True, market=price,
            depart=iso(self.now() + timedelta(days=self.rng.randint(1, 3), hours=9)), lead_days=2,
            expires=iso(self.now() + timedelta(days=2)), status="Open", quoted=None))
        self.mail("Empty leg desk", f"Empty leg enquiry — {where} to {base}",
                  f"Your {job['name']} is at {where} with nothing to do. A passenger has asked about the leg home; "
                  f"quote it and you recover part of the positioning.", action="charter")

    def client_legs(self, job):
        """The sectors the client is paying for. Fixed when the trip is booked."""
        if not job.get("client_legs"):
            route = [job["origin"], *job.get("stops", []), job["destination"]]
            legs = [dict(origin=a, destination=b, paid=True, note=f"{job['pax']} passengers")
                    for a, b in zip(route, route[1:])]
            if job.get("same_day"):
                legs.append(dict(origin=route[-1], destination=route[0], paid=True,
                                 note="Return sector" + (f" after {job['nights']} night(s)" if job.get("nights")
                                                         else " the same day")))
            job["client_legs"] = legs
        return job["client_legs"]

    def charter_legs(self, job):
        """What is left to fly: getting to the client from wherever the aircraft is now,
        then the client's remaining sectors. Recomputed every time, so moving the aircraft
        for other work never strands a trip."""
        client = self.client_legs(job)
        flown = int(job.get("done", 0))
        remaining = client[flown:]
        a = next((x for x in self.s["fleet"] if x["id"] == job["aircraft_id"]), None)
        here = (a and a["location"]) or self.s["company"]["base"]
        legs = []
        if remaining and here != remaining[0]["origin"]:
            legs.append(dict(seq=1, origin=here, destination=remaining[0]["origin"], paid=False,
                             note="Positioning empty to the client"))
        for i, l in enumerate(remaining):
            legs.append(dict(seq=len(legs) + 1, index=flown + i, **l))
        return legs

    def _plan_charter_legs(self, job, here):
        """A charter is a shape: position empty, fly the client through their itinerary,
        and on a same-day or overnight trip bring them home again."""
        legs = []
        route = [job["origin"], *job.get("stops", []), job["destination"]]
        if here != route[0]:
            legs.append(dict(seq=1, origin=here, destination=route[0], paid=False,
                             note="Positioning empty to the client"))
        for a, b in zip(route, route[1:]):
            legs.append(dict(seq=len(legs) + 1, origin=a, destination=b, paid=True,
                             note=f"{job['pax']} passengers"))
        if job.get("same_day"):
            legs.append(dict(seq=len(legs) + 1, origin=route[-1], destination=route[0], paid=True,
                             note="Return sector" + (" the same day" if not job.get("nights") else
                                                     f" after {job['nights']} night(s)")))
        return legs

    def _plan_charter_legs_old(self, job, here):
        legs = []
        if here != job["origin"]:
            legs.append(dict(seq=1, origin=here, destination=job["origin"], paid=False, note="Positioning to the client"))
        legs.append(dict(seq=len(legs) + 1, origin=job["origin"], destination=job["destination"], paid=True,
                         note=f"{job['pax']} passengers"))
        if job["same_day"]:
            legs.append(dict(seq=len(legs) + 1, origin=job["destination"], destination=job["origin"], paid=True,
                             note="Return sector, same day"))
        return legs

    # ================================================================ ferry board
    @staticmethod
    def _closest(icaos, near):
        """The site an operator would actually use out of a provider's network."""
        known = [i for i in icaos if i in AIRPORTS]
        return min(known, key=lambda i: gc_nm(near, i)) if known else (icaos[0] if icaos else near)

    def _nearest_site(self, options, near, key, prefer_nm=2600, take=4):
        """Pick a maintenance or storage site the operator would plausibly use:
        the closest few to its base, chosen at random among them, and inside the
        areas the certificate covers."""
        def dist(o):
            ds = [gc_nm(near, i) for i in key(o) if i in AIRPORTS]
            return min(ds) if ds else 99999
        allowed = [o for o in options if any(self.in_area(i) for i in key(o))]
        options = allowed or options
        ranked = sorted(((dist(o), n, o) for n, o in enumerate(options)))   # measured once
        close = [o for dn, _n, o in ranked if dn <= prefer_nm]
        if close:
            return self.rng.choice(close[:take])
        return ranked[0][2]                     # nothing nearby: the closest there is

    def _plausible_year(self, code, kind):
        """A build year the type could actually have."""
        yr = self.now().year
        lo, hi = build_year_range(code, yr)
        if kind == "New delivery":
            return min(hi, yr)
        return self.rng.randint(lo, max(lo, min(hi, yr - 1)))

    def in_area(self, *icaos):
        allowed = self._allowed_regions()
        for f in icaos:
            if not f:
                continue
            r = REGION_OF_COUNTRY.get((AIRPORTS.get(f) or {}).get("country"))
            if r and r not in allowed:
                return False
        return True

    def _allowed_regions(self):
        """Cached so the board generators can test thousands of fields cheaply."""
        areas = tuple(self.aoc_areas())
        if getattr(self, "_areas_key", None) != areas:
            self._areas_key = areas
            self._areas_set = set(areas)
            self._area_fields = None
        return self._areas_set

    def area_fields(self):
        """Every airport the certificate covers, for picking from directly rather than
        generating work and throwing it away."""
        self._allowed_regions()
        if getattr(self, "_area_fields", None) is None:
            self._area_fields = [i for i, a in AIRPORTS.items()
                                 if REGION_OF_COUNTRY.get(a["country"]) in self._areas_set]
        return self._area_fields

    def area_majors(self):
        if getattr(self, "_area_majors", None) is None or self._area_majors_key != self._areas_key:
            self._area_majors_key = self._areas_key
            self._area_majors = [i for i in MAJOR if self.in_area(i)]
        return self._area_majors

    def _area_operators(self, cargo):
        """Operators based inside the certificate, cached: picking the client first and
        the aircraft second means the job is in area by construction rather than by
        generating work and throwing most of it away."""
        key = (tuple(self.aoc_areas()), tuple(sorted(self.aoc_types())), bool(cargo))
        cache = getattr(self, "_areaop_cache", None)
        if cache is None:
            cache = self._areaop_cache = {}
        if key not in cache:
            pool = [o for o in OPERATORS if (o in CARGO_OPERATORS) == bool(cargo)]
            pool = [o for o in pool if self.in_area(OPERATOR_BASES.get(o))] or pool
            if self.restricted_by_type():
                # the client has to own something you are approved to fly, or the job
                # could only be built by giving them an aircraft they do not operate
                ok = self.allowed_type_codes()
                pool = [o for o in pool if any(t in ok for t in types_for(o))] or pool
            cache[key] = pool
        return cache[key]

    FERRY_RATE = {"Turboprop": (6000, 9, 900), "Regional": (8000, 12, 1100),
                  "Narrowbody": (12000, 18, 1400), "Widebody": (22000, 32, 1900),
                  "Light jet": (4500, 8, 950), "Midsize jet": (5200, 10, 1050),
                  "Super-midsize jet": (6200, 12, 1200), "Heavy jet": (8000, 15, 1450)}

    def _biz_ferry_job(self, pool, simple=False):
        """A business aircraft to move. Nobody leases a Citation back to GECAS: these are
        owners, management companies and the brokers who sell their aeroplanes, and the
        heavy work goes to the manufacturer's own service centre, not an airline shop."""
        if not pool:
            return None
        code = self.rng.choice(pool)
        ac = AIRCRAFT[code]
        svc = BIZ_SERVICE.get(ac["mfr"]) or dict(name=f"{ac['mfr']} service centre", sites=[])
        shops = [x for x in svc["sites"] if x in AIRPORTS and self.in_area(x)]
        hubs = [h for h in CHARTER_HUBS if h in AIRPORTS and self.in_area(h)]
        if len(hubs) < 6:
            hubs = (hubs + self.area_majors()[:60])[:60]
        if len(hubs) < 2:
            return None
        # a King Air is not going to cross a continent: keep the two ends inside the
        # type's reach, or every attempt is thrown away as infeasible
        reach = ac["range_nm"] * 0.85

        def near_enough(frm, pool_):
            got = [x for x in pool_ if x != frm and 120 < gc_nm(frm, x) < reach]
            return got or [x for x in pool_ if x != frm]
        o = d = client = desc = kind = None
        for _attempt in range(8):
            owner = self.rng.choice(BIZ_CLIENTS)
            broker = self.rng.choice(BIZ_BROKERS)
            home = self.rng.choice(hubs)
            shop = self._closest(shops, home) if shops else None
            kinds = ["Owner reposition", "Pre-purchase inspection", "Sale delivery"]
            if shop:
                kinds += ["Service centre input", "Service centre output", "Service centre input"]
            if not simple:
                kinds += ["Import delivery", "Ferry to storage"]
            kind = self.rng.choice(kinds)
            if kind == "Service centre input":
                if not shop or gc_nm(home, shop) >= reach:
                    continue
                o, d, client = home, shop, owner
                desc = f"Position to {svc['name']} at {shop} for scheduled inspection. Aircraft empty, owner not aboard."
            elif kind == "Service centre output":
                if not shop:
                    continue
                o, d, client = shop, self.rng.choice(near_enough(shop, hubs)), owner
                desc = f"Maintenance released by {svc['name']} at {shop}. Return the aircraft to the management fleet."
            elif kind == "Pre-purchase inspection":
                o, d, client = home, (shop if shop and gc_nm(home, shop) < reach else self.rng.choice(near_enough(home, hubs))), broker
                desc = f"Aircraft under offer. Position for pre-purchase inspection on behalf of {broker}; the buyer's technical representative travels separately."
            elif kind == "Sale delivery":
                o, d, client = home, self.rng.choice(near_enough(home, hubs)), broker
                desc = f"Sale closed. Deliver the aircraft to the new owner's base for {broker}."
            elif kind == "Import delivery":
                o = self.rng.choice(hubs)
                d, client = self.rng.choice(near_enough(o, hubs)), owner
                desc = f"Aircraft imported and placed on a new registry; deliver to {owner}'s management base. Import paperwork travels with the aircraft."
            elif kind == "Ferry to storage":
                stor = self._nearest_site(STORAGE, home, key=lambda x: [x["icao"]])
                o, d, client = home, stor["icao"], owner
                desc = f"Owner withdrawing the aircraft from service; park it at {stor['name']}."
            else:
                o, d, client = home, self.rng.choice(near_enough(home, hubs)), owner
                desc = f"Empty positioning leg for {owner}; the aircraft is needed at the other end for a trip."
            if not o or not d or o == d or not self.in_area(o, d):
                continue
            if gc_nm(o, d) > 120 and self.route_feasible(code, o, d):
                break
        else:
            return None
        return self._ferry_from(code, kind, client, desc, o, d, simple,
                                snag_band={"Service centre output": (0, 1), "Ferry to storage": (0, 1)}.get(kind, (0, 0)))

    def _ferry_job(self, simple=False):
        rep = self.s["company"]["reputation"]
        # client first, then something they fly: a Gulf operator's aircraft starts in the
        # Gulf, so the job lands inside the certificate without being filtered afterwards
        want_cargo = False if simple else self.rng.random() < 0.32
        area_ops = self._area_operators(want_cargo)
        seed_op = self.rng.choice(area_ops)
        fleet = [t for t in types_for(seed_op) if not AIRCRAFT[t].get("charter")]
        if self.restricted_by_type():
            ok = self.allowed_type_codes()
            fleet = [t for t in fleet if t in ok] or [t for t in ok if not AIRCRAFT[t].get("charter")]
            if not fleet:
                # the certificate covers business aircraft only: owners and management
                # companies move those just as airlines move airliners
                return self._biz_ferry_job(sorted(t for t in ok if AIRCRAFT[t].get("charter")), simple)
        elif self.rng.random() < 0.12:
            return self._biz_ferry_job([t for t, a in AIRCRAFT.items() if a.get("charter")], simple)
        if rep < 55 or simple:
            fleet = [t for t in fleet if AIRCRAFT[t]["cat"] != "Widebody"] or fleet
        if simple:
            # short-haul metal, a maintenance movement and no permits to wait for
            fleet = [t for t in fleet if AIRCRAFT[t]["cat"] in ("Turboprop", "Regional", "Narrowbody")] or fleet
        if not fleet:
            fleet = [t for t, a in AIRCRAFT.items() if not a.get("charter")]
        code = self.rng.choice(fleet)
        ac = AIRCRAFT[code]
        o = d = client = desc = kind = None
        for _attempt in range(10):
            kinds = (["MRO input", "MRO output", "Ferry to storage", "Reactivation"] if simple else
                     ["Lease return", "Redelivery", "Ferry to storage", "Reactivation", "MRO input", "MRO output", "Sale delivery"])
            if not simple and not ac.get("out_of_production") and ac["mfr"] in DELIVERY_CENTERS:
                kinds.append("New delivery")
            kind = self.rng.choice(kinds)
            lessor = self.rng.choice(LESSORS)["name"]
            pool = operators_for(code, self._area_operators(ac["cargo"]))   # flies the type, based in area
            pool = [o for o in pool if self.in_area(OPERATOR_BASES.get(o))] or pool
            op, op2 = self.rng.choice(pool), self.rng.choice(pool)
            hub, hub2 = OPERATOR_BASES.get(op, "EGLL"), OPERATOR_BASES.get(op2, "LFPG")
            # Operators use shops and storage fields they can sensibly reach: a US carrier
            # sends an A320 to Aeroman or a North American shop, not to Tel Aviv.
            mro = self._nearest_site(MROS, hub, key=lambda m: m["sites"])
            stor = self._nearest_site(STORAGE, hub, key=lambda x: [x["icao"]])
            if kind == "Lease return":
                o, d, client, desc = hub, self.rng.choice([stor["icao"], self._closest(mro["sites"], hub), hub2]), lessor, f"End of lease with {op}. Return to lessor-nominated location; redelivery conditions apply."
            elif kind == "Redelivery":
                o, d, client, desc = self._closest(mro["sites"], hub2), hub2, lessor, f"Post-redelivery check at {mro['name']} complete. Deliver to new lessee {op2}."
            elif kind == "Ferry to storage":
                o, d, client, desc = hub, stor["icao"], self.rng.choice([op, lessor]), f"Aircraft going into long-term storage at {stor['name']}."
            elif kind == "Reactivation":
                o, d, client, desc = stor["icao"], self.rng.choice([self._closest(mro["sites"], stor["icao"]), hub2]), lessor, f"Reactivated from storage at {stor['name']}; return-to-service checks complete, deferred defects carried."
            elif kind == "MRO input":
                o, d, client, desc = hub, self._closest(mro["sites"], hub), op, f"Position to {mro['name']} for scheduled heavy maintenance."
            elif kind == "MRO output":
                o, d, client, desc = self._closest(mro["sites"], hub), hub, op, f"Heavy check released by {mro['name']}. Return aircraft to operator."
            elif kind == "New delivery":
                o, d, client, desc = self._closest(DELIVERY_CENTERS[ac["mfr"]], hub), hub, op, f"Factory delivery flight from {ac['mfr']} to {op}."
            else:
                o, d, client, desc = hub, hub2, lessor, f"Aircraft sold; deliver to purchaser {op2}."
            # A job has to make sense: the aircraft must actually go somewhere, and the
            # type must be able to get there. If either fails, compose a different job
            # rather than sending it to an airport that has nothing to do with the client.
            if o and d and not self.in_area(o, d):
                continue
            if o != d and gc_nm(o, d) > 120 and self.route_feasible(code, o, d):
                break
        else:
            # nothing coherent after ten tries: a short repositioning for the same client
            near = [x for x in MAJOR if x != o and 200 < gc_nm(o, x) < ac["range_nm"] * 0.7
                    and self.route_feasible(code, o, x)]
            d = self.rng.choice(near[:25]) if near else min((x for x in MAJOR if x != o), key=lambda x: gc_nm(o, x))
            kind, client = "Positioning", client or self.rng.choice(LESSORS)["name"]
            desc = f"Reposition the aircraft to {d} for {client}."
        return self._ferry_from(code, kind, client, desc, o, d, simple)

    def _ferry_from(self, code, kind, client, desc, o, d, simple=False, snag_band=None):
        """Everything a ferry job needs once the client, the aircraft and the two
        ends are settled: the route with its technical stops, the fee, the defects
        and the permits. Airline work and business-aircraft work share all of it."""
        rep = self.s["company"]["reputation"]
        ac = AIRCRAFT[code]
        dist = gc_nm(o, d)
        routing = self.plan_route(code, o, d)
        base, per, day_rate = self.FERRY_RATE[ac["cat"]]
        legs_n = len(routing)
        block_h = dist / ac["cruise"] + 0.55 * legs_n
        crew_days = max(2, round(block_h / 9 + (legs_n - 1) * 0.6))
        fee_parts = [("Mobilisation and handling", base), (f"Sector fee, {int(dist):,} nm", per * dist),
                     (f"Crew day rate, 2 crew x {crew_days} days", 2 * day_rate * crew_days)]
        if legs_n > 1:
            fee_parts.append((f"Technical stops ({legs_n - 1})", 1800 * (legs_n - 1)))
        fee = sum(v for _, v in fee_parts) * (0.85 + rep / 250) * self.rng.uniform(0.9, 1.12)
        stops = dist > ac["range_nm"] * 0.82
        # snags / permit
        nsn = snag_band or {"Reactivation": (1, 3), "MRO output": (0, 2), "Lease return": (0, 2),
                            "Ferry to storage": (0, 1)}.get(kind, (0, 0))
        pool = snags_for(code)
        snags = self.rng.sample(pool, min(self.rng.randint(*nsn), len(pool)))
        permit = "Special flight permit" if any(x.get("max_alt") or x.get("gear_down") or x["code"] == "AC" for x in snags) or kind == "Reactivation" else "Standard CofA"
        oceanic = max_remoteness(o, d) > ETOPS_NM
        etops = (ac["cat"] in ("Widebody", "Narrowbody")) and not any(x["code"] == "ETOPS" for x in snags) and (kind not in ("Reactivation",) or self.rng.random() > 0.5)
        if snags:
            fee *= 1 + 0.06 * len(snags)
            fee_parts.append((f"Permit / defect surcharge ({len(snags)} item(s))", 0))
        if oceanic:
            fee *= 1.1
            fee_parts.append(("Oceanic sector surcharge", 0))
        countries = []
        _prev = o
        for _w in routing:
            for _c in route_countries(_prev, _w):
                if _c not in countries:
                    countries.append(_c)
            _prev = _w
        permits_needed = [c for c in countries if c not in NO_PERMIT]
        if simple:
            # a deliberately straightforward first job: a maintenance movement on a
            # standard certificate of airworthiness, with the overflight clearances
            # already held for the states on the route
            permit, snags, permits_needed = "Standard CofA", [], []
        fee *= self.diff()["fee"]
        days = max(3, int(dist / 1200) + 3 + (2 if permit != "Standard CofA" else 0) + (3 if self.diff()["permit"] > 1 and permits_needed else 0))
        beginner = (permit == "Standard CofA" and not stops and not oceanic and not snags and not permits_needed and dist < 1500
                    and kind not in ("Lease return", "Redelivery", "Sale delivery"))
        return dict(id=self.nid("job"), kind=kind, client=client, type=code, name=ac["name"], reg=self._reg(), origin=o, destination=d, distance=int(dist),
                    fee=money(fee), tech_stops=stops, desc=desc, family=ac["family"], expires=iso(self.now() + timedelta(days=self.rng.randint(3, 10))),
                    window_days=days, status="Open", current=o, legs=[], crew=[], accepted=None, deadline=None,
                    year=self._plausible_year(code, kind),
                    snags=snags, permit=permit, oceanic=oceanic, etops=etops, countries=countries, docs=[], rejected=False, twin=ac["family"] != "B747",
                    beginner=beginner, permits_needed=permits_needed, routing=routing, stops=len(routing) - 1,
                    block_h=round(block_h, 1), crew_days=crew_days,
                    fee_parts=[(n, money(v)) for n, v in fee_parts], fee_scale=round(fee / max(1, sum(v for _, v in fee_parts)), 2))

    BEGINNER_WANTED = 3

    def _ensure_beginner_jobs(self):
        """Keep straightforward work on the board while a company is finding its feet:
        no tech stops, no oceanic sectors, no deferred defects, no permits to wait for,
        and a week to do it in."""
        if self.s["company"]["reputation"] > 58 and self.ferries_done() > 6:
            return
        board = self.s["ferry_board"]
        have = sum(1 for j in board if j["status"] == "Open" and j.get("beginner"))
        guard = 0
        while have < self.BEGINNER_WANTED and guard < 25:
            guard += 1
            j = self._ferry_job(simple=True)
            if j and j.get("beginner") and self.in_area(j["origin"], j["destination"], *(j.get("routing") or [])):
                j["deadline"] = iso(self.now() + timedelta(days=max(7, j.get("window_days", 5))))
                board.insert(0, j)
                have += 1

    def refresh_ferry_board(self, full=False):
        b = self.s["ferry_board"]
        if full:
            b.clear()
        else:
            self.s["ferry_board"] = b = [j for j in b if j["status"] != "Open" or parse(j["expires"]) > self.now()]
        target = 10 + int(self.s["company"]["reputation"] / 20)
        guard, dry = 0, 0
        while sum(1 for j in b if j["status"] == "Open") < target and guard < 200 and dry < 25:
            guard += 1
            j = self._ferry_job()
            # a job you are not certificated to fly is no job at all
            if j and self.in_area(j["origin"], j["destination"], *(j.get("routing") or [])):
                b.append(j)
            else:
                dry += 1
        self._ensure_beginner_jobs()

    def _build_docs(self, j):
        docs = [dict(name="Insurance certificate (hull & liability, ferry endorsement)", days=1, fee=0)]
        if j["permit"] != "Standard CofA":
            docs.append(dict(name="Special flight permit (ferry permit) from state of registry", days=3, fee=2500))
        if j["kind"] in ("Lease return", "Redelivery", "Sale delivery"):
            docs.append(dict(name="Export CofA / deregistration paperwork", days=3, fee=1800))
        for cc in j["countries"]:
            if cc not in NO_PERMIT:
                d, f = PERMIT_COUNTRIES.get(cc, (2, 300))
                d = max(1, round(d * self.diff()["permit"]))
                kind = "Landing permit" if cc == AIRPORTS[j["destination"]]["country"] else "Overflight permit"
                docs.append(dict(name=f"{kind} — {cc}", days=d, fee=f))
        for d in docs:
            d["ready"] = iso(self.now() + timedelta(days=d["days"]))
        return docs

    def _check_flight_crew(self, commander, second, family):
        """A flight needs a commander. The second seat may be another captain or a
        first officer, but two first officers cannot operate together."""
        if commander["id"] == second["id"]:
            raise GameError("The same pilot cannot occupy both seats.")
        for p in (commander, second):
            if p["status"] != "Available":
                raise GameError(f"{p['name']} is not available ({p['status'].lower()}).")
            if family not in p["ratings"]:
                raise GameError(f"{p['name']} is not rated on {family}.")
        if commander["rank"] != "CPT":
            raise GameError(f"{commander['name']} is a first officer and cannot command the flight. "
                            "Assign a captain in the left seat.")
        for p in (commander, second):
            ok, n = self.is_current(p, family)
            if not ok:
                raise GameError(f"{p['name']} is not current on {family}: {n} of {RECENCY_NEEDED} landings in the last "
                                f"{RECENCY_DAYS} days. Book a recency detail from Crew & staff.")
        return True

    def next_waypoint(self, j):
        """The airport the next leg of a ferry job should go to."""
        rt = j.get("routing") or [j["destination"]]
        if j["current"] in rt:
            i = rt.index(j["current"])
            return rt[i + 1] if i + 1 < len(rt) else j["destination"]
        if j["current"] != j["origin"]:
            rt = self.plan_route(j["type"], j["current"], j["destination"])
            j["routing"] = ([x for x in (j.get("routing") or []) if x != j["destination"]] + rt) if False else rt
            j["stops"] = len(rt) - 1
        return (j.get("routing") or [j["destination"]])[0]

    def accept_ferry(self, job_id, captain_id, fo_id):
        j = self.job(job_id)
        if j["status"] != "Open":
            raise GameError("Job is no longer open.")
        cpt, fo = self.pilot(captain_id), self.pilot(fo_id)
        self._check_flight_crew(cpt, fo, j["family"])
        base = self.s["company"]["base"]
        pos = money(2 * (180 + 0.16 * gc_nm(base, j["origin"])))
        j["docs"] = self._build_docs(j)
        fees = sum(d["fee"] for d in j["docs"])
        if self.s["cash"] < pos + fees:
            raise GameError(f"Insufficient funds for crew positioning (${pos:,}) and permit fees (${fees:,}).")
        self.post("Crew positioning", f"Airline tickets {base}→{j['origin']} x2 (job #{j['id']})", -pos, ref=j["id"])
        if fees:
            self.post("Permits", f"Permit and paperwork fees job #{j['id']}", -fees, ref=j["id"])
        for p in (cpt, fo):
            p["status"], p["job_id"], p["location"] = "Ferry", j["id"], j["origin"]
        j["status"], j["crew"], j["accepted"] = "Accepted", [cpt["id"], fo["id"]], self.s["clock"]
        j["deadline"] = iso(self.now() + timedelta(days=j["window_days"]))
        ready = max(parse(d["ready"]) for d in j["docs"])
        self.mail(j["client"], f"Job #{j['id']} confirmed — {j['name']} {j['reg']} {j['origin']}→{j['destination']}",
                  f"Crew positioning booked. Documents in progress: {', '.join(d['name'] for d in j['docs'])}. Paperwork complete by {iso(ready)[:10]}; delivery deadline {j['deadline'][:10]}."
                  + (" Deferred defects on this aircraft impose permit limits — see the ferry board." if j["snags"] else ""), action="ferry", pin=True)
        self.notice(f"Ferry job #{j['id']} accepted: {j['name']} {j['reg']} {j['origin']}→{j['destination']} for {j['client']}. Paperwork complete {iso(ready)[:10]}, deadline {j['deadline'][:10]}.")
        self.save()
        return j

    REGISTRY = {"N": ("United States", "Federal Aviation Administration"), "G-": ("United Kingdom", "Civil Aviation Authority"),
                "D-A": ("Germany", "Luftfahrt-Bundesamt"), "EI-": ("Ireland", "Irish Aviation Authority"), "F-H": ("France", "Direction générale de l'aviation civile"),
                "OE-I": ("Austria", "Austro Control"), "PH-B": ("Netherlands", "Inspectie Leefomgeving en Transport"), "9H-": ("Malta", "Civil Aviation Directorate"),
                "2-": ("Guernsey", "Guernsey Aircraft Registry"), "VP-C": ("Cayman Islands", "Civil Aviation Authority of the Cayman Islands"),
                "M-A": ("Isle of Man", "Isle of Man Aircraft Registry"), "C-F": ("Canada", "Transport Canada"), "OY-": ("Denmark", "Trafikstyrelsen"),
                "SE-R": ("Sweden", "Transportstyrelsen"), "LN-": ("Norway", "Luftfartstilsynet"), "OH-L": ("Finland", "Traficom"), "SP-": ("Poland", "Urząd Lotnictwa Cywilnego"),
                "HB-J": ("Switzerland", "Federal Office of Civil Aviation"), "EC-": ("Spain", "Agencia Estatal de Seguridad Aérea"), "CS-T": ("Portugal", "ANAC"),
                "I-": ("Italy", "ENAC"), "TC-": ("Türkiye", "Directorate General of Civil Aviation"), "A6-": ("United Arab Emirates", "General Civil Aviation Authority"),
                "VT-": ("India", "Directorate General of Civil Aviation"), "VH-": ("Australia", "Civil Aviation Safety Authority"), "ZK-": ("New Zealand", "Civil Aviation Authority"),
                "PR-": ("Brazil", "ANAC"), "LV-": ("Argentina", "ANAC")}

    def _registry(self, reg):
        for pre, v in sorted(self.REGISTRY.items(), key=lambda x: -len(x[0])):
            if reg.startswith(pre):
                return v
        return ("State of registry", "Civil aviation authority")

    def document(self, job_id, index):
        """Render a viewable facsimile of one of a ferry job's documents."""
        j = self.job(job_id)
        docs = j.get("docs") or []
        if index < 0 or index >= len(docs):
            raise GameError("Document not found.")
        d = docs[index]
        ac = AIRCRAFT[j["type"]]
        state, authority = self._registry(j["reg"])
        ready = d["ready"]
        issued = ready if parse(ready) <= self.now() else None
        co = self.s["company"]
        name = d["name"]
        ref = f"{j['reg'].replace('-', '')}/{j['id']:04d}/{index + 1:02d}"
        base = dict(title=name, ref=ref, status="Issued" if issued else "Application submitted", issued=issued, ready=ready,
                    holder=co["name"], aircraft=f"{ac['name']} ({j['type']})", reg=j["reg"], serial=f"MSN {20000 + j['id'] * 7}",
                    route=" – ".join([j["origin"]] + (j.get("routing") or [j["destination"]])), fields=[], body=[], conditions=[], footer="")
        if name.startswith("Insurance"):
            base.update(issuer="Global Aerospace Underwriting Managers", authority="", fields=[
                ("Policy number", f"AV/{self.now().year}/{7000 + j['id']}"), ("Insured", co["name"]),
                ("Aircraft", f"{base['aircraft']} {j['reg']}"), ("Hull value", f"USD {AIRCRAFT[j['type']]['value'][0] * 1e6:,.0f}"),
                ("Legal liability", "USD 750,000,000 combined single limit"), ("Geographical limits", "Worldwide excluding sanctioned airspace"),
                ("Purpose of flight", "Ferry / positioning, no fare-paying passengers"), ("Period", f"{ready[:10]} to {iso(parse(ready) + timedelta(days=30))[:10]}")])
            base["body"] = ["This certificate is issued as evidence that the insurances described above are in force for the aircraft and purpose stated, "
                            "subject to the terms, conditions and exclusions of the policy. A ferry endorsement extends cover to flights conducted under a "
                            "special flight permit where such a permit is required."]
            base["conditions"] = ["No fare-paying passengers to be carried.", "Crew limited to those necessary for the conduct of the flight.",
                                  "Cover excludes operation contrary to any limitation in the certificate of airworthiness or flight permit."]
        elif "Special flight permit" in name:
            restr = self._restrictions(j["snags"])
            conds = ["The flight shall be conducted by day in visual meteorological conditions." if restr.get("day_only") else
                     "The flight may be conducted by day or by night in accordance with the operator's approvals.",
                     "No person may be carried other than the operating crew and persons essential to the flight.",
                     "No revenue payload may be carried."]
            if restr.get("max_alt"):
                conds.append(f"The aircraft shall not be operated above {restr['max_alt']:,} ft pressure altitude.")
            if restr.get("max_ias"):
                conds.append(f"Airspeed shall not exceed {restr['max_ias']} kt IAS.")
            if restr.get("gear_down"):
                conds.append("The landing gear shall remain extended and locked throughout the flight.")
            if restr.get("no_oceanic"):
                conds.append("The aircraft shall remain within 60 minutes' flying time of an adequate aerodrome at all times.")
            if restr.get("gpu"):
                conds.append("Ground power and an air start unit shall be available at each departure aerodrome.")
            conds.append("The aircraft shall be operated in accordance with the approved flight manual except as varied by this permit.")
            base.update(issuer=authority, authority=f"{state} — {authority}", fields=[
                ("Permit number", f"SFP/{self.now().year}/{1200 + j['id']}"), ("Aircraft", base["aircraft"]), ("Registration", j["reg"]),
                ("Operator", co["name"]), ("Purpose", "Ferry flight to a place where maintenance or storage is to be carried out"),
                ("Routing", base["route"]), ("Validity", f"{ready[:10]} to {iso(parse(ready) + timedelta(days=10))[:10]}")])
            base["body"] = [f"Pursuant to the applicable airworthiness regulations of {state}, permission is granted for the aircraft identified above, "
                            "which does not currently meet all applicable airworthiness requirements but is capable of safe flight, to be flown on the routing "
                            "stated for the purpose stated, subject to the conditions below."]
            base["conditions"] = conds
            base["footer"] = ("This permit does not constitute a certificate of airworthiness and is not valid for the carriage of "
                              "passengers or cargo for hire or reward. Compliance is judged on the conduct of the flight.")
            if j["snags"]:
                base["fields"].append(("Unserviceabilities", "; ".join(f"{x['code']} — {x['name']}" for x in j["snags"])))
        elif "Export CofA" in name:
            base.update(issuer=authority, authority=f"{state} — {authority}", fields=[
                ("Certificate number", f"EXP/{self.now().year}/{400 + j['id']}"), ("Aircraft", base["aircraft"]), ("Registration", j["reg"]),
                ("Manufacturer", ac["mfr"]), ("Exporting state", state), ("Importing state", AIRPORTS.get(j["destination"], {}).get("country", "—")),
                ("Total time", f"{self.rng.randint(20000, 60000):,} hours"), ("Certified for", "Export in accordance with the requirements of the importing authority")])
            base["body"] = ["The aircraft described above has been examined and found to conform to its type design and to be in a condition for safe operation, "
                            "except for the exceptions listed below, which have been accepted by the importing authority.",
                            "This certificate does not constitute authority to operate the aircraft and does not replace a certificate of airworthiness."]
            base["conditions"] = ["Records, modification status and airworthiness directive compliance transferred with the aircraft.",
                                  "Deregistration from the register of the exporting state to follow acceptance."]
        else:
            cc = name.split("—")[-1].strip()
            kind = "Landing" if name.startswith("Landing") else "Overflight"
            base.update(issuer=f"Civil aviation authority — {cc}", authority=f"Diplomatic clearance, {cc}", fields=[
                ("Clearance number", f"{cc}/{self.now().year}/{3000 + j['id'] * 3 + index}"), ("Type", f"{kind} permit — non-scheduled, non-revenue"),
                ("Aircraft", base["aircraft"]), ("Registration", j["reg"]), ("Operator", co["name"]),
                ("Routing", base["route"]), ("Validity", f"{ready[:10]} to {iso(parse(ready) + timedelta(days=7))[:10]} (±72 h on the notified schedule)")])
            base["body"] = [f"Clearance is granted for the aircraft identified above to {'land in' if kind == 'Landing' else 'overfly'} the territory of {cc} "
                            "on the routing and within the validity stated, for the purpose of a ferry flight with no traffic carried."]
            base["conditions"] = ["Flight to be operated in accordance with the notified flight plan and current NOTAM.",
                                  "Any change of aircraft, registration or schedule beyond the tolerance stated requires a fresh clearance.",
                                  "Air navigation and any applicable overflight charges are payable by the operator."]
        return base

    def expedite_docs(self, job_id):
        j = self.job(job_id)
        pending = [d for d in j["docs"] if parse(d["ready"]) > self.now() + timedelta(days=1)]
        if not pending:
            raise GameError("Nothing to expedite.")
        cost = money(2000 + 1.5 * sum(d["fee"] for d in pending) + 600 * len(pending))
        if self.s["cash"] < cost:
            raise GameError(f"Expedite costs ${cost:,}.")
        self.post("Permits", f"Expedited permits job #{j['id']} ({len(pending)} documents)", -cost, ref=j["id"])
        for d in pending:
            d["ready"] = iso(self.now() + timedelta(days=1))
        self.save()

    def rectify_snags(self, job_id):
        j = self.job(job_id)
        if j["status"] != "Accepted" or not j["snags"]:
            raise GameError("No open defects on this job.")
        cost = money(sum(x["cost"] for x in j["snags"]))
        if self.s["cash"] < cost:
            raise GameError(f"Rectification quoted at ${cost:,} by the line station at {j['current']}.")
        self.post("Maintenance", f"Pre-ferry defect rectification job #{j['id']} at {j['current']}", -cost, ref=j["id"])
        j["snags_cleared"] = [x["code"] for x in j["snags"]]
        j["snags"] = []
        j["permit"] = "Standard CofA"
        j["deadline"] = iso(parse(j["deadline"]) + timedelta(days=2))
        self.notice(f"Job #{j['id']}: defects rectified, {j['reg']} released on a standard CofA. Deadline extended 2 days.")
        self.save()

    def _finish_ferry(self, j, success, reason=""):
        base = self.s["company"]["base"]
        for pid in j["crew"]:
            p = self.pilot(pid)
            p["status"], p["job_id"], p["location"] = "Available", None, base
        if success:
            fee = j["fee"] * (0.9 if j.get("rejected") else 1.0)
            self.invoice(j["client"], f"Ferry fee {j['name']} {j['reg']} {j['origin']}–{j['destination']}", fee, ref=j["id"], kind="ferry")
            ret = money(2 * (180 + 0.16 * gc_nm(j["destination"], base)))
            self.post("Crew positioning", f"Return tickets {j['destination']}→{base} x2 (job #{j['id']})", -ret, ref=j["id"])
            j["status"] = "Completed"
            self.s["stats"]["ferry_done"] = self.s["stats"].get("ferry_done", 0) + 1
            self.rep(1.5 + (1.5 if AIRCRAFT[j["type"]]["cat"] == "Widebody" else 0), f"ferry #{j['id']} delivered to {j['client']}")
            if self.s["stats"]["flights"] <= 1 or AIRCRAFT[j["type"]]["cat"] == "Widebody" or (j.get("stops") or 0) >= 3:
                self.event("ferry", f"{j['name']} {j['reg']} delivered to {j['client']}", f"{j['origin']} to {j['destination']}, {j['distance']:,} nm{', ' + str(j['stops']) + ' technical stops' if j.get('stops') else ''}. Fee ${fee:,.0f}.")
            self.mail(j["client"], f"Job #{j['id']} — aircraft accepted at {j['destination']}", f"{j['name']} {j['reg']} accepted. Your invoice for ${fee:,.0f} has been approved for payment. Thank you for the delivery.", action="finance")
            self.award("first_delivery")
            if len([d for d in j["docs"] if "permit" in d["name"].lower()]) >= 3:
                self.award("paperwork")
            if j.get("permit_flown"):
                self.award("permit_ferry")
            return fee
        pen = money(j["fee"] * 0.2)
        self.mail(j["client"], f"Job #{j['id']} cancelled — {reason}", f"The delivery window has expired. A cancellation charge of ${pen:,} applies under the ferry agreement.", action="ferry", pin=True)
        self.post("Penalty", f"Ferry job #{j['id']} cancelled by {j['client']}: {reason}", -pen, ref=j["id"])
        j["status"] = "Cancelled"
        self.rep(-5, f"ferry #{j['id']} not completed ({reason})")
        return 0

    # ================================================================ cargo contract flying
    def cargo_job(self, jid):
        for j in self.s["cargo_board"]:
            if j["id"] == jid:
                return j
        raise GameError("Cargo pairing not found.")

    def _cargo_pairing(self, near_home=False):
        rep = self.s["company"]["reputation"]
        # only carriers with freighters of their own have crews to be short of
        pool = [c for c in CARGO_CARRIERS_WITH_AIRCRAFT if any(self.in_area(b) for b in c["bases"])] \
            or CARGO_CARRIERS_WITH_AIRCRAFT
        if self.restricted_by_type():
            ok = self.allowed_type_codes()
            pool = [c for c in pool if any(t in ok for t in c["types"])]
            if not pool:
                return None          # nobody hires crews for the types on your certificate
        if near_home:
            base = self.s["company"]["base"]
            close = [c for c in pool if any(b in AIRPORTS and gc_nm(base, b) < 1200 for b in c["bases"])]
            pool = close or pool
        if rep < 55:
            pool = [c for c in pool if any(AIRCRAFT[t]["cat"] != "Widebody" for t in c["types"] if t in AIRCRAFT)] or pool
        car = self.rng.choice(pool)
        types = [t for t in car["types"] if t in AIRCRAFT]
        if self.restricted_by_type():
            types = [t for t in types if t in self.allowed_type_codes()]
            if not types:
                return None
        if rep < 55:
            types = [t for t in types if AIRCRAFT[t]["cat"] != "Widebody"] or types
        code = self.rng.choice(types)
        ac = AIRCRAFT[code]
        base = self.rng.choice([b for b in car["bases"] if b in AIRPORTS] or ["KMEM"])
        net = [x for x in car["network"] if x in AIRPORTS and x != base and gc_nm(base, x) < ac["range_nm"] * 0.9]
        # the pattern is flown inside the certificate; the carrier's wider network is
        # theirs, not yours
        in_area_net = [x for x in net if self.in_area(x)]
        net = in_area_net or [x for x in car["network"] if x in AIRPORTS and x != base and self.in_area(x)][:5]
        if not net:
            net = [x for x in self.area_majors() if x != base][:6] or [base]
        long_haul = car["long_haul"] and ac["cat"] == "Widebody" and self.rng.random() < 0.6
        nlegs = self.rng.choice([2, 2, 3, 4]) if not long_haul else self.rng.choice([2, 3, 4, 5, 6])
        legs, cur, t = [], base, self.rng.choice([20, 21, 22, 23, 1, 2]) * 60 if not long_haul else self.rng.randint(0, 23) * 60
        for i in range(nlegs):
            if i == nlegs - 1 and self.rng.random() < 0.8:
                nxt = base
            else:
                choices = [x for x in net if x != cur] or [base]
                nxt = self.rng.choice(choices)
            if nxt == cur:
                nxt = base if cur != base else self.rng.choice(net)
            dist = gc_nm(cur, nxt)
            if dist > ac["range_nm"] * 0.9:
                nxt = min(net, key=lambda x: abs(gc_nm(cur, x) - ac["range_nm"] * 0.7))
                dist = gc_nm(cur, nxt)
            _routine = [x for x in CARGO_LOADS if not x[2]]
            _special = [x for x in CARGO_LOADS if x[2]]
            load, frac, dg = self.rng.choice(_special if self.rng.random() < 0.16 else _routine)
            payload = int(ac["mtow_kg"] * 0.22 * frac * self.rng.uniform(0.7, 1.15))
            ete = int(dist / ac["cruise"] * 60 + 30)
            legs.append(dict(seq=i + 1, flight_number=f"{car['iata']}{self.rng.randint(100, 9990)}", origin=cur, destination=nxt,
                             distance=int(dist), ete_min=ete, std=f"{(t // 60) % 24:02d}:{t % 60:02d}", load=load, payload_kg=payload,
                             dg=dg, flown=False, day=len([l for l in legs if l.get("_d")]) if False else 0))
            cur = nxt
            t += ete + self.rng.choice([90, 120, 180, 600 if long_haul else 240])
        block_h = sum(l["ete_min"] for l in legs) / 60
        days = max(1, int(sum(l["ete_min"] for l in legs) / 60 / 9) + (2 if long_haul else 1))
        bh_rate = {"Turboprop": 260, "Regional": 320, "Narrowbody": 420, "Widebody": 620}[ac["cat"]] * (0.85 + rep / 300) * self.diff()["fee"]
        day_rate = {"Turboprop": 900, "Regional": 1100, "Narrowbody": 1400, "Widebody": 1900}[ac["cat"]]

        # the pairing, priced the way a crewing contract actually is: block hours and
        # duty days for each pilot, then the premiums that genuinely attract more money
        base_pay = 2 * (bh_rate * block_h + day_rate * days)
        night_sectors = sum(1 for l in legs if int(l["std"][:2]) >= 22 or int(l["std"][:2]) < 5)
        ocean_sectors = sum(1 for l in legs
                            if max_remoteness(l["origin"], l["destination"]) > 400)
        extras = []
        premium = 0.0
        if night_sectors:
            v = 2 * day_rate * 0.18 * night_sectors
            premium += v
            extras.append(dict(what=f"Night pay, {night_sectors} sector(s) reporting between 2200 and 0500", amount=money(v)))
        if ocean_sectors:
            v = 2 * bh_rate * 0.25 * (block_h / max(1, len(legs))) * ocean_sectors
            premium += v
            extras.append(dict(what=f"Oceanic and remote pay, {ocean_sectors} sector(s)", amount=money(v)))
        if long_haul:
            v = 2 * day_rate * 0.5
            premium += v
            extras.append(dict(what="Long-haul pattern allowance", amount=money(v)))
        if any(l["dg"] for l in legs):
            v = base_pay * 0.12
            premium += v
            extras.append(dict(what="Special load handling", amount=money(v)))
        pay = base_pay + premium
        return dict(id=self.nid("cargo"), carrier=car["name"], iata=car["iata"], type=code, name=ac["name"], reg=self._reg(), base=base,
                    legs=legs, block_h=round(block_h, 1), days=days, pay=money(pay), bh_rate=money(bh_rate), day_rate=day_rate,
                    base_pay=money(base_pay), extras=extras, night_sectors=night_sectors, ocean_sectors=ocean_sectors,
                    family=ac["family"], long_haul=long_haul, status="Open", crew=[], accepted=None, deadline=None,
                    expires=iso(self.now() + timedelta(days=self.rng.randint(3, 9))), current=base, legs_flown=0,
                    reason=self.rng.choice(["crew shortage", "reserve crew off sick", "seasonal peak", "new lane launch", "crew training backlog", "AOG recovery flight"]),
                    dg=any(l["dg"] for l in legs), payload_max=max(l["payload_kg"] for l in legs))

    HOME_PAIRINGS = 3

    def refresh_cargo_board(self, full=False):
        b = self.s["cargo_board"]
        now = self.now()
        if full:
            b.clear()
        else:
            self.s["cargo_board"] = b = [j for j in b if j["status"] != "Open" or parse(j["expires"]) > now]
        target, spins, dry = 10, 0, 0
        while sum(1 for j in b if j["status"] == "Open") < target and spins < 300 and dry < 25:
            spins += 1
            # keep some work within reach of home, so a company based in Britain is not
            # only offered night freight out of Memphis
            home = sum(1 for j in b if j["status"] == "Open" and j.get("near_home"))
            near = home < self.HOME_PAIRINGS
            j = self._cargo_pairing(near_home=near)
            if not j:
                dry += 1
                continue
            if not self.in_area(j["base"]):
                continue
            j["near_home"] = near
            b.append(j)

    def accept_cargo(self, jid, captain_id, fo_id):
        j = self.cargo_job(jid)
        if j["status"] != "Open":
            raise GameError("This pairing has been taken.")
        cpt, fo = self.pilot(captain_id), self.pilot(fo_id)
        self._check_flight_crew(cpt, fo, j["family"])
        base = self.s["company"]["base"]
        pos = money(2 * (180 + 0.16 * gc_nm(base, j["base"])))
        if self.s["cash"] < pos:
            raise GameError(f"Crew positioning to {j['base']} costs ${pos:,}.")
        self.post("Crew positioning", f"Airline tickets {base}→{j['base']} x2 (cargo pairing #{j['id']})", -pos, ref=j["id"])
        for p in (cpt, fo):
            p["status"], p["job_id"], p["location"] = "Cargo", j["id"], j["base"]
        j["status"], j["crew"], j["accepted"] = "Accepted", [cpt["id"], fo["id"]], self.s["clock"]
        j["deadline"] = iso(self.now() + timedelta(days=j["days"] + 2))
        self.mail(j["carrier"], f"Crew assignment #{j['id']} — {j['iata']} {j['name']} out of {j['base']}",
                  f"Your crew is rostered for {len(j['legs'])} sectors ({j['block_h']:.1f} block hours) starting at {j['base']}. "
                  f"Aircraft and fuel are ours; you fly the schedule. Payment ${j['pay']:,} on completion of the pairing, due by {j['deadline'][:10]}."
                  + (" This pairing carries dangerous goods — the DG paperwork is in the aircraft." if j["dg"] else ""), action="cargo", pin=True)
        self.notice(f"Cargo pairing #{j['id']} accepted with {j['carrier']} at {j['base']}.")
        self.save()
        return j

    def _finish_cargo(self, j, success, reason=""):
        base = self.s["company"]["base"]
        for pid in j["crew"]:
            p = next((x for x in self.s["pilots"] if x["id"] == pid), None)
            if p:
                p["status"], p["job_id"], p["location"] = "Available", None, base
        if success:
            self.invoice(j["carrier"], f"Contract crew pairing #{j['id']} ({j['block_h']:.1f} BH)", j["pay"], ref=j["id"], kind="cargo")
            ret = money(2 * (180 + 0.16 * gc_nm(j["current"], base)))
            self.post("Crew positioning", f"Return tickets {j['current']}→{base} x2 (pairing #{j['id']})", -ret, ref=j["id"])
            j["status"] = "Completed"
            self.s["stats"]["cargo_done"] = self.s["stats"].get("cargo_done", 0) + 1
            self.rep(1.2, f"cargo pairing #{j['id']} completed for {j['carrier']}")
            self.mail(j["carrier"], f"Pairing #{j['id']} complete", f"All {len(j['legs'])} sectors operated. ${j['pay']:,} approved for payment. We will keep your crews on our call list.", action="finance")
            self.award("first_cargo")
            if len([x for x in self.s["cargo_board"] if x["status"] == "Completed"]) <= 1:
                self.event("cargo", f"First cargo pairing completed for {j['carrier']}", f"{len(j['legs'])} sectors, {j['block_h']:.1f} block hours, ${j['pay']:,}.")
            if sum(1 for x in self.s["cargo_board"] if x["status"] == "Completed") >= 5:
                self.award("cargo_regular")
            return j["pay"]
        pen = money(j["pay"] * 0.25)
        self.post("Penalty", f"Cargo pairing #{j['id']} not completed ({reason})", -pen, ref=j["id"])
        j["status"] = "Cancelled"
        self.rep(-4, f"cargo pairing #{j['id']} not completed")
        self.mail(j["carrier"], f"Pairing #{j['id']} — crew failed to complete", f"{reason.capitalize()}. We have covered the remaining sectors ourselves and deducted ${pen:,}.", action="cargo", pin=True)
        return 0

    # ================================================================ ACMI
    def _tender(self, renewal_of=None):
        rep = self.s["company"]["reputation"]
        if renewal_of:
            cust = next(c for c in ACMI_CUSTOMERS if c["name"] == renewal_of["customer"])
            code = renewal_of["type"]
        else:
            cands = [c for c in ACMI_CUSTOMERS if any(self.in_area(h) for h in c.get("hubs", []))] or ACMI_CUSTOMERS
            if self.restricted_by_type():
                fams = set(self.aoc_types())
                cands = [c for c in cands if fams & set(c["fams"])]
                if not cands:
                    return None      # no airline wants capacity on what you are approved for
            cust = self.rng.choice(cands)
            cust = dict(cust, hubs=[h for h in cust.get("hubs", []) if self.in_area(h)] or cust.get("hubs", []))
            own = types_for(cust["name"])
            types = [c for c in own if AIRCRAFT[c]["cargo"] == cust["cargo"]] or \
                    [c for c, a in AIRCRAFT.items() if a["family"] in cust["fams"] and a["cargo"] == cust["cargo"]]
            if self.restricted_by_type():
                types = [t for t in types if t in self.allowed_type_codes()]
                if not types:
                    return None
            if rep < 55:
                types = [t for t in types if AIRCRAFT[t]["cat"] != "Widebody"] or types
            code = self.rng.choice(types)
        ac = AIRCRAFT[code]
        mn = {"Turboprop": (120, 200), "Regional": (150, 250), "Narrowbody": (200, 300), "Widebody": (250, 350)}[ac["cat"]]
        reasons = (["peak cargo season", "e-commerce volume surge", "freighter conversion downtime", "engine shop-visit backlog", "new cargo lane launch", "heavy maintenance cover"]
                   if cust["cargo"] else
                   ["summer schedule capacity", "winter sun programme", "fleet grounding cover", "delivery delay cover", "heavy maintenance cover",
                    "new route launch", "crew shortage cover", "engine shop-visit backlog"])
        months = self.rng.choice([2, 3, 3, 4, 6, 6, 9, 12])
        start = self.now() + timedelta(days=self.rng.randint(6, 30))
        sf = season(start.month, cust["cargo"])
        rate = ac["rate"] * self.rng.uniform(0.9, 1.12) * (0.9 + rep / 500) * sf
        if renewal_of:
            rate = renewal_of["rate"] * self.rng.uniform(1.03, 1.12)
            start = parse(renewal_of["end"])
        hub = renewal_of["hub"] if renewal_of else self.rng.choice(cust["hubs"])
        return dict(id=self.nid("tender"), customer=cust["name"], iata=cust["iata"], type=code, name=ac["name"], hub=hub, family=ac["family"],
                    cargo=cust["cargo"], months=months, min_hours=self.rng.randint(*mn), rate=money(rate), start=iso(start),
                    reason="contract extension offer" if renewal_of else self.rng.choice(reasons), expires=iso(self.now() + timedelta(days=self.rng.randint(5, 20))),
                    network=[x for x in cust["network"]
                             if x in AIRPORTS and gc_nm(hub, x) < ac["range_nm"] * 0.85 and self.in_area(x)]
                            or [x for x in cust["network"][:6] if self.in_area(x)] or [hub],
                    competitors=[] if renewal_of else self.rng.sample(CARGO_COMPETITORS if cust["cargo"] else COMPETITORS, self.rng.randint(1, 3)), renewal=bool(renewal_of),
                    season_note="peak season rate" if sf > 1 else "off-season rate" if sf < 1 else "")

    def refresh_tenders(self, full=False):
        t = self.s["acmi_tenders"]
        now = self.now()
        if full:
            t.clear()
        else:
            for x in list(t):
                if parse(x["expires"]) <= now:
                    if x["competitors"]:
                        self.notice(f"{x['customer']} {x['name']} tender awarded to {self.rng.choice(x['competitors'])}.")
                    t.remove(x)
                elif x["competitors"] and self.rng.random() < 0.03 * (1 - self.s["company"]["reputation"] / 100):
                    w = self.rng.choice(x["competitors"])
                    self.notice(f"{x['customer']} closed the {x['name']} tender early — awarded to {w}.")
                    self.mail(x["customer"], f"{x['name']} requirement — tender closed", f"We have awarded the {x['name']} requirement at {x['hub']} to {w}. We will consider your company for future tenders.", action="tenders")
                    t.remove(x)
        target = int(7 * season(now.month, False))
        spins, dry = 0, 0
        while len(t) < target and spins < 200 and dry < 25:
            spins += 1
            x = self._tender()
            if not x:
                dry += 1
                continue
            if self.in_area(x["hub"]) and len(x.get("network") or []) >= 1:
                t.append(x)

    def accept_tender(self, tender_id, ac_id, crew_ids, livery=True):
        t = next((x for x in self.s["acmi_tenders"] if x["id"] == tender_id), None)
        if not t:
            raise GameError("Tender has expired.")
        a = self.fleet_ac(ac_id)
        if a["type"] != t["type"]:
            raise GameError(f"{t['customer']} requires a {t['name']} ({t['type']}); {a['reg']} is a {a['type']}.")
        if a["status"] != "Available":
            raise GameError(f"{a['reg']} is not available.")
        crew = [self.pilot(i) for i in crew_ids]
        if len(set(crew_ids)) < 4:
            raise GameError("Assign four pilots to the contract.")
        if sum(1 for p in crew if p["rank"] == "CPT") < 2:
            raise GameError("A contract needs at least two captains so both crew sets have a commander.")
        for p in crew:
            if p["status"] != "Available" or t["family"] not in p["ratings"]:
                raise GameError(f"{p['name']} is not available or not rated on {t['family']}.")
        cabin = 0
        if not t["cargo"]:
            cabin = CABIN_PER_SET[a["cat"]] * 2
            free = self.s["staff"]["cabin_crew"] - self._cabin_assigned()
            if free < cabin:
                raise GameError(f"Passenger ACMI on a {a['cat'].lower()} needs {cabin} cabin crew (2 sets); {max(0, free)} unassigned. Hire from Crew.")
        recon = (45000 if a["cat"] in ("Narrowbody", "Regional", "Turboprop") else 120000) if livery else 12000
        if self.s["cash"] < recon:
            raise GameError(f"Livery/decals and cabin reconfiguration costs ${recon:,}.")
        self.post("Reconfiguration", f"{'Livery and cabin reconfiguration' if livery else 'Decals and placards'} {a['reg']} for {t['customer']}", -recon)
        c = dict(id=self.nid("contract"), customer=t["customer"], iata=t["iata"], type=t["type"], name=t["name"], aircraft_id=a["id"], reg=a["reg"],
                 hub=t["hub"], network=t["network"], months=t["months"], min_hours=t["min_hours"], rate=t["rate"], start=t["start"],
                 end=iso(parse(t["start"]) + timedelta(days=30 * t["months"])), reason=t["reason"], cargo=t["cargo"], family=t["family"],
                 hours_month=0.0, hours_total=0.0, legs_month=0, revenue_total=0, months_billed=0, strikes=0, status="Pending start",
                 crew=[p["id"] for p in crew], history=[], signed=self.s["clock"], cabin_crew=cabin, renewal=t["renewal"],
                 kpi=dict(legs_scheduled=0, legs_flown=0, late=0, delay_min=0, satisfaction=80.0))
        a["status"], a["contract_id"], a["livery"] = "ACMI", c["id"], t["customer"]
        self._ground(a, 3 if livery else 1, f"Reconfiguration for {t['customer']}", prev="ACMI")
        for p in crew:
            p["status"], p["contract_id"], p["location"] = "ACMI", c["id"], t["hub"]
        self.s["acmi_tenders"].remove(t)
        self.s["contracts"].append(c)
        self.event("contract", f"ACMI contract signed with {c['customer']}", f"{c['name']} {a['reg']} at {c['hub']}, {c['months']} months at ${c['rate']:,}/BH.")
        self.mail(c["customer"], f"ACMI agreement #{c['id']} — {c['name']} {a['reg']}", f"Term {c['months']} months from {c['start'][:10]} at ${c['rate']:,}/BH, minimum {c['min_hours']} BH per month. Aircraft to be positioned at {c['hub']} in our livery by the start date. Our operations control will publish daily rotations.", action="contracts", pin=True)
        self.award("first_acmi")
        self.notice(f"ACMI contract #{c['id']} signed with {c['customer']}: {c['name']} {a['reg']}, {c['months']} months at ${c['rate']:,}/BH, min {c['min_hours']} BH/month. Position at {c['hub']} by {c['start'][:10]}.")
        self.save()
        return c

    def _end_contract(self, c, status, why):
        a = next((x for x in self.s["fleet"] if x["id"] == c["aircraft_id"]), None)
        if a:
            a["status"], a["contract_id"], a["livery"] = "Available", None, None
            if a.get("prev_status") == "ACMI":
                a["prev_status"] = "Available"
        for pid in c["crew"]:
            p = next((x for x in self.s["pilots"] if x["id"] == pid), None)
            if p:
                p["status"], p["contract_id"], p["location"] = "Available", None, c["hub"]
        c["status"] = status
        self.event("contract", f"Contract with {c['customer']} {status.lower()}", f"{c['hours_total']:.0f} block hours, ${c['revenue_total']:,.0f} revenue. {why.capitalize()}.")
        self.notice(f"Contract #{c['id']} with {c['customer']} {status.lower()}: {why}")
        if status == "Completed" and c["kpi"]["satisfaction"] >= 70:
            t = self._tender(renewal_of=c)
            self.s["acmi_tenders"].insert(0, t)
            self.notice(f"{c['customer']} has offered an extension at ${t['rate']:,}/BH (satisfaction {c['kpi']['satisfaction']:.0f}). See ACMI tenders.")
            self.mail(c["customer"], f"Extension offer — {c['name']}", f"We were satisfied with the performance on agreement #{c['id']} (score {c['kpi']['satisfaction']:.0f}) and would like to extend for {t['months']} months at ${t['rate']:,}/BH. The offer is open until {t['expires'][:10]}.", action="tenders", pin=True)
            self.award("extension")
        elif status == "Terminated":
            self.mail(c["customer"], f"Agreement #{c['id']} terminated", why.capitalize() + ".", action="contracts", pin=True)
        else:
            self.mail(c["customer"], f"Agreement #{c['id']} complete", f"Thank you for {c['hours_total']:.0f} block hours over {c['months']} months. The aircraft is released from our schedule.", action="contracts")

    def operate_rotation(self, cid, date=None, sectors=None):
        """Hand today's rotation to the company crew. An ACMI contract publishes a
        rotation every day whether or not you have time to fly it yourself."""
        c = self.contract(cid)
        if c["status"] != "Active":
            raise GameError("That contract is not active.")
        a = self.fleet_ac(c["aircraft_id"])
        legs = self.rotation(cid, date)
        flown, notes = 0, []
        for leg in legs:
            if sectors and flown >= sectors:
                break
            if a["location"] != leg["origin"]:
                notes.append(f"{a['reg']} is at {a['location']}, not {leg['origin']} — rotation stopped there.")
                break
            try:
                self.dispatch(dict(kind="acmi", contract_id=cid, flight_number=leg["flight_number"],
                                   origin=leg["origin"], destination=leg["destination"],
                                   distance_nm=leg["distance"], ete_min=leg["ete_min"],
                                   block_fuel_lbs=int(leg["distance"] * 14) + 4000, pax=leg.get("pax", 0),
                                   override=True, override_range=True))
                self.fly_with_crew(self.s["dispatched"][-1]["id"])
                flown += 1
            except GameError as e:
                notes.append(str(e))
                break
        if not flown:
            raise GameError(notes[0] if notes else "No sectors could be flown.")
        msg = f"{flown} sector(s) of the {c['customer']} rotation flown by your crew."
        return dict(flown=flown, message=msg + (" " + notes[0] if notes else ""))

    def cancel_contract(self, cid):
        """Hand an ACMI contract back early. The customer charges for the disruption and
        remembers it."""
        c = self.contract(cid)
        if c["status"] not in ("Active", "Pending start"):
            raise GameError("That contract is not running.")
        months_left = max(0, (parse(c["end"]) - self.now()).days / 30.0)
        penalty = money(c["min_hours"] * c["rate"] * min(2.0, months_left) * 0.35)
        if self.s["cash"] < penalty:
            raise GameError(f"Handing the contract back costs ${penalty:,.0f} in early termination charges.")
        self.post("ACMI", f"Early termination — {c['customer']} contract #{c['id']}", -penalty, ref=c["id"])
        c["status"] = "Terminated"
        c["ended"] = self.s["clock"]
        a = next((x for x in self.s["fleet"] if x["id"] == c.get("aircraft_id")), None)
        if a:
            a["status"], a["contract_id"], a["livery"] = "Available", None, None
        for p in self.s["pilots"]:
            if p.get("contract_id") == c["id"]:
                p["contract_id"], p["status"] = None, "Available"
        self.rep(-6, f"ACMI contract with {c['customer']} handed back early")
        self.mail(c["customer"], f"Contract #{c['id']} terminated early",
                  f"We acknowledge your notice to terminate with {months_left:.0f} month(s) remaining. "
                  f"Early termination charges of ${penalty:,.0f} have been invoiced, and we have had to source "
                  "replacement capacity at short notice. We will think carefully before tendering to you again.",
                  action="contracts", pin=True)
        self.notice(f"{c['customer']} contract terminated early — ${penalty:,.0f} in charges.")
        self.save()
        return dict(penalty=penalty, message=f"Contract handed back. Early termination charges ${penalty:,.0f}.")

    def rotation(self, cid, date=None):
        c = self.contract(cid)
        date = date or self.s["clock"][:10]
        r = random.Random(f"{cid}-{date}")
        ac = AIRCRAFT[c["type"]]
        dests = [x for x in c["network"] if x in AIRPORTS and x != c["hub"] and gc_nm(c["hub"], x) < ac["range_nm"] * 0.85]
        if not dests:
            dests = [x for x in c["network"] if x in AIRPORTS and x != c["hub"]] or ["EGLL"]
        n = r.choice([2, 2, 3])
        legs, base_no, t = [], r.randint(100, 8900), 6 * 60 + r.randint(0, 90)
        for i in range(n):
            d = r.choice(dests)
            for k, (o, de) in enumerate(((c["hub"], d), (d, c["hub"]))):
                dist = gc_nm(o, de)
                ete = int(dist / ac["cruise"] * 60 + 25)
                legs.append(dict(seq=len(legs) + 1, flight_number=f"{c['iata']}{base_no + i * 2 + k}", origin=o, destination=de, distance=int(dist),
                                 ete_min=ete, std=f"{t // 60:02d}:{t % 60:02d}", date=date))
                t += ete + 45
        return legs

    # ================================================================ dispatch
    def flight_by_id(self, fid):
        f = next((x for x in self.s["dispatched"] if x["id"] == int(fid)), None)
        if not f:
            raise GameError("That flight is not dispatched.")
        return f

    def tracked(self):
        """The dispatched flight the simulator is following, if any."""
        af = self.s.get("active_flight")
        if af and any(x["id"] == af["id"] for x in self.s["dispatched"]):
            return af
        return None

    def track_flight(self, fid):
        """Point the simulator link at one of the dispatched flights."""
        f = self.flight_by_id(fid)
        if f.get("status") == "En route":
            raise GameError(f"{f['flight_number']} is airborne with the company crew. "
                            "You cannot take over a sector somebody else is flying.")
        self.s["active_flight"] = f
        self.save()
        return f

    def dispatch(self, d):
        if len(self.s["dispatched"]) >= 12:
            raise GameError("Twelve flights are already dispatched. File or cancel one first.")
        busy_ac = {x.get("aircraft_id") for x in self.s["dispatched"] if x.get("aircraft_id")}
        busy_crew = {p for x in self.s["dispatched"] for p in (x.get("crew") or [])}
        busy_reg = {x.get("reg") for x in self.s["dispatched"] if x.get("reg")}
        want = AIRCRAFT.get(d.get("type") or "")
        if want and not self.family_allowed(want["family"]):
            pend = next((p for p in self.type_pending() if p["family"] == want["family"]), None)
            raise GameError(
                f"The {want['family']} is not on your operations specifications, so you cannot release "
                f"the {want['name']} under your AOC. "
                + (f"Your application is with the authority until {pend['ready'][:10]}."
                   if pend else "Apply to add the type on the Company profile."))
        outside = self.area_allowed(d.get("origin", ""), d.get("destination", ""))
        if outside:
            where = ", ".join(f"{f} ({REGIONS[r]['name']})" for f, r in outside)
            raise GameError(f"Your AOC does not cover {where}. Apply to add the area on the Company profile — "
                            "the authority charges a fee and takes a few weeks over it.")
        gu = self.s["safety"].get("grounded_until")
        if gu and self.now() < parse(gu):
            raise GameError(f"Operations are suspended until {gu[:10]} pending the safety audit after the accident.")
        if self.s["staff"]["dispatcher"] < max(1, math.ceil(len(self.s["fleet"]) / STAFF["dispatcher"]["per_aircraft"])):
            raise GameError("No licensed flight dispatcher on duty. Hire dispatchers from Crew → Ground staff.")
        kind = d["kind"]
        org, dst = d["origin"].upper().strip(), d["destination"].upper().strip()
        if len(org) != 4 or len(dst) != 4:
            raise GameError("Origin and destination must be 4-letter ICAO codes.")
        f = dict(id=self.nid("flight"), kind=kind, origin=org, destination=dst, alternate=(d.get("alternate") or "").upper(), route=d.get("route", ""),
                 cruise_alt=int(d.get("cruise_alt") or 0), planned_dist=int(d.get("distance_nm") or 0), planned_ete=int(d.get("ete_min") or 0),
                 block_fuel=int(d.get("block_fuel_lbs") or 0), zfw=int(d.get("zfw_lbs") or 0), pax=int(d.get("pax") or 0), cargo_lbs=int(d.get("cargo_lbs") or 0),
                 ofp_id=d.get("ofp_id", ""), flight_number=d.get("flight_number", ""), status="Planned", created=self.s["clock"], contract_id=None,
                 job_id=None, aircraft_id=None, crew=[], remarks=d.get("remarks", ""), weather=d.get("weather") or {}, std=d.get("std", ""),
                 restrictions={}, snags=[], etops=True, delay_min=0, wx_notes=[])
        ete_h = max(0.5, (f["planned_ete"] or 60) / 60)
        if kind == "acmi":
            c = self.contract(int(d["contract_id"]))
            a = self.fleet_ac(c["aircraft_id"])
            if c["status"] != "Active":
                raise GameError("Contract is not active yet (aircraft must be positioned at the hub and the start date reached).")
            if a["location"] != org:
                raise GameError(f"{a['reg']} is at {a['location']}, not {org}.")
            self._check_airworthy(a)
            crew = self._pick_contract_crew(c, ete_h)
            f.update(contract_id=c["id"], aircraft_id=a["id"], type=a["type"], reg=a["reg"], crew=crew, customer=c["customer"], etops=a["etops"])
            f["flight_number"] = f["flight_number"] or f"{c['iata']}{self.rng.randint(100, 999)}"
            f["delay_min"] = self._tech_delay(a)
        elif kind == "ferry":
            j = self.job(int(d["job_id"]))
            if j["status"] != "Accepted":
                raise GameError("Ferry job not accepted.")
            if j["current"] != org:
                raise GameError(f"Aircraft {j['reg']} is currently at {j['current']}; the next leg must depart from there.")
            legmax = AIRCRAFT[j["type"]]["range_nm"] * 0.9
            if dst in AIRPORTS and gc_nm(org, dst) > legmax:
                nxt = self.next_waypoint(j)
                raise GameError(f"{int(gc_nm(org, dst)):,} nm exceeds the {AIRCRAFT[j['type']]['name']}'s practical range of about {int(legmax):,} nm. "
                                f"The planned routing calls for a technical stop at {nxt} ({int(gc_nm(org, nxt)):,} nm) — file this leg to {nxt} and continue from there.")
            pending = [x for x in j["docs"] if parse(x["ready"]) > self.now()]
            if pending:
                raise GameError(f"Paperwork not complete: {pending[0]['name']} ready {pending[0]['ready'][:10]}. Advance the clock or expedite from the ferry board.")
            for pid in j["crew"]:
                ok, why = self.crew_legal(self.pilot(pid), ete_h)
                if not ok:
                    raise GameError(f"{self.pilot(pid)['name']} {why}.")
            f.update(job_id=j["id"], type=j["type"], reg=j["reg"], crew=j["crew"], customer=j["client"], etops=j["etops"], snags=j["snags"],
                     restrictions=self._restrictions(j["snags"]))
            f["flight_number"] = f["flight_number"] or f"{self.s['company']['code']}{9000 + j['id']}"
        elif kind == "charter":
            j = next((x for x in self.s["charter_jobs"] if x["id"] == int(d.get("job_id") or 0)), None)
            if not j:
                raise GameError("Charter trip not found. Choose a booked trip from the list.")
            if j["status"] in ("Completed", "Missed"):
                raise GameError(f"Trip #{j['id']} is already {j['status'].lower()}. "
                                "Pick another booked trip, or quote for new work on the Charter board.")
            if j["status"] not in ("Booked", "Flying"):
                raise GameError(f"Trip #{j['id']} cannot be flown ({j['status'].lower()}).")
            a = self.fleet_ac(j["aircraft_id"])
            legs = self.charter_legs(j)
            if not legs:
                raise GameError("Every sector of this trip has been flown.")
            leg = legs[0]
            if a["location"] != leg["origin"]:
                raise GameError(f"{a['reg']} is at {a['location']} and the trip needs it at {leg['origin']}. "
                                "Dispatch the trip again and it will position there for you.")
            crew = self._auto_crew(a, ete_h)
            f.update(aircraft_id=a["id"], type=a["type"], reg=a["reg"], crew=crew, job_id=j["id"],
                     customer=f"{j['client']} via {j['broker']}", etops=a["etops"], snags=a["snags"],
                     restrictions=self._restrictions(a["snags"]), pax=j["pax"] if leg["paid"] else 0,
                     charter_leg=dict(leg), origin=leg["origin"], destination=leg["destination"])
            j["status"] = "Flying"
        elif kind == "cargo":
            j = self.cargo_job(int(d["job_id"]))
            if j["status"] != "Accepted":
                raise GameError("Cargo pairing not accepted.")
            leg = next((l for l in j["legs"] if not l["flown"]), None)
            if not leg:
                raise GameError("All sectors in this pairing have been flown.")
            if leg["origin"] != org or leg["destination"] != dst:
                raise GameError(f"The next sector on pairing #{j['id']} is {leg['flight_number']} {leg['origin']}→{leg['destination']}.")
            for pid in j["crew"]:
                ok, why = self.crew_legal(self.pilot(pid), ete_h)
                if not ok:
                    raise GameError(f"{self.pilot(pid)['name']} {why}.")
            f.update(job_id=j["id"], type=j["type"], reg=j["reg"], crew=j["crew"], customer=j["carrier"], etops=True,
                     cargo_lbs=int(leg["payload_kg"] / KG_PER_LB), pax=0, std=leg["std"], load=leg["load"], dg=leg["dg"])
            f["flight_number"] = f["flight_number"] or leg["flight_number"]
        elif kind in ("positioning", "company"):
            a = self.fleet_ac(int(d["aircraft_id"]))
            if a["status"] not in ("Available", "ACMI"):
                raise GameError(f"{a['reg']} is {a['status'].lower()}.")
            if a["location"] != org:
                raise GameError(f"{a['reg']} is at {a['location']}, not {org}.")
            self._check_airworthy(a)
            if a["status"] == "ACMI":
                crew = self._pick_contract_crew(self.contract(a["contract_id"]), ete_h)
            else:
                rated = [p for p in self.s["pilots"] if p["status"] == "Available" and a["family"] in p["ratings"]
                         and self.crew_legal(p, ete_h)[0]]
                cpt = [p for p in rated if p["rank"] == "CPT"]
                if not cpt:
                    raise GameError(f"No available, duty-legal captain rated on {a['family']} to command the flight.")
                second = next((p for p in rated if p["rank"] == "FO" and p["id"] != cpt[0]["id"]),
                              next((p for p in cpt[1:]), None))
                if not second:
                    raise GameError(f"Only one pilot rated on {a['family']} is available; a flight needs two.")
                crew = [cpt[0]["id"], second["id"]]
            legmax = AIRCRAFT[a["type"]]["range_nm"] * 0.9
            if dst in AIRPORTS and org in AIRPORTS and gc_nm(org, dst) > legmax and not d.get("override_range"):
                rt = self.plan_route(a["type"], org, dst)
                raise GameError(f"{int(gc_nm(org, dst)):,} nm exceeds the {AIRCRAFT[a['type']]['name']}'s practical range of about {int(legmax):,} nm. "
                                f"Suggested routing {' – '.join([org] + rt)}: file this leg to {rt[0]} ({int(gc_nm(org, rt[0])):,} nm) and continue from there.")
            f.update(aircraft_id=a["id"], type=a["type"], reg=a["reg"], crew=crew, customer=self.s["company"]["name"], etops=a["etops"],
                     snags=a["snags"], restrictions=self._restrictions(a["snags"]))
            f["flight_number"] = f["flight_number"] or f"{self.s['company']['code']}{8000 + a['id']}"
        else:
            raise GameError("Unknown flight kind.")
        f["twin"] = AIRCRAFT[f["type"]]["family"] != "B747"
        if f["planned_dist"] == 0 and org in AIRPORTS and dst in AIRPORTS:
            f["planned_dist"] = int(gc_nm(org, dst))
        if f["planned_ete"] == 0:
            f["planned_ete"] = int(f["planned_dist"] / AIRCRAFT[f["type"]]["cruise"] * 60 + 25)
        an = self.analyse(f, d)
        if an:
            if an["blocking"] and not d.get("override"):
                raise GameError(" ".join(an["blocking"]) + " Correct the load, choose another runway/airport, or tick Accept performance risk to dispatch anyway.")
            f["perf"] = an
            for w in an["warnings"]:
                f["wx_notes"].append(w) if False else None
        if org in AIRPORTS and dst in AIRPORTS:
            f["remote_nm"] = int(max_remoteness(org, dst))
            f["oceanic"] = f["remote_nm"] > ETOPS_NM
            f["fuel_price_origin"] = round(self.fuel_price(org), 2)
            f["fuel_price_dest"] = round(self.fuel_price(dst), 2)
        # weather screen
        from flightops import wx_flags
        w = f["weather"]
        if w:
            fl = wx_flags(w.get("dest_metar"))
            if fl:
                f["wx_notes"].append(f"Destination: {', '.join(fl)}")
                if not f["alternate"]:
                    f["wx_notes"].append("No alternate filed with adverse destination weather")
            fo = wx_flags(w.get("orig_metar"))
            if fo:
                f["wx_notes"].append(f"Departure: {', '.join(fo)}")
        if f.get("aircraft_id") and f["aircraft_id"] in busy_ac:
            raise GameError(f"{f.get('reg')} is already on a dispatched flight. File or cancel that sector first.")
        if f.get("reg") and f["reg"] in busy_reg:
            raise GameError(f"{f['reg']} is already on a dispatched flight. File or cancel that sector first.")
        clash = [p for p in (f.get("crew") or []) if p in busy_crew]
        if clash:
            raise GameError(f"{self.pilot(clash[0])['name']} is already crewing a dispatched flight.")
        self.s["dispatched"].append(f)
        if not self.tracked():
            self.s["active_flight"] = f
        self.save()
        return f

    def analyse(self, f, d=None):
        """Runway performance and weight & balance for a flight dict."""
        d = d or {}
        t = f["type"]
        org, dst = f["origin"], f["destination"]
        wind_dir = float(d.get("wind_dir") or 0) or None
        wind_kt = float(d.get("wind_kt") or 0)
        oat = float(d["oat_c"]) if d.get("oat_c") not in (None, "") else 15.0
        state = d.get("surface_state") or "dry"
        ballast = float(d.get("ballast_kg") or 0)
        pax_dist = float(d.get("pax_dist", 0.5) or 0.5)
        cargo_dist = float(d.get("cargo_dist", 0.5) or 0.5)
        block_lb = float(f.get("block_fuel") or 0)
        pax = int(f.get("pax") or 0)
        cargo_kg = float(f.get("cargo_lbs") or 0) * KG_PER_LB
        fuel_kg = block_lb * KG_PER_LB
        if not fuel_kg:
            ac = AIRCRAFT[t]
            fuel_kg = (f.get("planned_ete", 60) / 60 * ac["burn"] * 1.25) * KG_PER_LB
        ls = perf.loadsheet(t, pax=pax, cargo_kg=cargo_kg, fuel_kg=fuel_kg, ballast_kg=ballast, pax_dist=pax_dist, cargo_dist=cargo_dist)
        if not ls:
            return None
        trip_kg = 0.0
        if f.get("planned_ete"):
            trip_kg = f["planned_ete"] / 60 * AIRCRAFT[t]["burn"] * KG_PER_LB
        law = max(ls["zfw"], ls["tow"] - trip_kg)
        to = perf.takeoff(t, ls["tow"], org, elevation(org), oat, wind_dir, wind_kt, state, f.get("restrictions"))
        ld = perf.landing(t, law, dst, elevation(dst), oat, wind_dir, wind_kt, state, f.get("restrictions"), f.get("snags"))
        warn, block = [], []
        for x in ls["limits"]:
            (block if ("exceeds" in x and "CG" not in x) else warn).append(x)
        if law > ls["mlw"]:
            warn.append(f"Estimated landing weight {int(law):,} kg is above MLW {ls['mlw']:,} kg — burn or dump fuel before landing.")
        if to and to.get("ok") is False:
            block.append(f"Runway {to['runway']} at {org} is {abs(to['margin']):,} ft short for {int(ls['tow']):,} kg "
                         f"({to['required']:,} ft required, {to['available']:,} ft available). Maximum weight for this runway is about {to['limit_weight']:,} kg.")
        if ld and ld.get("ok") is False:
            block.append(f"Landing distance at {dst} runway {ld['runway']}: {ld['required']:,} ft required, {ld['available']:,} ft available.")
        for src in (to, ld):
            if src:
                warn.extend(src.get("notes", []))
        if to and to.get("ok") and to["margin"] < 500:
            warn.append(f"Only {to['margin']:,} ft of takeoff margin at {org}.")
        if not ls["cg_ok"] and ls["ballast_advised"]:
            warn.append(f"Add about {ls['ballast_advised']:,} kg of forward ballast to bring the CG into the envelope.")
        return dict(loadsheet=ls, takeoff=to, landing=ld, landing_weight=int(law), warnings=warn, blocking=block,
                    conditions=dict(oat_c=oat, wind_dir=wind_dir or 0, wind_kt=wind_kt, surface_state=state,
                                    ballast_kg=int(ballast), pax_dist=pax_dist, cargo_dist=cargo_dist))

    def loadsheet(self, f=None):
        """A full loadsheet in the form an operations department would issue."""
        f = f or self.s.get("active_flight")
        if not f:
            raise GameError("No dispatched flight.")
        an = f.get("perf") or self.analyse(f)
        if not an:
            raise GameError("No performance data for this type.")
        ls, to, ld = an["loadsheet"], an.get("takeoff") or {}, an.get("landing") or {}
        ac = AIRCRAFT[f["type"]]
        p = perf.PERF.get(f["type"], {})
        crew = [self.pilot(i) for i in f.get("crew", []) if any(x["id"] == i for x in self.s["pilots"])]
        cond = an.get("conditions") or {}
        cargo_kg = ls["cargo_kg"]
        fwd = round(cargo_kg * (1 - cond.get("cargo_dist", 0.5)))
        aft = cargo_kg - fwd
        pax = ls["pax"]
        pax_fwd = round(pax * (1 - cond.get("pax_dist", 0.5)))
        # what actually limits the takeoff weight
        limits = [("MTOW structural", ls["mtow"]),
                  ("MZFW + fuel", ls["mzfw"] + ls["fuel_kg"]),
                  ("MLW + trip fuel", ls["mlw"] + max(0, ls["tow"] - an["landing_weight"]))]
        if to.get("limit_weight"):
            limits.append((f"Runway {to.get('runway', '')} {f['origin']}", to["limit_weight"]))
        limiting = min(limits, key=lambda x: x[1])
        underload = limiting[1] - ls["tow"]
        return dict(
            flight=f.get("flight_number"), date=self.s["clock"], origin=f["origin"], destination=f["destination"],
            alternate=f.get("alternate"), aircraft=f"{ac['name']} ({f['type']})", reg=f.get("reg"),
            customer=f.get("customer"), kind=f.get("kind"), load=f.get("load"), dg=bool(f.get("dg")),
            crew=[dict(role="Commander" if i == 0 else "Second pilot", rank=p2["rank"], name=p2["name"]) for i, p2 in enumerate(crew)],
            cabin_crew=0 if f.get("kind") == "ferry" else None,
            weights=dict(
                oew=ls["oew"], pax=pax, pax_kg=ls["pax_kg"], cargo=cargo_kg, ballast=ls["ballast_kg"],
                zfw=ls["zfw"], mzfw=ls["mzfw"], fuel=ls["fuel_kg"], fuel_cap=ls["fuel_cap"],
                tow=ls["tow"], mtow=ls["mtow"], law=an["landing_weight"], mlw=ls["mlw"],
                trip=max(0, ls["tow"] - an["landing_weight"]),
            ),
            distribution=dict(hold_fwd=fwd, hold_aft=aft, cabin_fwd=pax_fwd, cabin_aft=pax - pax_fwd,
                              cargo_dist=cond.get("cargo_dist", 0.5), pax_dist=cond.get("pax_dist", 0.5)),
            balance=dict(zfw_cg=ls["zfw_cg"], tow_cg=ls["tow_cg"], env=ls["env"], ok=ls["cg_ok"],
                         ballast_advised=ls["ballast_advised"]),
            limits=dict(items=[dict(name=n, weight=int(w)) for n, w in limits],
                        limiting=limiting[0], underload=int(underload)),
            performance=dict(
                takeoff=dict(runway=to.get("runway"), required=to.get("required"), available=to.get("available"),
                             margin=to.get("margin"), limit_weight=to.get("limit_weight"), density_alt=to.get("density_alt"),
                             headwind=to.get("headwind"), crosswind=to.get("crosswind")) if to else None,
                landing=dict(runway=ld.get("runway"), required=ld.get("required"), available=ld.get("available"),
                             margin=ld.get("margin"), vref=ld.get("vref")) if ld else None,
                conditions=cond),
            fuel=dict(block=f.get("block_fuel"), block_kg=ls["fuel_kg"], trip_kg=max(0, ls["tow"] - an["landing_weight"]),
                      price=f.get("fuel_price_origin")),
            notes=an.get("warnings", []), blocking=an.get("blocking", []),
            issued_by=self.s["company"]["name"], vref=ld.get("vref"),
        )

    def prefill_flight(self, d):
        """Assemble what SimBrief needs from the dispatch form without dispatching."""
        kind = d["kind"]
        if kind == "charter" and not (d.get("origin") and d.get("destination")):
            # the trip knows where the next sector goes even if the form has not filled in yet
            j = next((x for x in self.s["charter_jobs"] if x["id"] == int(d.get("job_id") or 0)), None)
            if not j:
                raise GameError("Choose a booked charter trip first — quote for work on the Charter board.")
            legs = self.charter_legs(j)
            done = {(l["origin"], l["destination"]) for l in j["flown"]}
            leg = next((l for l in legs if (l["origin"], l["destination"]) not in done), legs[-1])
            d = dict(d, origin=leg["origin"], destination=leg["destination"])
        f = dict(kind=kind, origin=d["origin"].upper().strip(), destination=d["destination"].upper().strip(), alternate=(d.get("alternate") or "").upper(),
                 route=d.get("route", ""), cruise_alt=int(d.get("cruise_alt") or 0), pax=int(d.get("pax") or 0), cargo_lbs=int(d.get("cargo_lbs") or 0),
                 flight_number=d.get("flight_number", ""), std=d.get("std", ""), restrictions={}, snags=[], etops=True, crew=[])
        if not (len(f["origin"]) == 4 and len(f["destination"]) == 4):
            raise GameError("Enter origin and destination first.")
        if kind == "acmi":
            c = self.contract(int(d["contract_id"]))
            a = self.fleet_ac(c["aircraft_id"])
            f.update(type=a["type"], reg=a["reg"], customer=c["customer"], etops=a["etops"], crew=c["crew"][:2])
        elif kind == "ferry":
            j = self.job(int(d["job_id"]))
            f.update(type=j["type"], reg=j["reg"], customer=j["client"], etops=j["etops"], snags=j["snags"], restrictions=self._restrictions(j["snags"]),
                     permit=j["permit"], crew=j["crew"])
        elif kind == "charter":
            j = next((x for x in self.s["charter_jobs"] if x["id"] == int(d.get("job_id") or 0)), None)
            if not j:
                raise GameError("Choose a booked charter trip first — quote for work on the Charter board.")
            if True:
                legs = self.charter_legs(j)
                done = {(l["origin"], l["destination"]) for l in j["flown"]}
                leg = next((l for l in legs if (l["origin"], l["destination"]) not in done), legs[-1])
                f.update(type=j["type"], reg=j["reg"], customer=f"{j['client']} via {j['broker']}",
                         origin=leg["origin"], destination=leg["destination"],
                         pax=j["pax"] if leg["paid"] else 0, charter_leg=dict(leg))
        elif kind == "cargo":
            j = self.cargo_job(int(d["job_id"]))
            leg = next((l for l in j["legs"] if not l["flown"]), j["legs"][-1])
            f.update(type=j["type"], reg=j["reg"], customer=j["carrier"], etops=True, crew=j["crew"], cargo_lbs=int(leg["payload_kg"] / KG_PER_LB), pax=0)
        else:
            a = self.fleet_ac(int(d["aircraft_id"]))
            f.update(type=a["type"], reg=a["reg"], customer=self.s["company"]["name"], etops=a["etops"], snags=a["snags"], restrictions=self._restrictions(a["snags"]))
        return f

    @staticmethod
    def _restrictions(snags):
        r = {}
        for x in snags:
            for k in ("max_alt", "max_ias"):
                if x.get(k):
                    r[k] = min(r.get(k, 1e9), x[k])
            for k in ("gear_down", "day_only", "no_oceanic", "gpu"):
                if x.get(k):
                    r[k] = True
        return r

    def _auto_crew(self, a, ete_h):
        """A commander and a second pilot rated on the type, both duty-legal."""
        rated = [p for p in self.s["pilots"] if p["status"] == "Available" and a["family"] in p["ratings"]
                 and self.crew_legal(p, ete_h)[0] and self.is_current(p, a["family"])[0]]
        cpt = [p for p in rated if p["rank"] == "CPT"]
        if not cpt:
            raise GameError(f"No available, duty-legal and current captain rated on {a['family']}.")
        second = next((p for p in rated if p["id"] != cpt[0]["id"]), None)
        if not second:
            raise GameError(f"Only one pilot rated on {a['family']} is available; a flight needs two.")
        return [cpt[0]["id"], second["id"]]

    def _pick_contract_crew(self, c, ete_h):
        avail = sorted([self.pilot(i) for i in c["crew"] if self.crew_legal(self.pilot(i), ete_h)[0]], key=self._duty_today)
        cp = [p for p in avail if p["rank"] == "CPT"]
        if not cp:
            raise GameError("No duty-legal captain on this contract to command the flight. Wait for rest or assign more crew.")
        second = next((p for p in avail if p["id"] != cp[0]["id"]), None)
        if not second:
            raise GameError("Only one duty-legal pilot on this contract; a flight needs two.")
        return [cp[0]["id"], second["id"]]

    def _tech_delay(self, a):
        age = self.now().year - a["year"]
        p = (0.03 + age / 250 + a["fh_since_a"] / A_CHECK_FH * 0.04 + 0.05 * len(a["snags"])) * self.diff()["delay"]
        if self.rng.random() < p:
            m = self.rng.randint(20, 150)
            self.post("Maintenance", f"Line maintenance call-out {a['reg']} (technical delay {m} min)", -2500)
            self.notice(f"{a['reg']}: technical delay of {m} minutes before departure.")
            self.mail("Maintenance control", f"{a['reg']} technical delay {m} min", self.rng.choice(["Fault on the pre-flight walk-round; line maintenance attending.", "Hydraulic leak found at pushback; deferral being raised.", "Avionics fault reset required; engineer called out.", "Tyre change required before departure."]) + " Delay minutes count against the customer's OTP.")
            return m
        return 0

    def set_flight_status(self, status, fid=None):
        f = self.flight_by_id(fid) if fid else self.tracked()
        if f:
            f["status"] = status
            self.save()

    def cancel_flight(self, fid=None):
        f = self.flight_by_id(fid) if fid else self.tracked()
        if not f:
            self.s["active_flight"] = None
            self.save()
            return
        if f.get("status") == "En route":
            eta = parse(f["crew_flight"]["eta"])
            raise GameError(f"{f['flight_number']} is airborne — {f['origin']} to {f['destination']}, "
                            f"ETA {eta:%d %b %H:%M}Z. The crew have the aeroplane; you cannot cancel "
                            "a sector that is in the air.")
        # a cargo or charter sector that was part way through goes back to the job
        self.s["dispatched"] = [x for x in self.s["dispatched"] if x["id"] != f["id"]]
        if self.s.get("active_flight") and self.s["active_flight"]["id"] == f["id"]:
            self.s["active_flight"] = self.s["dispatched"][0] if self.s["dispatched"] else None
        for pid in f.get("crew", []):
            p = next((x for x in self.s["pilots"] if x["id"] == pid), None)
            if p and p["status"] == "On duty":
                p["status"] = "Available"
        self.save()

    def sync_sim_clock(self, sample):
        """Clock mode 'sim': adopt the simulator's Zulu time (forward only)."""
        if not sample or self.s["company"]["clock_mode"] != "sim":
            return
        try:
            year = sample.get("zulu_year") or self.now().year
            doy = sample.get("zulu_doy") or self.now().timetuple().tm_yday
            dt = datetime(year, 1, 1) + timedelta(days=doy - 1, seconds=int(sample.get("zulu_sec", 0)))
            if dt > self.now():
                self.advance_to(dt)
        except Exception:
            pass

    # ================================================================ safety
    def risk_context(self, f, summ=None):
        ac = AIRCRAFT[f["type"]]
        crew = [p for p in (self._find_pilot(i) for i in f.get("crew", [])) if p]
        duty = max([self._duty_today(p) for p in crew] or [0.0])
        hours = min([p["hours"] for p in crew] or [8000])
        a = next((x for x in self.s["fleet"] if x["id"] == f.get("aircraft_id")), None)
        perf_ = f.get("perf") or {}
        std = (f.get("std") or "")[:2]
        night = std.isdigit() and (int(std) >= 21 or int(std) <= 5)
        ctx = dict(duty_h=duty, crew_hours_min=hours, snags=f.get("snags") or [], wx=f.get("wx_notes") or [],
                   surface_state=(perf_.get("conditions") or {}).get("surface_state", "dry"),
                   runway_margin=(perf_.get("takeoff") or {}).get("margin"), permit_flight=bool(f.get("restrictions")),
                   night=bool(night), a_check_fh=A_CHECK_FH, remote_nm=f.get("remote_nm", 0),
                   xwind=(perf_.get("takeoff") or {}).get("crosswind", 0), hdwind=(perf_.get("takeoff") or {}).get("headwind", 0))
        if a:
            ctx.update(fh_since_a=a["fh_since_a"], age_years=self.now().year - a["year"],
                       engine_hours_left=min([e["hours_to_sv"] for e in a["engines"]] or [5000]),
                       checks_overdue=int(a["fh_since_a"] >= A_CHECK_FH) + int(self.now() > parse(a["c_check_due"])))
        else:
            ctx.update(fh_since_a=self.rng.randint(0, A_CHECK_FH), age_years=self.now().year - (f.get("year") or self.now().year - 12),
                       engine_hours_left=self.rng.randint(400, 6000), checks_overdue=0)
        if summ:
            h = summ.get("handling")
            if h is None:
                vs = summ.get("touchdown_vs") or -200
                h = 1.0 + (0.8 if vs < -700 else 0.4 if vs < -450 else 0.0) + (0.5 if summ.get("overspeed_s") else 0.0) \
                    + (0.6 if any((summ.get("violations") or {}).values()) else 0.0) + (0.3 if summ.get("bounces") else 0.0)
            ctx["handling"] = h
        return ctx

    def _find_pilot(self, pid):
        return next((p for p in self.s["pilots"] if p["id"] == pid), None)

    def safety_roll(self, f, summ, simulated):
        """Roll for an occurrence and apply its consequences. Returns the event or None."""
        sf = self.s["safety"]
        if not sf.get("enabled", True):
            return None
        ctx = self.risk_context(f, summ)
        scale = self.diff()["delay"] * (1.0 if simulated else 0.75)
        ev = safety.roll(ctx, self.rng, scale)
        sf["since_incident"] = sf.get("since_incident", 0) + 1
        if not ev:
            if sf["since_incident"] >= 100:
                self.award("safe_100")
            return None
        return self._apply_occurrence(f, ev, ctx)

    def _apply_occurrence(self, f, ev, ctx):
        sf = self.s["safety"]
        sev, t = ev["severity"], ev["template"]
        a = next((x for x in self.s["fleet"] if x["id"] == f.get("aircraft_id")), None)
        crew = [p for p in (self._find_pilot(i) for i in f.get("crew", [])) if p]
        rec = dict(id=self.nid("occ"), date=self.s["clock"], severity=sev, flight=f["flight_number"], type=f["type"], reg=f.get("reg"),
                   sector=f"{f['origin']}–{f.get('destination')}", owned=bool(a), customer=f.get("customer"), causes=ev["causes"],
                   multiplier=ev["multiplier"], text=t["text"], injuries=0, fatalities=0, cost=0, hull_loss=False,
                   finding=safety.finding_text(ev["causes"]))
        if sev == "occurrence":
            rec["cost"] = t["cost"]
            if t["cost"]:
                self.post("Maintenance", f"Occurrence report {f['flight_number']}: rectification", -t["cost"], ref=f["id"])
            if t["days"] and a:
                self._ground(a, t["days"], "Occurrence rectification")
            self.mail("Safety department", f"Occurrence report — {f['flight_number']}", t["text"] + " Filed as a routine occurrence; no injuries and no damage beyond limits.", action="safety")
        elif sev == "incident":
            days = self.rng.randint(*t["days"])
            value = (a["value"] if a else AIRCRAFT[f["type"]]["value"][0] * 1e6 * 0.6)
            cost = value * self.rng.uniform(*t["cost"])
            inj, fat = safety.casualties(self.rng, t, len(crew), "incident")
            rec.update(injuries=inj, fatalities=fat, cost=money(cost), days=days)
            excess = min(cost, 750000)
            covered = max(0.0, cost - excess)
            if a:
                self.post("Insurance claim", f"Repair excess {a['reg']} after incident on {f['flight_number']}", -excess, ref=f["id"])
                if covered:
                    self.notice(f"Insurers accepted ${covered:,.0f} of the ${cost:,.0f} repair bill for {a['reg']}.")
                self._ground(a, days, "Incident damage repair")
                a["value"] = money(a["value"] * 0.93)
            else:
                liab = cost * 0.5
                self.post("Liability", f"Damage liability to {f.get('customer')} — {f.get('reg')}", -liab, ref=f["id"])
                rec["cost"] = money(liab)
            sf["premium_factor"] = round(min(2.5, sf.get("premium_factor", 1.0) + 0.25), 2)
            self._injure_crew(crew, inj, fat)
            self.rep(-6, f"reportable incident on {f['flight_number']}")
            self._open_investigation(rec, days_open=self.rng.randint(20, 60))
            self.mail("Safety department", f"Serious incident — {f['flight_number']} {f.get('reg')}",
                      t["text"] + (f" {inj} crew member(s) received medical treatment." if inj else " No injuries.")
                      + f" The aircraft is out of service for about {days} days. The authority has opened an investigation.", action="safety", pin=True)
        else:
            inj, fat = safety.casualties(self.rng, t, len(crew), "accident")
            rec.update(injuries=inj, fatalities=fat, hull_loss=True)
            value = a["value"] if a else AIRCRAFT[f["type"]]["value"][0] * 1e6 * 0.7
            if a:
                excess = min(value * 0.05, 2_000_000)
                payout = value - excess if a["owned"] else 0
                self.post("Insurance claim", f"Hull loss excess {a['reg']}", -excess, ref=f["id"])
                if a["owned"] and payout > 0:
                    self.post("Insurance claim", f"Hull insurance settlement {a['reg']}", payout, ref=f["id"])
                if not a["owned"]:
                    self.post("Liability", f"Agreed hull value settlement to {a['lessor']} for {a['reg']}", -value * 0.35, ref=f["id"])
                for c in self.s["contracts"]:
                    if c["aircraft_id"] == a["id"] and c["status"] in ("Active", "Pending start"):
                        self._end_contract(c, "Terminated", "the aircraft was lost")
                self.s["fleet"].remove(a)
                rec["cost"] = money(value)
            else:
                liab = value * 0.45
                self.post("Liability", f"Hull liability to {f.get('customer')} — {f.get('reg')} destroyed", -liab, ref=f["id"])
                rec["cost"] = money(liab)
            if fat:
                self.post("Crew", "Death in service benefits and support to families", -900000 * fat)
            if inj:
                self.post("Crew", "Medical costs and crew support", -140000 * inj)
            self._injure_crew(crew, inj, fat)
            sf["hull_losses"] = sf.get("hull_losses", 0) + 1
            sf["premium_factor"] = round(min(3.5, sf.get("premium_factor", 1.0) + 0.8), 2)
            ground = self.rng.randint(5, 14)
            sf["grounded_until"] = iso(self.now() + timedelta(days=ground))
            self.rep(-25 if fat else -18, f"accident involving {f.get('reg')}")
            self._open_investigation(rec, days_open=self.rng.randint(180, 420))
            head = "Accident" + (" with fatalities" if fat else "")
            self.mail("Safety department", f"{head} — {f['flight_number']} {f.get('reg')}",
                      t["text"] + (f" The two operating crew were lost." if fat >= 2 else f" {fat} crew member(s) were lost." if fat else
                                   f" {inj} crew member(s) were injured." if inj else " The crew were not injured.")
                      + f" The aircraft was destroyed. The authority has opened a full investigation and our operations are suspended for {ground} days pending an audit.",
                      action="safety", pin=True)
            self.notice(f"ACCIDENT: {f.get('reg')} was destroyed on {f['origin']}–{f.get('destination')}. Operations suspended for {ground} days.")
            for j in self.s["ferry_board"]:
                if j["status"] == "Accepted" and f.get("job_id") == j["id"]:
                    j["status"] = "Cancelled"
            for j in self.s["cargo_board"]:
                if j["status"] == "Accepted" and f.get("job_id") == j["id"]:
                    j["status"] = "Cancelled"
        self.event("safety", ("Accident — " if sev == "accident" else "Serious incident — " if sev == "incident" else "Occurrence — ") + f"{f.get('reg') or f['type']} on {f['origin']}–{f.get('destination')}",
                   rec["text"] + (f" {rec['fatalities']} crew lost." if rec["fatalities"] else f" {rec['injuries']} crew injured." if rec["injuries"] else ""))
        sf["occurrences"].insert(0, rec)
        sf["occurrences"] = sf["occurrences"][:120]
        sf["injuries"] = sf.get("injuries", 0) + rec["injuries"]
        sf["fatalities"] = sf.get("fatalities", 0) + rec["fatalities"]
        if sev != "occurrence":
            sf["since_incident"] = 0
        return rec

    def _injure_crew(self, crew, injured, fatal):
        for i, p in enumerate(crew):
            if i < fatal:
                self.s["pilots"] = [x for x in self.s["pilots"] if x["id"] != p["id"]]
            elif i < fatal + injured:
                p["status"], p["job_id"], p["contract_id"] = "Medical", None, None
                p["training_until"] = iso(self.now() + timedelta(days=self.rng.randint(30, 120)))

    def _open_investigation(self, rec, days_open):
        self.s["safety"]["investigation"] = dict(occurrence_id=rec["id"], opened=self.s["clock"],
                                                 due=iso(self.now() + timedelta(days=days_open)), flight=rec["flight"], reg=rec["reg"])

    def safety_summary(self):
        sf = self.s["safety"]
        flights = max(1, self.s["stats"]["flights"])
        occ = sf["occurrences"]
        return dict(enabled=sf.get("enabled", True), occurrences=occ[:40], since_incident=sf.get("since_incident", 0),
                    hull_losses=sf.get("hull_losses", 0), fatalities=sf.get("fatalities", 0), injuries=sf.get("injuries", 0),
                    premium_factor=sf.get("premium_factor", 1.0), grounded_until=sf.get("grounded_until"),
                    investigation=sf.get("investigation"), rate=round(len([o for o in occ if o["severity"] != "occurrence"]) / flights * 1000, 2),
                    exposure=dict(sectors=self.s["stats"]["flights"], hours=self.s["stats"]["hours"]))

    def current_risk(self):
        """Live risk picture across the fleet and roster, for the safety dashboard."""
        items = []
        today = self.s["clock"][:10]
        for p in self.s["pilots"]:
            d = p["duty_h"] if p.get("duty_date") == today else 0
            if d >= 9:
                items.append(dict(level="high", text=f"{p['rank']} {p['name']} has {d:.1f} h duty today."))
            if p["hours"] < 1500:
                items.append(dict(level="watch", text=f"{p['rank']} {p['name']} has {p['hours']:,.0f} total hours — limited experience."))
        for a in self.s["fleet"]:
            left = A_CHECK_FH - a["fh_since_a"]
            if left <= 0:
                items.append(dict(level="high", text=f"{a['reg']} A-check overdue."))
            elif left < 60:
                items.append(dict(level="watch", text=f"{a['reg']} has {left:.0f} h to its A-check."))
            if self.now() > parse(a["c_check_due"]):
                items.append(dict(level="high", text=f"{a['reg']} C-check overdue."))
            esv = min([e["hours_to_sv"] for e in a["engines"]] or [9999])
            if esv < 250 and not a["pbh"]:
                items.append(dict(level="watch", text=f"{a['reg']} engine {esv:.0f} h from its shop visit."))
            if a["snags"]:
                items.append(dict(level="watch", text=f"{a['reg']} carrying {len(a['snags'])} deferred defect(s)."))
            if self.now().year - a["year"] > 22:
                items.append(dict(level="watch", text=f"{a['reg']} is {self.now().year - a['year']} years old."))
        for j in self.s["ferry_board"]:
            if j["status"] == "Accepted" and j["snags"]:
                items.append(dict(level="watch", text=f"Ferry job #{j['id']}: {j['reg']} carries {len(j['snags'])} deferred defect(s) under a permit."))
        return items[:20]

    # ================================================================ PIREP
    CREW_TURN_MIN = 45          # taxi in, shut down, paperwork, crew off the aircraft

    def fly_with_crew(self, fid=None):
        """Hand the dispatched sector to the company crew.

        The crew take the aeroplane and it is gone for as long as the sector takes.
        The outcome is settled at the moment they push back — their experience, their
        duty time and the conditions you sent them into — but it is not filed until
        they land. On the game clock that is the same thing, because the clock is
        yours to move, so the sector files at once and the clock jumps; on a real or
        simulator clock the aircraft and the crew are unavailable until the ETA.
        """
        from flightops import simulate_sector
        f = self.flight_by_id(fid) if fid else self.tracked()
        if not f:
            raise GameError("No dispatched flight.")
        if f.get("status") == "En route":
            cf = f["crew_flight"]
            raise GameError(f"{f['flight_number']} is already airborne with the crew; "
                            f"it files on arrival at {parse(cf['eta']):%d %b %H:%M}Z.")
        ctx = self.risk_context(f)
        summ = simulate_sector(f, AIRCRAFT[f["type"]], ctx, self.rng)
        block = max(1, int(round(summ.get("block_min") or f["planned_ete"] or 60)))
        off = self.now() + timedelta(minutes=int(f.get("delay_min") or 0))
        eta = off + timedelta(minutes=block)
        f["status"] = "En route"
        f["crew_flight"] = dict(off=iso(off), eta=iso(eta), block_min=block, summary=summ)
        self.save()
        if self.s["company"].get("clock_mode", "game") == "game":
            # the player drives this clock, so there is nothing to wait for
            self.advance_to(eta + timedelta(minutes=self.CREW_TURN_MIN))
            rec = next((r for r in self.s["flights"] if r["id"] == f["id"]), None)
            if rec:
                return dict(filed=True, pirep=rec)
        self.notice(f"{f['flight_number']} off blocks with the crew — {f['origin']} to {f['destination']}, "
                    f"ETA {eta:%d %b %H:%M}Z.")
        self.save()
        return dict(filed=False, eta=iso(eta), block_min=block, flight_number=f["flight_number"],
                    id=f["id"], origin=f["origin"], destination=f["destination"])

    def _settle_crew_flights(self):
        """File any crew-flown sector that has reached its destination."""
        now = self.now()
        due = sorted([f for f in self.s["dispatched"]
                      if f.get("status") == "En route" and f.get("crew_flight")
                      and parse(f["crew_flight"]["eta"]) <= now],
                     key=lambda x: x["crew_flight"]["eta"])
        for f in due:
            cf = f.pop("crew_flight")
            f["status"] = "Planned"
            try:
                self.file_pirep(cf["summary"], simulated=True, fid=f["id"], advance_clock=False)
            except GameError:
                f["status"], f["crew_flight"] = "En route", cf      # put it back; try again next tick
                break

    def crew_airborne(self):
        """Sectors the crews are operating right now, for the dispatch and schedule screens."""
        out = []
        for f in self.s["dispatched"]:
            cf = f.get("crew_flight")
            if f.get("status") != "En route" or not cf:
                continue
            off, eta = parse(cf["off"]), parse(cf["eta"])
            total = max(1.0, (eta - off).total_seconds())
            done = (self.now() - off).total_seconds()
            out.append(dict(id=f["id"], flight_number=f["flight_number"], origin=f["origin"],
                            destination=f["destination"], type=f["type"], reg=f["reg"],
                            off=cf["off"], eta=cf["eta"], block_min=cf["block_min"],
                            progress=round(max(0.0, min(1.0, done / total)), 3),
                            minutes_left=max(0, int((eta - self.now()).total_seconds() // 60)),
                            crew=f.get("crew", []), kind=f["kind"]))
        return out

    def file_pirep(self, summ, manual=False, simulated=False, fid=None, advance_clock=True):
        f = self.flight_by_id(fid) if fid else self.tracked()
        if not f:
            raise GameError("No dispatched flight.")
        if f.get("status") == "En route":
            raise GameError(f"{f['flight_number']} is airborne with the company crew; "
                            f"it files itself on arrival at {parse(f['crew_flight']['eta']):%d %b %H:%M}Z.")
        ac = AIRCRAFT[f["type"]]
        arrival, diverted = f["destination"], False
        if manual:
            block_min = f["planned_ete"]
            fuel_burn = int(f["planned_dist"] / ac["cruise"] * ac["burn"])
            touchdown_vs, max_g, overspeed, taxi_over, dist = None, 1.0, 0, 0, f["planned_dist"]
            summ = summ or {}
        else:
            if not summ.get("complete"):
                raise GameError("Flight is not complete: taxi to the gate, set the parking brake and shut down before filing.")
            last = summ.get("last") or {}
            if last.get("lat"):
                near, dn = self.nearest_airport(last["lat"], last["lon"])
                if dn > 6:
                    arrival, diverted = near or "ZZZZ", True
                elif near != f["destination"] and f["destination"] in AIRPORTS:
                    arrival, diverted = near, True
            block_min = max(1, summ["block_min"])
            fuel_burn = summ["fuel_burn"] or int(block_min / 60 * ac["burn"])
            touchdown_vs, max_g, overspeed, taxi_over = summ["touchdown_vs"], summ["max_g"], summ["overspeed_s"], summ["taxi_overspeed_s"]
            dist = summ["dist_nm"] or f["planned_dist"]
        block_hrs = block_min / 60
        if manual:
            score, notes = 70, ["Manual PIREP (no telemetry) — capped at 70."]
        elif simulated:
            score, notes = 92, [f"Operated by the company crew without the simulator; scoring capped at 92."]
        else:
            score, notes = 100, []
        # ---- landing
        if touchdown_vs is not None:
            if touchdown_vs < -1000:
                score -= 60; notes.append(f"Very hard landing {touchdown_vs} fpm — structural inspection required.")
            elif touchdown_vs < -700:
                score -= 35; notes.append(f"Hard landing {touchdown_vs} fpm — hard landing inspection required.")
            elif touchdown_vs < -450:
                score -= 12; notes.append(f"Firm landing {touchdown_vs} fpm.")
            elif touchdown_vs > -60:
                notes.append(f"Smooth touchdown {touchdown_vs} fpm.")
        if not manual:
            if summ.get("bounces"):
                score -= 6 * summ["bounces"]; notes.append(f"Bounced landing ({summ['bounces']}).")
            tdz = None
            if summ.get("td_lat"):
                tdz = perf.landing_position(summ["td_lat"], summ["td_lon"], summ.get("td_hdg"), arrival)
            if tdz:
                summ["tdz"] = tdz
                if tdz["from_threshold"] < 0:
                    score -= 25; notes.append(f"Touched down short of runway {tdz['runway']}.")
                elif tdz["from_threshold"] < 500:
                    score -= 6; notes.append(f"Touchdown {tdz['from_threshold']} ft from the threshold of runway {tdz['runway']} — short of the touchdown zone.")
                elif tdz["from_threshold"] > 3000:
                    score -= 12; notes.append(f"Long landing: touchdown {tdz['from_threshold']:,} ft down runway {tdz['runway']} of {tdz['length']:,} ft.")
                elif tdz["from_threshold"] > 2000:
                    score -= 5; notes.append(f"Touchdown {tdz['from_threshold']:,} ft down runway {tdz['runway']}.")
                else:
                    notes.append(f"Touchdown in the zone, {tdz['from_threshold']} ft down runway {tdz['runway']}, {abs(tdz['centreline'])} ft {'right' if tdz['centreline'] > 0 else 'left'} of centreline.")
                if abs(tdz["centreline"]) > 75:
                    score -= 8; notes.append(f"Off centreline by {abs(tdz['centreline'])} ft at touchdown.")
                if tdz["from_threshold"] > 0 and tdz["length"] - tdz["from_threshold"] < 2500 and AIRCRAFT[f["type"]]["cat"] != "Turboprop":
                    notes.append(f"Only {tdz['length'] - tdz['from_threshold']:,} ft of runway remaining at touchdown.")
                self.award("tdz") if 500 <= tdz["from_threshold"] <= 1500 and abs(tdz["centreline"]) <= 25 else None
            if summ.get("td_bank") is not None and abs(summ["td_bank"]) > 5:
                score -= 5; notes.append(f"Wing-low touchdown, bank {summ['td_bank']}°.")
            if summ.get("td_pitch") is not None and summ["td_pitch"] > 9 and ac["cat"] != "Turboprop":
                score -= 8; notes.append(f"High pitch at touchdown ({summ['td_pitch']}°) — tail-strike risk.")
            if summ.get("td_xwind") is not None and abs(summ["td_xwind"]) > 30:
                notes.append(f"Crosswind {abs(summ['td_xwind'])} kt at touchdown — above most demonstrated limits.")
            if summ.get("flare_vs") is not None and summ["flare_vs"] < -1100:
                score -= 5; notes.append(f"Unstable at 50 ft: {summ['flare_vs']} fpm.")
            for g in (summ.get("stability") or []):
                if not g["stable"]:
                    score -= 8 if g["gate"] == 500 else 5
                    notes.append(f"Unstable at {g['gate']} ft: {', '.join(g['issues'])}.")
            v = summ.get("violations", {})
            if v.get("max_alt"):
                score -= 20; notes.append("Exceeded ferry-permit altitude limit.")
            if v.get("max_ias"):
                score -= 15; notes.append("Exceeded ferry-permit speed limit.")
            if v.get("gear_up"):
                score -= 30; notes.append("Gear retracted on a gear-down ferry — permit breached.")
            if f.get("restrictions") and not any(v.values()):
                if f["kind"] == "ferry":
                    self.job(f["job_id"])["permit_flown"] = True
            remote = summ.get("max_remote_nm", 0)
            if remote > ETOPS_NM:
                self.award("atlantic")
            if touchdown_vs is not None and touchdown_vs > -60:
                self.award("greaser")
            no_oceanic = f.get("restrictions", {}).get("no_oceanic") or (not f.get("etops", True) and f.get("twin", True) and ac["family"] != "B747")
            if no_oceanic and remote > ETOPS_NM:
                score -= 20; notes.append(f"Non-ETOPS aircraft flew {remote} nm from the nearest diversion airport (limit ≈{ETOPS_NM} nm).")
            elif remote > ETOPS_NM:
                notes.append(f"Oceanic sector: {remote} nm from nearest diversion airport at the farthest point (ETOPS).")
        if max_g > 2.0:
            score -= 10; notes.append(f"Exceeded 2.0 G ({max_g}).")
        if overspeed > 0:
            score -= min(25, 5 + overspeed); notes.append(f"Overspeed for {overspeed}s.")
        if taxi_over > 5:
            score -= 5; notes.append(f"Taxi speed above 30 kt for {taxi_over}s.")
        if diverted:
            notes.append(f"Diverted / landed at {arrival} instead of {f['destination']}.")
        if not manual and f["block_fuel"] and summ.get("fuel_start"):
            diff = abs(summ["fuel_start"] - f["block_fuel"]) / max(1, f["block_fuel"])
            if diff > 0.15:
                score -= 5; notes.append(f"Block fuel differed from OFP by {int(diff * 100)}%.")
        for n in f.get("wx_notes", []):
            if "No alternate" in n:
                score -= 5; notes.append(n + ".")
        score = max(0, score)
        # ---- money
        income, costs = [], []
        if f["kind"] not in ("ferry", "cargo"):          # client's aircraft, client's maintenance
            costs.append(("Maintenance reserve", ac["mx_fh"] * block_hrs))
        costs.append(("Crew per diem", 2 * 95 * max(1, block_hrs / 8)))
        if touchdown_vs is not None and touchdown_vs < -700:
            costs.append(("Hard landing inspection", ac["mx_fh"] * (60 if touchdown_vs < -1000 else 25)))
        if f.get("restrictions", {}).get("gpu"):
            costs.append(("GPU / air-start (APU inop)", 450))
        job_done = False
        if f["kind"] == "acmi":
            c = self.contract(f["contract_id"])
            rev = c["rate"] * block_hrs
            income.append((f"ACMI block hours {c['customer']} ({block_hrs:.2f} BH @ ${c['rate']:,})", rev))
            c["hours_month"] += block_hrs; c["hours_total"] += block_hrs; c["legs_month"] += 1; c["revenue_total"] += rev
            k = c["kpi"]; k["legs_flown"] += 1
            if f["delay_min"] > 15:
                k["late"] += 1; k["delay_min"] += f["delay_min"]
                pen = (f["delay_min"] - 15) * 60
                costs.append((f"Delay penalty clause ({f['delay_min']} min)", pen))
                notes.append(f"Departed {f['delay_min']} min late (technical); delay penalty applied.")
            if diverted:
                k["late"] += 1
        elif f["kind"] == "ferry":
            j = self.job(f["job_id"])
            j["current"] = arrival
            j["legs"].append(dict(flight_id=f["id"], origin=f["origin"], arrival=arrival, block_min=block_min))
            for pid in j["crew"]:
                self.pilot(pid)["location"] = arrival
            costs.append(("Crew hotel", 2 * 210))
            if arrival == j["destination"]:
                if j["kind"] in ("Lease return", "Redelivery", "Sale delivery") and not j.get("rejected"):
                    p = 0.06 + 0.12 * len(j["snags"]) + (0.3 if score < 60 else 0)
                    if self.rng.random() < p:
                        mro = min((s for m in MROS for s in m["sites"] if s != arrival), key=lambda s: gc_nm(arrival, s))
                        j["rejected"], j["destination"] = True, mro
                        j["deadline"] = iso(self.now() + timedelta(days=4))
                        self.mail(j["client"], f"Job #{j['id']} — aircraft NOT accepted at {arrival}", f"Our technical representative found the aircraft outside redelivery conditions ({len(j['snags'])} open defects). Please ferry {j['reg']} to {mro} for rectification within 4 days. The fee is reduced 10% under the agreement.", action="ferry", pin=True)
                        notes.append(f"{j['client']} rejected the aircraft at redelivery inspection (open defects). Ferry to {mro} for rectification; fee reduced 10%.")
                        self.rep(-2, f"redelivery rejected on job #{j['id']}")
                    else:
                        job_done = True
                else:
                    job_done = True
        elif f["kind"] == "charter":
            j = next((x for x in self.s["charter_jobs"] if x["id"] == f.get("job_id")), None)
            if j:
                leg = f.get("charter_leg") or {}
                j["flown"].append(dict(origin=f["origin"], destination=arrival, score=score, paid=bool(leg.get("paid")),
                                       touchdown=summ.get("touchdown_vs") if summ else None))
                if leg.get("paid"):
                    j["done"] = int(j.get("done", 0)) + 1
                client = self.client_legs(j)
                if j.get("done", 0) >= len(client):
                    # what it cost you to run: handling at every stop, and the crew away overnight
                    stops = len({l["destination"] for l in client}) + 1
                    cat = AIRCRAFT[j["type"]]["cat"]
                    # handling scales with the aeroplane: a stand and a set of steps for a
                    # light jet, a full turnaround crew for an airliner
                    handling = stops * {"Turboprop": 950, "Light jet": 900, "Midsize jet": 1000,
                                        "Super-midsize jet": 1200, "Heavy jet": 1800,
                                        "Regional": 1900, "Narrowbody": 2600, "Widebody": 5200}.get(cat, 1200)
                    nights = j.get("nights", 0)
                    crew_away = 2 + (j.get("needs", {}).get("attendants", 0) if j.get("group") else 0)
                    hotels = nights * crew_away * 240 + nights * crew_away * 95
                    # catering per head: a named restaurant for a private party, a tray for a charter group
                    per_head = 14 if j.get("group") else 60
                    catering = per_head * j["pax"] * max(1, len(client))
                    self.post("Charter costs", f"Handling, catering and crew expenses — trip #{j['id']}",
                              -(handling + hotels + catering), ref=j["id"])
                    j["direct_costs"] = money(handling + hotels + catering)

                    # how the client judges it, weighted by what this client cares about
                    cares = j.get("cares") or dict(punctual=0.45, comfort=0.35, cabin=0.20)
                    tds = [abs(x["touchdown"] or 250) for x in j["flown"] if x.get("touchdown")]
                    comfort = 100 - (sum(tds) / len(tds) - 150) / 6 if tds else 82
                    late = max(0.0, (self.now() - parse(j["depart"])).total_seconds() / 3600)
                    punctual = 100 - min(70, late * 12 / max(0.4, j.get("tolerance", 1.0)))
                    cabin = 100 - 14 * len(j.get("fit_notes") or [])
                    sat = round(comfort * cares.get("comfort", 0.35) + punctual * cares.get("punctual", 0.45)
                                + cabin * cares.get("cabin", 0.20))
                    sat = max(20, min(100, sat))
                    j["scorecard"] = dict(comfort=round(comfort), punctual=round(punctual), cabin=round(cabin))
                    j["satisfaction"], j["status"] = sat, "Completed"
                    self.invoice(j["broker"], f"Charter {j['origin']}–{j['destination']} for {j['client'].lower()}", j["fee"], ref=j["id"], kind="charter")
                    self.rep(2.0 if sat >= 80 else 0.5 if sat >= 60 else -2.0, f"charter for {j['client'].lower()}")
                    notes.append(f"Charter complete for {j['client'].lower()} via {j['broker']}; "
                                 f"${j['fee']:,.0f} invoiced, ${j['direct_costs']:,.0f} of trip costs. "
                                 f"Client satisfaction {sat} (comfort {j['scorecard']['comfort']}, "
                                 f"punctuality {j['scorecard']['punctual']}, cabin {j['scorecard']['cabin']}).")
                    self._offer_empty_leg(j, arrival)
                    if sat >= 85 and self.rng.random() < 0.5:
                        self.mail(j["broker"], "Repeat business",
                                  f"The client was pleased. We will come to you first next time we have something similar.",
                                  action="charter")
                        self.s["company"]["reputation"] = min(100.0, self.s["company"]["reputation"] + 0.5)
                else:
                    client = self.client_legs(j)
                    rest = client[j.get("done", 0):]
                    nxt = None
                    if rest:
                        nxt = (dict(origin=arrival, destination=rest[0]["origin"], paid=False)
                               if arrival != rest[0]["origin"] else dict(rest[0]))
                    notes.append(f"Charter sector complete; {len(client) - j.get('done', 0)} client sector(s) to go."
                                 + (f" Next: {nxt['origin']} to {nxt['destination']}"
                                    + ("" if nxt["paid"] else " — positioning, unpaid") + "." if nxt else ""))
        elif f["kind"] == "cargo":
            j = self.cargo_job(f["job_id"])
            leg = next((l for l in j["legs"] if not l["flown"]), None)
            if leg:
                leg["flown"] = True
                leg["actual"] = dict(flight_id=f["id"], arrival=arrival, block_min=round(block_min, 1), score=score)
            j["current"] = arrival
            j["legs_flown"] += 1
            for pid in j["crew"]:
                self.pilot(pid)["location"] = arrival
            costs.append(("Crew hotel", 2 * 195))
            if f.get("dg"):
                self.award("cargo_dg")
            if dist > 3000:
                self.award("cargo_long")
            if diverted:
                notes.append(f"{j['carrier']} operations advised of the diversion; the remaining sectors are rescheduled from {arrival}.")
                for l in j["legs"]:
                    if not l["flown"]:
                        l["origin"] = arrival
                        break
            if all(l["flown"] for l in j["legs"]):
                pay = self._finish_cargo(j, True)
                income.append(("Pairing payment", pay))
                notes.append(f"Pairing #{j['id']} complete: {len(j['legs'])} sectors for {j['carrier']}, ${pay:,.0f} invoiced.")
        else:
            price = self.fuel_price(f["origin"])
            costs += [(f"Fuel uplift {f['origin']} @ ${price:.2f}/USG", fuel_burn / FUEL_LBS_PER_USG * price),
                      (f"Landing & handling {arrival}", ac["mtow_kg"] / 1000 * 6.5 + 900), ("Navigation charges", ac["mtow_kg"] / 1000 * 0.9 * max(1, dist / 100))]
        if f["aircraft_id"]:
            a = self.fleet_ac(f["aircraft_id"])
            if a["pbh"]:
                costs.append((f"Power-by-the-hour ({ENGINE_OEM[a['family']]})", a["pbh_rate"] * block_hrs))
        for desc, amt in income:
            if f["kind"] == "acmi":
                self.invoice(f.get("customer") or "Customer", desc, amt, ref=f["id"], kind="acmi")
            elif f["kind"] in ("ferry", "cargo"):
                pass                                   # invoiced when the job completes
            else:
                self.post("Flight revenue", desc, amt, ref=f["id"])
        for desc, amt in costs:
            self.post("Flight costs", f"{desc} — {f['flight_number']}", -amt, ref=f["id"])
        # ---- aircraft / crew
        if f["aircraft_id"]:
            a = self.fleet_ac(f["aircraft_id"])
            a["hours"] += round(block_hrs, 2); a["cycles"] += 1; a["fh_since_a"] += block_hrs; a["location"] = arrival
            for e in a["engines"]:
                e["hours_to_sv"] -= block_hrs
            if a["status"] == "ACMI":
                c = self.contract(a["contract_id"])
                if c["status"] == "Pending start" and arrival == c["hub"]:
                    self.notice(f"{a['reg']} positioned at {c['hub']} for {c['customer']}.")
        for pid in f["crew"]:
            p = next((x for x in self.s["pilots"] if x["id"] == pid), None)
            if p:
                p["hours"] += round(block_hrs, 1)
                p["company_hours"] = round(p.get("company_hours", 0) + block_hrs, 1)
                self._log_landing(p, AIRCRAFT[f["type"]]["family"])
                self._log_duty(p, block_hrs)
        if score >= 90:
            self.rep(0.4, f"{f['flight_number']} completed, score {score}")
        elif score < 60:
            self.rep(-1.5, f"{f['flight_number']} score {score}")
        if job_done:
            j = self.job(f["job_id"])
            fee = self._finish_ferry(j, True)
            income.append(("Ferry fee", fee))
            done = {"MRO input": f"Aircraft positioned to the maintenance provider at {arrival} for {j['client']}",
                    "Ferry to storage": f"Aircraft placed into storage at {arrival} for {j['client']}",
                    "Lease return": f"Aircraft returned to {j['client']} at {arrival}",
                    }.get(j.get("kind"), f"Aircraft delivered to {j['client']} at {arrival}")
            notes.append(f"{done}; ferry fee ${fee:,.0f} invoiced.")
        occ = self.safety_roll(f, None if manual else summ, simulated)
        if occ:
            notes.append(occ["text"])
            if occ["severity"] != "occurrence":
                notes.append(occ["finding"])
        rec = dict(f)
        rec.update(occurrence=occ, simulated=simulated, status="Filed", arrival=arrival, diverted=diverted, block_min=round(block_min, 1), fuel_burn=int(fuel_burn), dist_nm=int(dist),
                   touchdown_vs=touchdown_vs, max_g=max_g, score=score, notes=notes, manual=manual, filed=self.s["clock"],
                   income=money(sum(a for _, a in income)), costs=money(sum(a for _, a in costs)), max_alt=None if manual else summ.get("max_alt"),
                   landing_desc=self._landing_desc(touchdown_vs), landing=None if manual else dict(
                       vs=touchdown_vs, g=summ.get("touchdown_g"), ias=summ.get("td_ias"), pitch=summ.get("td_pitch"), bank=summ.get("td_bank"),
                       xwind=summ.get("td_xwind"), hdwind=summ.get("td_hdwind"), flare_vs=summ.get("flare_vs"), flare_ias=summ.get("flare_ias"),
                       bounces=summ.get("bounces", 0), tdz=summ.get("tdz"), gates=summ.get("stability"), vref=summ.get("vref")))
        self.s["flights"].insert(0, rec)
        self.s["flights"] = self.s["flights"][:800]
        self.store_pirep(f["id"], dict(record=rec, telemetry={k: v for k, v in (summ or {}).items() if k != "last"}))
        st = self.s["stats"]
        st["flights"] += 1; st["hours"] = round(st["hours"] + block_hrs, 1); st["nm"] = round(st["nm"] + dist)
        if ac["cat"] == "Widebody":
            self.award("widebody")
        if (f.get("perf") or {}).get("takeoff") and 0 <= (f["perf"]["takeoff"].get("margin") or 9999) < 1000:
            self.award("short_field")
        if f["kind"] == "acmi" and self.contract(f["contract_id"])["hours_month"] >= self.contract(f["contract_id"])["min_hours"]:
            self.award("acmi_month")
        self.check_achievements()
        was_tracked = bool(self.s.get("active_flight")) and self.s["active_flight"]["id"] == f["id"]
        self.s["dispatched"] = [x for x in self.s["dispatched"] if x["id"] != f["id"]]
        if was_tracked or not self.s["dispatched"]:
            # only move the simulator link if the flight it was following has been filed
            self.s["active_flight"] = self.s["dispatched"][0] if self.s["dispatched"] else None
        if advance_clock:
            self.advance(minutes=int(block_min) + 45 + f["delay_min"])
        self.save()
        return rec

    @staticmethod
    def _landing_desc(vs):
        if vs is None:
            return "n/a"
        return "Greaser" if vs > -60 else "Smooth" if vs > -180 else "Normal" if vs > -300 else "Firm" if vs > -450 else "Hard" if vs > -700 else "Very hard"

    # ================================================================ finance
    def take_loan(self, amount):
        amount = float(amount)
        fleet_val = sum(a["value"] for a in self.s["fleet"] if a["owned"])
        cap = max(2_000_000, fleet_val * 0.6) - sum(l["balance"] for l in self.s["loans"])
        if amount <= 0 or amount > cap:
            raise GameError(f"Bank will extend up to ${max(0, cap):,.0f} against owned fleet value.")
        apr, months = 0.075, 60
        r = apr / 12
        pay = amount * r / (1 - (1 + r) ** -months)
        self.s["loans"].append(dict(id=self.nid("loan"), principal=money(amount), balance=amount, apr=apr, months_left=months, payment=money(pay), opened=self.s["clock"]))
        self.post("Loan", "Term loan drawdown (7.5% APR, 60 months)", amount)
        self.save()

    def repay_loan(self, loan_id):
        l = next((x for x in self.s["loans"] if x["id"] == loan_id), None)
        if not l:
            raise GameError("Loan not found.")
        if self.s["cash"] < l["balance"]:
            raise GameError("Insufficient funds to settle the loan.")
        self.post("Loan", f"Early settlement loan #{l['id']}", -l["balance"])
        self.s["loans"].remove(l)
        self.save()

    def statements(self):
        """Income statement by month/category and a balance sheet."""
        months = {}
        for l in self.s["ledger"]:
            m = l["date"][:7]
            if l["category"] in ("Capital", "Loan", "Lease deposit", "Aircraft purchase", "Aircraft sale"):
                continue
            months.setdefault(m, {})
            months[m][l["category"]] = months[m].get(l["category"], 0) + l["amount"]
        inc = [dict(month=m, lines=sorted(v.items(), key=lambda x: -abs(x[1])), net=sum(v.values())) for m, v in sorted(months.items(), reverse=True)]
        fleet_val = sum(a["value"] for a in self.s["fleet"] if a["owned"])
        deposits = sum(a.get("deposit", 0) for a in self.s["fleet"] if not a["owned"])
        loans = sum(l["balance"] for l in self.s["loans"])
        bs = dict(cash=money(self.s["cash"]), fleet=money(fleet_val), deposits=money(deposits), loans=money(loans),
                  equity=money(self.s["cash"] + fleet_val + deposits - loans))
        util = {}
        for f in self.s["flights"]:
            if f.get("aircraft_id"):
                util.setdefault(f["filed"][:7], {}).setdefault(f["reg"], 0)
                util[f["filed"][:7]][f["reg"]] += f["block_min"] / 60
        return dict(income=inc[:12], balance=bs, utilisation=util)

    # ================================================================ time
    def advance(self, days=0, minutes=0):
        self.advance_to(self.now() + timedelta(days=days, minutes=minutes))

    def advance_to(self, target):
        if getattr(self, "_advancing", False):
            # a sector filing itself inside an advance must not re-enter the loop;
            # the outer pass is already walking the clock to at least this point
            self._advance_to = max(getattr(self, "_advance_to", target), target)
            return
        self._advancing, self._advance_to = True, target
        try:
            cur = self.now()
            while cur < target:
                cur = min(target, (cur + timedelta(days=1)).replace(hour=0, minute=0))
                self.s["clock"] = iso(cur)
                self._settle_crew_flights()
                if cur.strftime("%Y-%m-%d") != self.s["last_day"]:
                    self._daily()
                    self.s["last_day"] = cur.strftime("%Y-%m-%d")
                if cur.strftime("%Y-%m") != self.s["last_month"]:
                    self._monthly()
                    self.s["last_month"] = cur.strftime("%Y-%m")
                target = max(target, self._advance_to)
            self.s["clock"] = iso(target)
            self._settle_crew_flights()
        finally:
            self._advancing = False
        self.save()

    def _daily(self):
        now = self.now()
        yday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        for j in self.s["ferry_board"]:
            if j["status"] == "Accepted" and now > parse(j["deadline"]):
                self._finish_ferry(j, False, "delivery window missed")
        self.s["ferry_board"] = [j for j in self.s["ferry_board"] if not (j["status"] in ("Completed", "Cancelled") and (now - parse(j["accepted"] or self.s["clock"])).days > 60)]
        if now.weekday() == 0:
            self.refresh_market()
            self.refresh_hire_pool()
        self._settle_invoices()
        self._settle_area_applications()
        self._settle_type_applications()
        self._settle_deliveries()
        self.refresh_charter()
        self.check_objectives()
        for j in self.s["charter_jobs"]:
            if j["status"] == "Booked" and now > parse(j["depart"]) + timedelta(hours=6):
                j["status"] = "Missed"
                self.post("Charter", f"Compensation to {j['broker']} — trip not operated", -j["fee"] * 0.35, ref=j["id"])
                self.rep(-4, f"charter for {j['client'].lower()} not operated")
                self.mail(j["broker"], f"Trip not operated — {j['origin']} to {j['destination']}",
                          "The aircraft did not arrive and the client was moved to another operator. "
                          "We have deducted a cancellation fee and will think carefully before offering you work again.",
                          action="charter", pin=True)
        for j in self.s["cargo_board"]:
            if j["status"] == "Accepted" and now > parse(j["deadline"]):
                self._finish_cargo(j, False, "the pairing was not completed within the roster window")
        self.s["cargo_board"] = [j for j in self.s["cargo_board"] if j["status"] == "Open" or (j.get("accepted") and (now - parse(j["accepted"])).days < 45)]
        self.refresh_ferry_board()
        self.refresh_cargo_board()
        self.refresh_tenders()
        for j in self.s["ferry_board"]:
            if j["status"] == "Accepted":
                just = [d for d in j["docs"] if not d.get("notified") and parse(d["ready"]) <= now]
                for d in just:
                    d["notified"] = True
                if just:
                    left = [d for d in j["docs"] if parse(d["ready"]) > now]
                    self.mail("Permit office", f"Job #{j['id']}: {', '.join(d['name'].split(' — ')[0].split(' (')[0] for d in just)} received",
                              ("All documents are now in hand; the leg can be released." if not left else f"Still outstanding: {', '.join(d['name'] for d in left)} (latest {max(d['ready'] for d in left)[:10]})."), action="ferry" if not left else None, pin=not left)
        for a in self.s["fleet"]:
            if a["status"] == "Maintenance" and a["mx_until"] and now >= parse(a["mx_until"]):
                why = a.get("mx_reason") or "maintenance"
                a["status"], a["mx_until"], a["mx_reason"] = a.get("prev_status", "Available"), None, None
                self.notice(f"{a['reg']} released to service.")
                self.mail("Maintenance control", f"{a['reg']} released to service", f"{why} complete. Aircraft serviceable at {a['location']}.", action="fleet")
        for p in self.s["pilots"]:
            if p["status"] in ("Training", "Medical") and p["training_until"] and now >= parse(p["training_until"]):
                if p["status"] == "Medical":
                    self.mail("Crew medical", f"{p['rank']} {p['name']} returned to flying duties", "Medical clearance received and recurrent training complete.", action="crew")
                p["status"], p["training_until"] = "Available", None
        sf = self.s["safety"]
        if sf.get("grounded_until") and now >= parse(sf["grounded_until"]):
            sf["grounded_until"] = None
            self.mail("Civil aviation authority", "Operations approval restored", "The post-accident audit is complete and your air operator certificate is restored to full effect. Corrective actions remain subject to follow-up.", action="safety")
        inv = sf.get("investigation")
        if inv and now >= parse(inv["due"]):
            o = next((x for x in sf["occurrences"] if x["id"] == inv["occurrence_id"]), None)
            sf["investigation"] = None
            if o:
                o["report"] = True
                self.mail("Accident investigation authority", f"Final report published — {o['flight']} {o['reg']}",
                          f"{o['text']} {o['finding']} Safety recommendations have been issued to the operator.", action="safety", pin=True)
                if not o.get("causes"):
                    self.rep(2, "investigation found no operator causal factors")
        for c in self.s["contracts"]:
            if c["status"] == "Active":
                c["kpi"]["legs_scheduled"] += len(self.rotation(c["id"], yday))
            if c["status"] == "Pending start" and now >= parse(c["start"]):
                a = next((x for x in self.s["fleet"] if x["id"] == c["aircraft_id"]), None)
                if a and a["location"] == c["hub"] and a["status"] != "Maintenance":
                    c["status"] = "Active"
                    self.notice(f"Contract #{c['id']} with {c['customer']} is now active. Daily rotations available in Dispatch.")
                elif (now - parse(c["start"])).days > 7:
                    self.post("Penalty", f"Non-delivery penalty {c['customer']} contract #{c['id']}", -c["rate"] * c["min_hours"] * 0.5)
                    self.rep(-8, f"failed to position {c['reg']} for {c['customer']}")
                    self._end_contract(c, "Terminated", "aircraft not positioned by start date")
            if c["status"] == "Active" and now >= parse(c["end"]):
                self._end_contract(c, "Completed", f"{c['months']}-month term complete; {c['hours_total']:.0f} BH flown")
                self.rep(3, f"contract #{c['id']} with {c['customer']} completed")

    def _monthly(self):
        rep_lines, total_in, total_out = [], 0.0, 0.0

        def out(cat, desc, amt):
            nonlocal total_out
            if amt:
                self.post(cat, desc, -amt); total_out += amt; rep_lines.append((desc, -amt))

        def inc(cat, desc, amt):
            nonlocal total_in
            self.post(cat, desc, amt); total_in += amt; rep_lines.append((desc, amt))

        month = (self.now() - timedelta(days=1)).strftime("%B %Y")
        for a in self.s["fleet"]:
            if not a["owned"]:
                out("Lease", f"Monthly lease {a['reg']} ({a['lessor']})", a["lease"])
            out("Insurance", f"Hull & liability insurance {a['reg']}" + (f" (loaded {self.s['safety']['premium_factor']:.2f}x after claims)" if self.s["safety"].get("premium_factor", 1) > 1 else ""),
                a["value"] * 0.009 / 12 * self.s["safety"].get("premium_factor", 1.0))
            a["value"] = money(a["value"] * (1 - 0.045 / 12))
            if self.rng.random() < 0.02 and a["status"] != "Maintenance":
                days = self.rng.randint(3, 10)
                cost = AIRCRAFT[a["type"]]["mx_fh"] * 30
                out("Maintenance", f"Airworthiness Directive compliance {a['reg']}", cost)
                self._ground(a, days, "AD compliance work")
                self.notice(f"An Airworthiness Directive grounds {a['reg']} for {days} days.")
                self.mail("Civil aviation authority", f"Airworthiness Directive — {a['name']}", f"Mandatory inspection applies to {a['reg']}. The aircraft is grounded for {days} days; compliance cost ${cost:,.0f}.", action="fleet", pin=True)
        for p in self.s["pilots"]:
            hired = p.get("hired")
            if hired and self.now().month == parse(hired).month and (self.now() - parse(hired)).days > 300:
                p["salary"] = money(p["salary"] * 1.03)
                self.notice(f"Seniority increment for {p['rank']} {p['name']} — now ${p['salary']:,}/month.")
            out("Crew", f"Salary {p['rank']} {p['name']}", p["salary"])
        for role, n in self.s["staff"].items():
            out("Crew", f"Salaries {STAFF[role]['title']} x{n}", STAFF[role]["salary"] * n)
        out("Overheads", "Office, hangar space, ops software and AOC compliance", 24000 + 7500 * len(self.s["fleet"]))
        for c in self.s["contracts"]:
            if c["status"] != "Active":
                continue
            util = c["hours_month"] / c["min_hours"]
            short = max(0.0, c["min_hours"] - c["hours_month"])
            if short > 0:
                self.invoice(c["customer"], f"Minimum guarantee true-up ({short:.0f} BH)", short * c["rate"], ref=c["id"], kind="acmi")
                total_in += short * c["rate"]
                rep_lines.append((f"Minimum guarantee true-up {c['customer']} ({short:.0f} BH) — invoiced", money(short * c["rate"])))
                c["revenue_total"] += short * c["rate"]
            k = c["kpi"]
            completion = k["legs_flown"] / k["legs_scheduled"] if k["legs_scheduled"] else 1.0
            otp = 1 - k["late"] / k["legs_flown"] if k["legs_flown"] else 1.0
            k["satisfaction"] = round(max(0, min(100, 40 + 30 * min(1, util / 0.5) + 15 * completion + 15 * otp)), 1)
            if util < 0.10:
                c["strikes"] += 1
                self.notice(f"{c['customer']} has issued a non-performance notice on contract #{c['id']} ({c['hours_month']:.0f} of {c['min_hours']} BH flown).")
                self.mail(c["customer"], f"Notice of non-performance — agreement #{c['id']}", f"Only {c['hours_month']:.0f} of the {c['min_hours']} guaranteed block hours were operated in {month}. A second notice will terminate the agreement.", action="contracts", pin=True)
                if c["strikes"] >= 2:
                    out("Penalty", f"Termination for non-performance — {c['customer']} #{c['id']}", c["rate"] * c["min_hours"] * 0.5)
                    self.rep(-10, f"contract #{c['id']} terminated by {c['customer']}")
                    self._end_contract(c, "Terminated", "non-performance")
            elif util >= 0.5:
                self.rep(2, f"strong utilisation on {c['customer']} contract")
            c["history"].append(dict(month=month, hours=round(c["hours_month"], 1), legs=c["legs_month"], util=round(util * 100), otp=round(otp * 100), completion=round(completion * 100), satisfaction=k["satisfaction"]))
            if k["legs_flown"] >= 20 and k["late"] == 0:
                self.award("otp")
            c["hours_month"], c["legs_month"], c["months_billed"] = 0.0, 0, c["months_billed"] + 1
            k["legs_scheduled"], k["legs_flown"], k["late"], k["delay_min"] = 0, 0, 0, 0
        for l in list(self.s["loans"]):
            interest = l["balance"] * l["apr"] / 12
            principal = min(l["balance"], l["payment"] - interest)
            l["balance"] -= principal; l["months_left"] -= 1
            out("Loan", f"Loan #{l['id']} instalment (interest ${interest:,.0f})", interest + principal)
            if l["balance"] <= 1:
                self.s["loans"].remove(l)
        self._snapshot(month, total_in, total_out)
        self.s["month_reports"].insert(0, dict(month=month, income=money(total_in), expenses=money(total_out), net=money(total_in - total_out),
                                               cash=money(self.s["cash"]), lines=[(d, money(a)) for d, a in rep_lines]))
        self.s["month_reports"] = self.s["month_reports"][:36]
        self.notice(f"Month-end close for {month}: net ${money(total_in - total_out):,}.")
        self.mail("Finance", f"Month-end close — {month}", f"Income ${money(total_in):,}, fixed costs ${money(total_out):,}, net ${money(total_in - total_out):,}. Cash ${money(self.s['cash']):,}.", action="statements")
        if total_in - total_out > 0:
            self.award("profit")
        self.check_achievements()
        pf = self.s["safety"].get("premium_factor", 1.0)
        if pf > 1.0:
            self.s["safety"]["premium_factor"] = round(max(1.0, pf - 0.02), 2)
        if self.s["cash"] < -2_000_000:
            self.notice("WARNING: the bank has flagged the account. Sustained negative cash will lead to insolvency.")

    def _snapshot(self, month, month_in, month_out):
        """One data point per month for the analytics charts."""
        s = self.s
        prev_flights = s["snapshots"][-1]["flights"] if s["snapshots"] else 0
        prev_hours = s["snapshots"][-1]["hours"] if s["snapshots"] else 0.0
        rev = dict(ferry=0.0, cargo=0.0, acmi=0.0, charter=0.0, other=0.0)
        cost = {}
        key = (self.now() - timedelta(days=1)).strftime("%Y-%m")
        for l in s["ledger"]:
            if l["date"][:7] != key:
                continue
            c, a = l["category"], l["amount"]
            if a > 0:
                if c == "Ferry revenue":
                    rev["ferry"] += a
                elif c == "Cargo flying":
                    rev["cargo"] += a
                elif c == "ACMI revenue":
                    rev["acmi"] += a
                elif c == "Charter revenue":
                    rev["charter"] += a
                elif c == "Flight revenue":
                    rev["other"] += a
                elif c not in ("Capital", "Loan", "Lease deposit", "Aircraft sale", "Insurance claim"):
                    rev["other"] += a
            elif c not in ("Capital", "Loan", "Lease deposit", "Aircraft purchase"):
                cost[c] = cost.get(c, 0) + -a
        fleet_val = sum(a["value"] for a in s["fleet"] if a["owned"])
        deposits = sum(a.get("deposit", 0) for a in s["fleet"] if not a["owned"])
        loans = sum(l["balance"] for l in s["loans"])
        util = {}
        for f in s["flights"]:
            if f["filed"][:7] == key and f.get("reg"):
                util[f["reg"]] = round(util.get(f["reg"], 0) + f["block_min"] / 60, 1)
        income_total = sum(rev.values())
        expense_total = sum(cost.values())
        s["snapshots"].append(dict(month=key, label=month, cash=money(s["cash"]), equity=money(s["cash"] + fleet_val + deposits - loans),
                                   fleet=len(s["fleet"]), fleet_value=money(fleet_val), pilots=len(s["pilots"]), staff=sum(s["staff"].values()),
                                   reputation=s["company"]["reputation"], flights=s["stats"]["flights"], hours=round(s["stats"]["hours"], 1),
                                   month_flights=s["stats"]["flights"] - prev_flights, month_hours=round(s["stats"]["hours"] - prev_hours, 1),
                                   revenue={k: money(v) for k, v in rev.items()}, costs={k: money(v) for k, v in cost.items()},
                                   income=money(income_total), expenses=money(expense_total), net=money(income_total - expense_total),
                                   fixed_costs=money(month_out),
                                   contracts=len([c for c in s["contracts"] if c["status"] == "Active"]), utilisation=util,
                                   occurrences=len([o for o in s["safety"]["occurrences"] if o["date"][:7] == key]),
                                   since_incident=s["safety"].get("since_incident", 0)))
        s["snapshots"] = s["snapshots"][-240:]
        if self.now().month == 1 and len(s["snapshots"]) >= 2:
            self._annual_report()

    def _annual_report(self):
        year = (self.now() - timedelta(days=1)).year
        snaps = [x for x in self.s["snapshots"] if x["month"].startswith(str(year))]
        if not snaps:
            return
        flights = [f for f in self.s["flights"] if f["filed"][:4] == str(year)]
        rev = {}
        for sn in snaps:                       # whatever lines of business the year contained
            for k, v in (sn.get("revenue") or {}).items():
                rev[k] = rev.get(k, 0) + v
        best = max(snaps, key=lambda x: x["net"])
        worst = min(snaps, key=lambda x: x["net"])
        occ = [o for o in self.s["safety"]["occurrences"] if o["date"][:4] == str(year)]
        rep = dict(year=year, closing_cash=snaps[-1]["cash"], closing_equity=snaps[-1]["equity"], fleet=snaps[-1]["fleet"],
                   pilots=snaps[-1]["pilots"], reputation=snaps[-1]["reputation"], revenue=rev,
                   income=sum(x["income"] for x in snaps), expenses=sum(x["expenses"] for x in snaps),
                   net=sum(x["net"] for x in snaps), sectors=len(flights), hours=round(sum(f["block_min"] for f in flights) / 60, 1),
                   nm=sum(f["dist_nm"] for f in flights), best=dict(month=best["label"], net=best["net"]), worst=dict(month=worst["label"], net=worst["net"]),
                   avg_score=round(sum(f["score"] for f in flights) / len(flights), 1) if flights else 0,
                   occurrences=len(occ), accidents=len([o for o in occ if o["severity"] == "accident"]),
                   customers=sorted({f.get("customer") for f in flights if f.get("customer")}))
        self.s["years"].insert(0, rep)
        self.s["years"] = self.s["years"][:30]
        self.event("company", f"{year} results published", f"Revenue ${rep['income']:,}, net ${rep['net']:,}, {rep['sectors']} sectors and {rep['hours']:,.0f} block hours flown.")
        self.mail("Finance", f"Annual report — {year}", f"Net result ${rep['net']:,} on income of ${rep['income']:,}. {rep['sectors']} sectors, {rep['hours']:,.0f} block hours, "
                  f"fleet of {rep['fleet']}, reputation {rep['reputation']:.1f}. Best month {rep['best']['month']} (${rep['best']['net']:,}).", action="analytics", pin=True)

    def analytics(self):
        s = self.s
        cur = dict(month=self.now().strftime("%Y-%m"), label=self.now().strftime("%B %Y") + " (in progress)",
                   cash=money(s["cash"]), equity=money(s["cash"] + sum(a["value"] for a in s["fleet"] if a["owned"])
                                                       + sum(a.get("deposit", 0) for a in s["fleet"] if not a["owned"])
                                                       - sum(l["balance"] for l in s["loans"])),
                   fleet=len(s["fleet"]), pilots=len(s["pilots"]), reputation=s["company"]["reputation"],
                   flights=s["stats"]["flights"], hours=round(s["stats"]["hours"], 1))
        landings = [dict(date=f["filed"], vs=f["touchdown_vs"], type=f["type"], score=f["score"], flight=f["flight_number"])
                    for f in reversed(s["flights"]) if f.get("touchdown_vs") is not None and not f.get("manual")]
        by_ac = {}
        for f in s["flights"]:
            if not f.get("aircraft_id"):
                continue
            r = by_ac.setdefault(f["reg"], dict(reg=f["reg"], type=f["type"], sectors=0, hours=0.0, revenue=0, costs=0))
            r["sectors"] += 1; r["hours"] = round(r["hours"] + f["block_min"] / 60, 1); r["revenue"] += f["income"]; r["costs"] += f["costs"]
        for a in s["fleet"]:
            r = by_ac.setdefault(a["reg"], dict(reg=a["reg"], type=a["type"], sectors=0, hours=0.0, revenue=0, costs=0))
            r["owned"] = a["owned"]; r["lease"] = a["lease"]; r["value"] = a["value"]; r["in_fleet"] = True
        customers = {}
        for f in s["flights"]:
            c = f.get("customer")
            if not c:
                continue
            x = customers.setdefault(c, dict(name=c, sectors=0, revenue=0, hours=0.0))
            x["sectors"] += 1; x["revenue"] += f["income"]; x["hours"] = round(x["hours"] + f["block_min"] / 60, 1)
        for c in s["contracts"]:
            x = customers.setdefault(c["customer"], dict(name=c["customer"], sectors=0, revenue=0, hours=0.0))
            x["contract_revenue"] = x.get("contract_revenue", 0) + money(c["revenue_total"])
            x["satisfaction"] = c["kpi"]["satisfaction"]
        return dict(snapshots=s["snapshots"], current=cur, years=s["years"], timeline=s["timeline"][:200],
                    landings=landings[-300:], aircraft=sorted(by_ac.values(), key=lambda x: -x["hours"]),
                    customers=sorted(customers.values(), key=lambda x: -(x["revenue"] + x.get("contract_revenue", 0)))[:20],
                    pilots=[dict(name=p["name"], rank=p["rank"], hours=p["hours"], company_hours=p.get("company_hours", 0)) for p in s["pilots"]],
                    operator_logos=OPERATOR_LOGOS)

    # ================================================================ view
    def view(self):
        base = dict(aircraft_types={t: dict(a, tofl=perf.PERF.get(t, {}).get("tofl"),
                                            ldfl=perf.PERF.get(t, {}).get("ldfl"))
                                    for t, a in AIRCRAFT.items()},
                    staff_def=STAFF, a_check_fh=A_CHECK_FH, etops_nm=ETOPS_NM, engine_oem=ENGINE_OEM,
                    difficulties={k: dict(label=v["label"], desc=v["desc"]) for k, v in DIFFICULTY.items()}, achievement_defs=ACHIEVEMENTS)
        fams = {}
        for t, a in AIRCRAFT.items():
            f = fams.setdefault(a["family"], dict(family=a["family"], cat=a["cat"], mfr=a["mfr"], types=[], names=[]))
            f["types"].append(t)
            f["names"].append(a["name"])
        base["families"] = fams
        base["type_bands"] = TYPE_APPLICATION
        if not self.state:
            base["company"] = None
            return base
        s = self.s
        v = {k: s[k] for k in ("company", "clock", "cash", "fleet", "market", "pilots", "hire_pool", "ferry_board", "acmi_tenders", "contracts",
                                "active_flight", "notices", "month_reports", "loans", "stats", "staff", "inbox", "achievements", "cargo_board")}
        v["ledger"] = s["ledger"][-300:][::-1]
        v["flights"] = s["flights"][:200]
        v["company"] = dict(v["company"], safety_enabled=s["safety"].get("enabled", True))
        v["upgrades"] = {p["id"]: self.upgrade_check(p) for p in s["pilots"] if p["rank"] == "FO"}
        v["career"] = self.career_view()
        v["aoc_areas"] = self.aoc_areas()
        v["aoc_pending"] = self.area_pending()
        v["regions"] = REGIONS
        v["area_costs"] = {r: self.area_cost(r) for r in REGIONS if r not in self.aoc_areas()}
        v["aoc_types"] = self.aoc_types()
        v["aoc_types_pending"] = self.type_pending()
        v["type_costs"] = ({f: self.type_cost(f) for f in sorted({a["family"] for a in AIRCRAFT.values()})
                            if f not in self.aoc_types()} if self.restricted_by_type() else {})
        # the crew's sector is settled the moment they push back, so the result must not
        # travel to the browser with it: strip it out and send the progress instead
        strip = lambda f: {k: val for k, val in f.items() if k != "crew_flight"} if f else f
        v["dispatched"] = [strip(f) for f in s["dispatched"]]
        v["active_flight"] = strip(v["active_flight"])
        v["airborne"] = self.crew_airborne()
        v["tracked_id"] = (self.tracked() or {}).get("id")
        v["charter_board"] = [q for q in s["charter_board"] if q["status"] == "Open"]
        v["charter_history"] = [q for q in s["charter_board"] if q["status"] in ("Won", "Lost")][-12:]
        v["charter_jobs"] = [dict(j, legs=self.charter_legs(j), client_legs=self.client_legs(j),
                                  done=j.get("done", 0))
                             for j in s["charter_jobs"] if j["status"] in ("Booked", "Flying")]
        v["charter_done"] = [j for j in s["charter_jobs"] if j["status"] in ("Completed", "Missed")][-10:]
        v["receivables"] = sorted([r for r in s["receivables"] if not r["paid"]], key=lambda r: r["due"])
        v["outstanding"] = money(self.outstanding())
        v["terms_days"] = self.diff().get("terms", 30)
        v["currency"] = {p["id"]: {f: dict(zip(("current", "landings"), self.is_current(p, f))) for f in p["ratings"]} for p in s["pilots"]}
        v["recency_days"] = RECENCY_DAYS
        v["recency_needed"] = RECENCY_NEEDED
        v["operator_logos"] = OPERATOR_LOGOS
        v["family_types"] = FAMILY_TYPES
        v["currencies"] = CURRENCIES
        v["substitutes"] = {t: substitutes(t) for t in AIRCRAFT}
        v["family_covers"] = FAMILY_COVERS
        v["logo_tone"] = {k: t["tone"] for k, t in LOGO_TONE.items()}
        v["cabin_assigned"] = self._cabin_assigned()
        v["dispatchers_needed"] = max(1, math.ceil(len(s["fleet"]) / STAFF["dispatcher"]["per_aircraft"]))
        v["mx_needed"] = math.ceil(len(s["fleet"]) / STAFF["mx_controller"]["per_aircraft"])
        v["season"] = dict(pax=season(self.now().month, False), cargo=season(self.now().month, True))
        v.update(base)
        return v
