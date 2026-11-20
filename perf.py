"""Runway performance and weight & balance.

Simplified but physically-shaped models: takeoff and landing field lengths scale with
weight squared over air density and thrust/lift terms, with corrections for altitude,
temperature, wind, slope, runway state and inoperative equipment. Numbers are tuned to
sit close to published field lengths for each type at MTOW, sea level, ISA.
"""
import json
import math
import os
import sys

HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
_RW_PATH = os.path.join(HERE, "runways.json")
RUNWAYS = {}
if os.path.exists(_RW_PATH):
    with open(_RW_PATH, encoding="utf-8") as _fh:
        RUNWAYS = json.load(_fh)

LB_PER_KG = 2.20462
FUEL_LB_PER_USG = 6.7

# Per-type performance and loading reference.
# tofl/ldfl: field length required at MTOW / MLW, sea level, ISA, dry, flaps normal (ft)
# oew_kg: operating empty weight; mlw_kg: max landing; mzfw_kg: max zero fuel
# fuel_kg: usable fuel capacity; pax_kg: weight per passenger incl. baggage
# arm_*: simplified balance arms in % MAC contribution
PERF = {
    "AT76": dict(tofl=4380, ldfl=3200, oew_kg=13500, mlw_kg=22350, mzfw_kg=21000, fuel_kg=5000, vref=113, cat="Turboprop"),
    "DH8D": dict(tofl=4675, ldfl=4230, oew_kg=17820, mlw_kg=28009, mzfw_kg=26308, fuel_kg=5318, vref=126, cat="Turboprop"),
    "CRJ9": dict(tofl=6300, ldfl=5100, oew_kg=21845, mlw_kg=34065, mzfw_kg=31750, fuel_kg=8888, vref=134, cat="Regional"),
    "E190": dict(tofl=6890, ldfl=4380, oew_kg=27837, mlw_kg=45800, mzfw_kg=43000, fuel_kg=12971, vref=132, cat="Regional"),
    "E195": dict(tofl=7200, ldfl=4600, oew_kg=28970, mlw_kg=45800, mzfw_kg=43000, fuel_kg=12971, vref=136, cat="Regional"),
    "A319": dict(tofl=6100, ldfl=4600, oew_kg=40800, mlw_kg=62500, mzfw_kg=58500, fuel_kg=18730, vref=131, cat="Narrowbody"),
    "A320": dict(tofl=6900, ldfl=4900, oew_kg=42600, mlw_kg=66000, mzfw_kg=62500, fuel_kg=18730, vref=138, cat="Narrowbody"),
    "A20N": dict(tofl=6500, ldfl=4800, oew_kg=44300, mlw_kg=67400, mzfw_kg=64300, fuel_kg=19000, vref=136, cat="Narrowbody"),
    "A321": dict(tofl=7700, ldfl=5300, oew_kg=48500, mlw_kg=77800, mzfw_kg=73800, fuel_kg=18730, vref=142, cat="Narrowbody"),
    "A21N": dict(tofl=7400, ldfl=5300, oew_kg=50100, mlw_kg=79200, mzfw_kg=75600, fuel_kg=25752, vref=142, cat="Narrowbody"),
    "B737": dict(tofl=6700, ldfl=4700, oew_kg=38147, mlw_kg=58604, mzfw_kg=54657, fuel_kg=20894, vref=134, cat="Narrowbody"),
    "B738": dict(tofl=7500, ldfl=5100, oew_kg=41413, mlw_kg=66361, mzfw_kg=62732, fuel_kg=20894, vref=142, cat="Narrowbody"),
    "B739": dict(tofl=8000, ldfl=5400, oew_kg=44676, mlw_kg=71350, mzfw_kg=67494, fuel_kg=20894, vref=145, cat="Narrowbody"),
    "B38M": dict(tofl=7000, ldfl=5000, oew_kg=45070, mlw_kg=69308, mzfw_kg=65952, fuel_kg=20826, vref=142, cat="Narrowbody"),
    "B752": dict(tofl=7500, ldfl=5200, oew_kg=57840, mlw_kg=89811, mzfw_kg=83460, fuel_kg=34000, vref=138, cat="Narrowbody"),
    "B763": dict(tofl=8300, ldfl=5600, oew_kg=90011, mlw_kg=145150, mzfw_kg=133810, fuel_kg=73000, vref=145, cat="Widebody"),
    "B76F": dict(tofl=8300, ldfl=5600, oew_kg=86500, mlw_kg=147870, mzfw_kg=140160, fuel_kg=73000, vref=145, cat="Widebody"),
    "A332": dict(tofl=8200, ldfl=5300, oew_kg=120200, mlw_kg=182000, mzfw_kg=170000, fuel_kg=109186, vref=140, cat="Widebody"),
    "A333": dict(tofl=8400, ldfl=5800, oew_kg=124500, mlw_kg=187000, mzfw_kg=175000, fuel_kg=97530, vref=143, cat="Widebody"),
    "A339": dict(tofl=8500, ldfl=5700, oew_kg=132000, mlw_kg=191000, mzfw_kg=181000, fuel_kg=111276, vref=142, cat="Widebody"),
    "A359": dict(tofl=8800, ldfl=6100, oew_kg=142400, mlw_kg=207000, mzfw_kg=195700, fuel_kg=110500, vref=140, cat="Widebody"),
    "B772": dict(tofl=9800, ldfl=5800, oew_kg=138100, mlw_kg=213180, mzfw_kg=199580, fuel_kg=140700, vref=143, cat="Widebody"),
    "B77W": dict(tofl=10500, ldfl=6300, oew_kg=167800, mlw_kg=251290, mzfw_kg=237680, fuel_kg=145540, vref=149, cat="Widebody"),
    "PC12": dict(tofl=2650, ldfl=2200, oew_kg=3061, mlw_kg=4500, mzfw_kg=4100, fuel_kg=1226, vref=85, cat="Turboprop"),
    "BE20": dict(tofl=3300, ldfl=2700, oew_kg=4260, mlw_kg=6577, mzfw_kg=5670, fuel_kg=1650, vref=103, cat="Turboprop"),
    "E55P": dict(tofl=3700, ldfl=2600, oew_kg=5310, mlw_kg=7620, mzfw_kg=6600, fuel_kg=2360, vref=108, cat="Regional"),
    "C25C": dict(tofl=3410, ldfl=2900, oew_kg=4785, mlw_kg=7212, mzfw_kg=6033, fuel_kg=2600, vref=107, cat="Regional"),
    "H25B": dict(tofl=5032, ldfl=3200, oew_kg=7303, mlw_kg=10591, mzfw_kg=8369, fuel_kg=4536, vref=124, cat="Regional"),
    "C56X": dict(tofl=3560, ldfl=3180, oew_kg=5850, mlw_kg=8460, mzfw_kg=6895, fuel_kg=3400, vref=108, cat="Regional"),
    "E545": dict(tofl=4720, ldfl=2170, oew_kg=10700, mlw_kg=16600, mzfw_kg=13200, fuel_kg=7200, vref=110, cat="Regional"),
    "CL35": dict(tofl=4835, ldfl=2360, oew_kg=10900, mlw_kg=16556, mzfw_kg=13154, fuel_kg=6350, vref=112, cat="Regional"),
    "GLF6": dict(tofl=6299, ldfl=3050, oew_kg=24494, mlw_kg=37738, mzfw_kg=28304, fuel_kg=20720, vref=126, cat="Widebody"),
    "GL7T": dict(tofl=5800, ldfl=2237, oew_kg=25990, mlw_kg=40460, mzfw_kg=29800, fuel_kg=22300, vref=120, cat="Widebody"),
    "FA8X": dict(tofl=5880, ldfl=2220, oew_kg=16880, mlw_kg=28030, mzfw_kg=20000, fuel_kg=16090, vref=110, cat="Widebody"),
    "B75F": dict(tofl=8200, ldfl=5100, oew_kg=58400, mlw_kg=95250, mzfw_kg=90000, fuel_kg=33540, vref=138, cat="Narrowbody"),
    "B38F": dict(tofl=7800, ldfl=5000, oew_kg=42000, mlw_kg=66361, mzfw_kg=62732, fuel_kg=20890, vref=141, cat="Narrowbody"),
    "AT7F": dict(tofl=4400, ldfl=3200, oew_kg=13500, mlw_kg=22350, mzfw_kg=21000, fuel_kg=5000, vref=110, cat="Turboprop"),
    "DC3":  dict(tofl=3300, ldfl=3000, oew_kg=7650, mlw_kg=11431, mzfw_kg=10886, fuel_kg=2100, vref=85, cat="Turboprop"),
    "C208": dict(tofl=2420, ldfl=2000, oew_kg=2145, mlw_kg=3969, mzfw_kg=3720, fuel_kg=1010, vref=75, cat="Turboprop"),
    "DHC6": dict(tofl=1500, ldfl=1400, oew_kg=3363, mlw_kg=5579, mzfw_kg=5080, fuel_kg=1150, vref=75, cat="Turboprop"),
    "SF34": dict(tofl=4300, ldfl=3900, oew_kg=8140, mlw_kg=12930, mzfw_kg=11930, fuel_kg=2580, vref=105, cat="Turboprop"),
    "AT43": dict(tofl=3900, ldfl=3500, oew_kg=10285, mlw_kg=18300, mzfw_kg=16700, fuel_kg=4500, vref=100, cat="Turboprop"),
    "CR2F": dict(tofl=6100, ldfl=4900, oew_kg=13740, mlw_kg=21319, mzfw_kg=20412, fuel_kg=6489, vref=135, cat="Regional"),
    "A306": dict(tofl=8400, ldfl=5300, oew_kg=90900, mlw_kg=140000, mzfw_kg=130000, fuel_kg=48000, vref=140, cat="Widebody"),
    "B722": dict(tofl=8600, ldfl=5000, oew_kg=45360, mlw_kg=72600, mzfw_kg=65300, fuel_kg=26000, vref=138, cat="Narrowbody"),
    "E19F": dict(tofl=6900, ldfl=4400, oew_kg=28800, mlw_kg=45800, mzfw_kg=42300, fuel_kg=12970, vref=132, cat="Regional"),
    "E95F": dict(tofl=7300, ldfl=4600, oew_kg=29500, mlw_kg=45800, mzfw_kg=43800, fuel_kg=12970, vref=134, cat="Regional"),
    "A21F": dict(tofl=7800, ldfl=5000, oew_kg=48000, mlw_kg=77800, mzfw_kg=73800, fuel_kg=18730, vref=142, cat="Narrowbody"),
    "A33F": dict(tofl=8900, ldfl=5700, oew_kg=125000, mlw_kg=187000, mzfw_kg=178000, fuel_kg=97530, vref=145, cat="Widebody"),
    "MD11": dict(tofl=10500, ldfl=7000, oew_kg=131000, mlw_kg=222940, mzfw_kg=218000, fuel_kg=117000, vref=155, cat="Widebody"),
    "B77F": dict(tofl=10400, ldfl=6300, oew_kg=144400, mlw_kg=260810, mzfw_kg=248120, fuel_kg=145540, vref=149, cat="Widebody"),
    "B788": dict(tofl=8500, ldfl=5100, oew_kg=119950, mlw_kg=172365, mzfw_kg=161025, fuel_kg=101450, vref=140, cat="Widebody"),
    "B789": dict(tofl=9200, ldfl=5500, oew_kg=128850, mlw_kg=192775, mzfw_kg=181435, fuel_kg=101450, vref=145, cat="Widebody"),
    "B744": dict(tofl=10200, ldfl=6200, oew_kg=178750, mlw_kg=285765, mzfw_kg=256280, fuel_kg=173000, vref=152, cat="Widebody"),
    "B748": dict(tofl=10700, ldfl=6300, oew_kg=197131, mlw_kg=346091, mzfw_kg=329838, fuel_kg=194000, vref=152, cat="Widebody"),
    # Additional passenger-to-freighter conversions (gameplay estimates, not AFM data).
    # The 767-200SF reference values follow the previously discussed Operator addition.
    "B75S": dict(tofl=8300, ldfl=5100, oew_kg=59200, mlw_kg=95250, mzfw_kg=90000, fuel_kg=33540, vref=138, cat="Narrowbody"),  # 757-200SF
    "B762F": dict(tofl=7600, ldfl=5200, oew_kg=78215, mlw_kg=128365, mzfw_kg=117025, fuel_kg=62150, vref=140, cat="Widebody"),  # 767-200SF
    "B762": dict(tofl=7600, ldfl=5200, oew_kg=78215, mlw_kg=128365, mzfw_kg=117025, fuel_kg=62150, vref=140, cat="Widebody"),   # 767-200BDSF (alternate code)
    "B76B": dict(tofl=8500, ldfl=5600, oew_kg=90700, mlw_kg=145150, mzfw_kg=133810, fuel_kg=73000, vref=145, cat="Widebody"),  # 767-300BCF
    "B76D": dict(tofl=8500, ldfl=5600, oew_kg=90200, mlw_kg=145150, mzfw_kg=133810, fuel_kg=73000, vref=145, cat="Widebody"),  # 767-300BDSF
    "B74B": dict(tofl=10300, ldfl=6200, oew_kg=181000, mlw_kg=285765, mzfw_kg=256280, fuel_kg=173000, vref=152, cat="Widebody"),  # 747-400BCF
}

