"""Safety model.

Every sector carries a small, quantified risk. The base rates are deliberately low —
an accident is a rare event — but they are multiplied by the things that really drive
risk in an operation: crew fatigue and inexperience, deferred defects, overdue or
near-limit maintenance, ageing airframes, weather, thin runway margins and flying an
aircraft on a special permit outside its normal envelope.

Occurrences come in three severities:
  * occurrence  — an event with no damage: bird strike, tyre burst, precautionary shutdown
  * incident    — damage to the aircraft, downtime, an insurance claim, possible minor injuries
  * accident    — substantial damage or hull loss, an investigation and possible casualties

The intent is that a well-run operation almost never sees the third category. Everything
here is fictional and reported in the language a safety department would use.
"""
import random

# Per-sector base probabilities for a well-run operation in good conditions.
BASE = dict(occurrence=0.010, incident=0.0009, accident=0.00010)

FACTORS = [
    # key, label, how the multiplier is derived from the context
    ("fatigue", "Crew duty and fatigue"),
    ("experience", "Crew experience on type"),
    ("defects", "Deferred defects carried"),
    ("maintenance", "Maintenance status"),
    ("airframe", "Airframe age"),
    ("weather", "Weather"),
    ("runway", "Runway margin"),
    ("permit", "Permit / non-standard operation"),
    ("handling", "Handling on this sector"),
]

OCCURRENCES = [
    dict(text="Bird strike on departure; no damage found at the turnaround inspection.", cost=1800, days=0),
    dict(text="Lightning strike in the climb; conductivity checks carried out, aircraft serviceable.", cost=4200, days=0),
    dict(text="Cabin pressurisation warning, precautionary descent; system reset and monitored.", cost=2500, days=0),
    dict(text="Main wheel tyre replaced after the landing roll; wear beyond limits.", cost=3800, days=0),
    dict(text="Engine oil filter bypass indication; borescope carried out, no findings.", cost=9500, days=1),
    dict(text="TCAS resolution advisory in the descent; report filed with the authority.", cost=0, days=0),
    dict(text="Ground handling damage at the stand; dent within limits, deferred.", cost=6500, days=0),
    dict(text="Cargo load shifted in flight; load spread checked and repalletised.", cost=3200, days=0),
    dict(text="Bleed air leak on the ground before departure; rectified by line maintenance.", cost=5200, days=0),
]

INCIDENTS = [
    dict(text="Hard landing exceeding limits; hard landing inspection found structural damage requiring repair.", days=(6, 18), cost=(0.006, 0.020), injury=0.05),
    dict(text="Runway excursion on landing; the aircraft left the paved surface and sustained gear and flap damage.", days=(14, 40), cost=(0.02, 0.06), injury=0.12),
    dict(text="Tailstrike on rotation; rear fuselage skin damage requiring a structural repair.", days=(10, 25), cost=(0.01, 0.035), injury=0.0),
    dict(text="Engine failure in the cruise; single-engine diversion, engine removed for shop visit.", days=(12, 30), cost=(0.03, 0.08), injury=0.0),
    dict(text="Nose gear collapse during the landing roll; substantial lower fuselage damage.", days=(20, 60), cost=(0.05, 0.12), injury=0.15),
    dict(text="Ground fire in the cargo hold after arrival; extinguished by the airport fire service, smoke and heat damage.", days=(25, 70), cost=(0.06, 0.15), injury=0.20),
    dict(text="Severe turbulence encounter; injuries to crew and damage to interior fittings.", days=(3, 10), cost=(0.004, 0.012), injury=0.55),
    dict(text="Loss of braking on a contaminated runway; overrun into the stopway with gear damage.", days=(12, 35), cost=(0.02, 0.05), injury=0.10),
]

ACCIDENTS = [
    dict(text="Controlled flight into terrain during a non-precision approach in poor visibility.", hull=True, fatal=0.85),
    dict(text="Loss of control in flight following a system failure and crew mishandling.", hull=True, fatal=0.80),
    dict(text="Runway overrun at high speed; the aircraft crossed the airport perimeter and was destroyed by the subsequent fire.", hull=True, fatal=0.35),
    dict(text="In-flight fire that could not be contained; the crew diverted but the aircraft was destroyed after landing.", hull=True, fatal=0.30),
    dict(text="Structural failure in flight following an undetected fatigue crack.", hull=True, fatal=0.85),
    dict(text="Collision with terrain shortly after takeoff at a high density altitude with the aircraft above its performance limit.", hull=True, fatal=0.70),
    dict(text="Gear-up landing following a hydraulic failure; substantial damage, the airframe was written off as beyond economic repair.", hull=True, fatal=0.02),
    dict(text="Severe damage on landing after an unstable approach; the airframe was assessed as beyond economic repair.", hull=True, fatal=0.03),
]