# Balance model: CG expressed in % MAC. Envelope is 15–35% MAC for jets, a little wider
# for turboprops. Arms are the CG each load element pulls the aircraft towards.
BALANCE = dict(oew=24.0, fwd_hold=-10.0, aft_hold=70.0, cabin_fwd=0.0, cabin_aft=55.0, fuel=26.0, env=(15.0, 35.0))
BALANCE_TP = dict(env=(12.0, 38.0))
# Empty-aircraft CG by type: freighters and aircraft with heavy tails sit further aft
OEW_ARM = {"MD11": 35.5, "DC3": 22.0, "C208": 20.0, "DHC6": 20.0, "SF34": 24.0, "AT43": 26.0, "H25B": 27.0, "B75F": 27.0, "B38F": 30.0, "AT7F": 28.0, "PC12": 24.0, "BE20": 24.0, "E55P": 26.0, "C25C": 26.0, "C56X": 27.0,
           "E545": 29.0, "CL35": 29.0, "GLF6": 33.0, "GL7T": 34.0, "FA8X": 32.0, "CR2F": 33.0, "A306": 33.0, "B722": 27.5, "E19F": 30.0, "E95F": 30.5, "A21F": 30.0, "A33F": 35.0, "B76F": 37.0, "B77F": 36.5, "B744": 36.0, 
           "B748": 36.0, "CRJ9": 33.0, "E190": 30.0, "E195": 30.0, "AT76": 28.0, "DH8D": 28.0, "B752": 27.0, "B75S": 27.5, "B762F": 36.0, "B762": 36.0, "B76B": 37.0, "B76D": 37.0, "B74B": 36.0}