FINDINGS = {
    "fatigue": "The investigation found the crew had operated close to their flight duty limits with reduced rest, and identified fatigue as a contributing factor.",
    "experience": "The investigation noted the crew's limited recent experience on type as a contributing factor.",
    "defects": "The investigation identified deferred defects carried on the aircraft as a contributing factor.",
    "maintenance": "The investigation found that scheduled maintenance had been deferred beyond its due point and identified this as a causal factor.",
    "airframe": "The investigation noted the age and condition of the airframe as a contributing factor.",
    "weather": "The investigation identified the weather conditions at the time as a contributing factor.",
    "runway": "The investigation found the runway available offered little margin for the weight being operated.",
    "permit": "The investigation noted the aircraft was operating under a special flight permit with associated restrictions.",
    "handling": "The investigation identified the handling of the aircraft on the sector as a causal factor.",
}


def risk_profile(ctx):
    """ctx: dict with the operational facts of a sector. Returns factor multipliers."""
    f = {}
    duty = ctx.get("duty_h", 0.0)
    f["fatigue"] = 1.0 + max(0.0, duty - 8) * 0.35 + (0.8 if ctx.get("night") else 0.0) * 0.4
    hrs = ctx.get("crew_hours_min", 8000)
    f["experience"] = 1.0 + max(0.0, (3000 - min(hrs, 3000)) / 3000) * 1.6
    f["defects"] = 1.0 + 0.5 * len(ctx.get("snags") or [])
    fh_ratio = ctx.get("fh_since_a", 0) / max(1, ctx.get("a_check_fh", 600))
    over = ctx.get("checks_overdue", 0)
    esv = ctx.get("engine_hours_left", 5000)
    f["maintenance"] = 1.0 + max(0.0, fh_ratio - 0.75) * 2.0 + over * 2.5 + (0.8 if esv < 250 else 0.0)
    age = ctx.get("age_years", 5)
    f["airframe"] = 1.0 + max(0, age - 15) * 0.05
    f["weather"] = 1.0 + 0.55 * len(ctx.get("wx", []) or []) + (0.4 if ctx.get("surface_state") in ("wet", "contaminated") else 0.0)
    margin = ctx.get("runway_margin")
    f["runway"] = 1.0 if margin is None else (2.6 if margin < 0 else 1.8 if margin < 500 else 1.3 if margin < 1500 else 1.0)
    f["permit"] = 1.35 if ctx.get("permit_flight") else 1.0
    f["handling"] = ctx.get("handling", 1.0)
    return f


def multiplier(f):
    m = 1.0
    for v in f.values():
        m *= v
    return m


def contributors(f, limit=3):
    return [k for k, v in sorted(f.items(), key=lambda x: -x[1]) if v > 1.15][:limit]


def roll(ctx, rng=None, scale=1.0):
    """Return an occurrence dict or None."""
    rng = rng or random
    f = risk_profile(ctx)
    m = min(12.0, multiplier(f))
    cause = contributors(f)
    p_acc = BASE["accident"] * m * scale
    p_inc = BASE["incident"] * m * scale
    p_occ = BASE["occurrence"] * m * scale
    r = rng.random()
    if r < p_acc:
        t = dict(rng.choice(ACCIDENTS))
        return dict(severity="accident", template=t, factors=f, multiplier=round(m, 2), causes=cause)
    if r < p_acc + p_inc:
        t = dict(rng.choice(INCIDENTS))
        return dict(severity="incident", template=t, factors=f, multiplier=round(m, 2), causes=cause)
    if r < p_acc + p_inc + p_occ:
        t = dict(rng.choice(OCCURRENCES))
        return dict(severity="occurrence", template=t, factors=f, multiplier=round(m, 2), causes=cause)
    return None


def finding_text(causes):
    if not causes:
        return "The investigation did not identify a single causal factor."
    return " ".join(FINDINGS[c] for c in causes if c in FINDINGS)


def casualties(rng, template, crew_n=2, severity="accident"):
    """Return (injured, fatal) among the operating crew. Deliberately restrained."""
    if severity == "incident":
        if rng.random() < template.get("injury", 0.0):
            return (1 if rng.random() < 0.7 else crew_n), 0
        return 0, 0
    p = template.get("fatal", 0.5)
    r = rng.random()
    if r < p:
        return 0, crew_n
    if r < p + 0.35:
        return (1 if rng.random() < 0.5 else crew_n), 0
    return 0, 0