def runways(icao):
    return RUNWAYS.get((icao or "").upper(), [])


_LONGEST = {}


def longest(icao):
    """Longest runway, cached: this is asked millions of times during route planning."""
    key = (icao or "").upper()
    if key not in _LONGEST:
        r = runways(key)
        _LONGEST[key] = r[0]["l"] if r else None
    return _LONGEST[key]


def _dens_factor(elev_ft, oat_c):
    """Density-altitude multiplier on field length."""
    isa = 15 - 1.98 * elev_ft / 1000
    da = elev_ft + 118.8 * (oat_c - isa)
    return (1 + da / 1000 * 0.07), int(da)


def wind_components(rw_hdg, wind_dir, wind_kt):
    rel = math.radians(((wind_dir or 0) - rw_hdg + 540) % 360 - 180)
    return round(wind_kt * math.cos(rel), 1), round(wind_kt * math.sin(rel), 1)


def takeoff(type_code, weight_kg, icao, elev_ft=0, oat_c=15, wind_dir=None, wind_kt=0,
            surface_state="dry", restrictions=None, runway=None):
    """Return the takeoff analysis for the best (or given) runway."""
    p = PERF.get(type_code)
    if not p:
        return None
    restrictions = restrictions or {}
    rws = [runway] if runway else runways(icao)
    if not rws:
        return dict(ok=None, reason="No runway data for this airport.")
    mtow = MTOW.get(type_code)
    ratio = (weight_kg / mtow) ** 2 if mtow else 1.0
    dens, da = _dens_factor(elev_ft, oat_c)
    state = {"dry": 1.0, "wet": 1.15, "contaminated": 1.35}.get(surface_state, 1.0)
    best = None
    for rw in rws:
        surf = 1.0 if rw["s"] == "H" else 1.20
        for e in rw["e"]:
            head, cross = wind_components(e["hdg"], wind_dir, wind_kt) if wind_kt else (0.0, 0.0)
            wind_f = 1 - 0.006 * head if head > 0 else 1 + 0.02 * abs(head)
            req = p["tofl"] * max(0.35, ratio) * dens * state * surf * wind_f
            asda = rw["l"] - (e.get("disp", 0) if False else 0)     # displaced threshold does not reduce TODA
            margin = asda - req
            cand = dict(runway=e["id"], length=rw["l"], surface="Hard" if rw["s"] == "H" else "Unpaved", lit=rw["lit"],
                        required=int(req), available=asda, margin=int(margin), headwind=head, crosswind=cross,
                        density_alt=da, ok=margin >= 0)
            if best is None or cand["margin"] > best["margin"]:
                best = cand
    notes = []
    if best["surface"] == "Unpaved":
        notes.append("Unpaved runway: 20% distance penalty and a jet-blast/FOD risk.")
    if abs(best["crosswind"]) > 30:
        notes.append(f"Crosswind {abs(best['crosswind'])} kt exceeds most demonstrated limits.")
    if not best["lit"]:
        notes.append("Runway unlit: day operations only.")
    if restrictions.get("day_only"):
        notes.append("Permit restricts the flight to day VMC.")
    best["notes"] = notes
    best["limit_weight"] = _limit_weight(p["tofl"], best["available"], mtow, dens, state, 1.0 if best["surface"] == "Hard" else 1.20)
    return best


def landing(type_code, weight_kg, icao, elev_ft=0, oat_c=15, wind_dir=None, wind_kt=0,
            surface_state="dry", restrictions=None, snags=None):
    p = PERF.get(type_code)
    if not p:
        return None
    restrictions = restrictions or {}
    snags = snags or []
    rws = runways(icao)
    if not rws:
        return dict(ok=None, reason="No runway data for this airport.")
    ratio = weight_kg / p["mlw_kg"]
    dens, da = _dens_factor(elev_ft, oat_c)
    state = {"dry": 1.0, "wet": 1.15, "contaminated": 1.45}.get(surface_state, 1.0)
    rev_pen = 1.10 if any(s.get("code") == "REV" for s in snags) else 1.0
    gear_pen = 1.0
    best = None
    for rw in rws:
        surf = 1.0 if rw["s"] == "H" else 1.15
        for e in rw["e"]:
            head, cross = wind_components(e["hdg"], wind_dir, wind_kt) if wind_kt else (0.0, 0.0)
            wind_f = 1 - 0.005 * head if head > 0 else 1 + 0.02 * abs(head)
            req = p["ldfl"] * max(0.5, ratio) * dens * state * surf * rev_pen * gear_pen * wind_f
            lda = rw["l"] - e.get("disp", 0)
            margin = lda - req
            cand = dict(runway=e["id"], length=rw["l"], lda=lda, surface="Hard" if rw["s"] == "H" else "Unpaved", lit=rw["lit"],
                        required=int(req), available=lda, margin=int(margin), headwind=head, crosswind=cross,
                        density_alt=da, ok=margin >= 0, vref=int(p["vref"] * math.sqrt(max(0.5, ratio))))
            if best is None or cand["margin"] > best["margin"]:
                best = cand
    notes = []
    if rev_pen > 1:
        notes.append("Thrust reverser deactivated: 10% landing distance penalty, no contaminated runway.")
    if state > 1 and rev_pen > 1:
        notes.append("Reverser inoperative on a wet or contaminated runway is not permitted.")
    if abs(best["crosswind"]) > 30:
        notes.append(f"Crosswind {abs(best['crosswind'])} kt exceeds most demonstrated limits.")
    best["notes"] = notes
    return best


def _limit_weight(base_tofl, avail_ft, mtow, dens, state, surf):
    """Largest weight whose required distance fits the runway."""
    if not mtow:
        return None
    k = base_tofl * dens * state * surf
    if k <= 0:
        return mtow
    ratio = avail_ft / k
    if ratio >= 1:
        return mtow
    return int(mtow * math.sqrt(max(0.0, ratio)))


MTOW = {}   # filled by data import below to avoid a circular import at module load


def set_mtow(d):
    MTOW.clear()
    MTOW.update(d)


# ---------------------------------------------------------------- weight & balance
def loadsheet(type_code, pax=0, cargo_kg=0, fuel_kg=0, ballast_kg=0, extra_crew=0, cargo_dist=0.5, pax_dist=0.5):
    """Compute weights and a %MAC centre of gravity.

    cargo_dist / pax_dist: 0 = all forward, 1 = all aft, 0.5 = evenly distributed.
    """
    p = PERF.get(type_code)
    if not p:
        return None
    b = dict(BALANCE, oew=OEW_ARM.get(type_code, BALANCE["oew"]))
    env = BALANCE_TP["env"] if p["cat"] == "Turboprop" else BALANCE["env"]
    pax_kg = pax * 100.0                       # passenger + baggage, standard mass
    crew_kg = (4 + extra_crew) * 90.0
    oew = p["oew_kg"] + crew_kg
    zfw = oew + pax_kg + cargo_kg + ballast_kg
    tow = zfw + fuel_kg
    # moments about %MAC
    def arm(dist, fwd, aft):
        return fwd + (aft - fwd) * dist
    m = oew * b["oew"] + pax_kg * arm(pax_dist, b["cabin_fwd"], b["cabin_aft"]) \
        + cargo_kg * arm(cargo_dist, b["fwd_hold"], b["aft_hold"]) + ballast_kg * b["fwd_hold"]
    zfw_cg = m / zfw if zfw else b["oew"]
    tow_cg = (m + fuel_kg * b["fuel"]) / tow if tow else zfw_cg
    limits = []
    if zfw > p["mzfw_kg"]:
        limits.append(f"Zero fuel weight {int(zfw):,} kg exceeds MZFW {p['mzfw_kg']:,} kg by {int(zfw - p['mzfw_kg']):,} kg.")
    if tow > MTOW.get(type_code, 1e9):
        limits.append(f"Takeoff weight {int(tow):,} kg exceeds MTOW {MTOW[type_code]:,} kg by {int(tow - MTOW[type_code]):,} kg.")
    if fuel_kg > p["fuel_kg"]:
        limits.append(f"Fuel {int(fuel_kg):,} kg exceeds tank capacity {p['fuel_kg']:,} kg.")
    cg_ok = env[0] <= tow_cg <= env[1]
    if not cg_ok:
        limits.append(f"Takeoff CG {tow_cg:.1f}% MAC is outside the {env[0]:.0f}–{env[1]:.0f}% MAC envelope"
                      + (" — load aft or reduce forward ballast." if tow_cg < env[0] else " — move load forward or add forward ballast."))
    return dict(oew=int(oew), pax=pax, pax_kg=int(pax_kg), cargo_kg=int(cargo_kg), ballast_kg=int(ballast_kg), fuel_kg=int(fuel_kg),
                zfw=int(zfw), tow=int(tow), mzfw=p["mzfw_kg"], mtow=MTOW.get(type_code), mlw=p["mlw_kg"], fuel_cap=p["fuel_kg"],
                zfw_cg=round(zfw_cg, 1), tow_cg=round(tow_cg, 1), env=env, cg_ok=cg_ok, limits=limits,
                ballast_advised=_ballast_advice(p, oew, pax_kg, cargo_kg, fuel_kg, env, b))


def _ballast_advice(p, oew, pax_kg, cargo_kg, fuel_kg, env, b):
    """An empty ferry often sits out of the aft limit: suggest forward ballast."""
    if pax_kg or cargo_kg > 500:
        return 0
    b = dict(b)
    zfw = oew + cargo_kg
    tow = zfw + fuel_kg
    cg = (oew * b["oew"] + cargo_kg * b["aft_hold"] + fuel_kg * b["fuel"]) / tow if tow else b["oew"]
    if cg <= env[1]:
        return 0
    # ballast at the forward hold needed to bring CG to mid-envelope
    target = (env[0] + env[1]) / 2
    need = (tow * (cg - target)) / max(1.0, target - b["fwd_hold"])
    return int(round(need / 100.0) * 100)


def landing_position(lat, lon, hdg, icao):
    """Touchdown zone distance from threshold and centreline offset, if the runway is known."""
    best = None
    for rw in runways(icao):
        for e in rw["e"]:
            if "lat" not in e:
                continue
            d_nm = _gc(lat, lon, e["lat"], e["lon"])
            if d_nm > 3:
                continue
            brg = _bearing(e["lat"], e["lon"], lat, lon)
            rel = math.radians((brg - e["hdg"] + 540) % 360 - 180)
            along = d_nm * 6076.12 * math.cos(rel)
            offset = d_nm * 6076.12 * math.sin(rel)
            hdg_diff = abs(((hdg or e["hdg"]) - e["hdg"] + 540) % 360 - 180)
            if along < -500 or along > rw["l"] or hdg_diff > 40:
                continue
            cand = dict(runway=e["id"], length=rw["l"], from_threshold=int(along), centreline=int(offset), hdg_diff=round(hdg_diff))
            if best is None or abs(cand["centreline"]) < abs(best["centreline"]):
                best = cand
    return best


def _gc(a, b, c, d):
    la1, lo1, la2, lo2 = map(math.radians, (a, b, c, d))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3440.065 * 2 * math.asin(math.sqrt(max(0.0, min(1.0, h))))


def _bearing(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(math.radians, (la1, lo1, la2, lo2))
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360
