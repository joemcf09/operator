# Operator — Ferry, Cargo & ACMI
### Version 1.0

A local application for flight simmers who want to run a third-party flight operation: ferrying other
people's aircraft, flying freight as contract crew for real cargo carriers, and wet-leasing your own
metal to airlines — with real economics, real customers and telemetry-verified flights.

Works with **MSFS 2020 / MSFS 2024 / Prepar3D** (SimConnect) and **X-Plane 11 / 12** (UDP datarefs),
and imports your **SimBrief** OFP for dispatch.

## Run it

Windows: double-click `run.bat`. macOS/Linux: `./run.sh`. Installed copies just use the Start menu or
desktop shortcut.

Operator opens in **its own desktop window** — no browser chrome, its own taskbar entry, closing the
window quits the program. On Windows that window is the Edge WebView2 runtime that ships with Windows 10
and 11; nothing extra to install. If it is unavailable, Operator falls back to an app-mode Edge or Chrome
window, and failing that to an ordinary browser tab. Start it with `--browser` (there is a Start menu
shortcut for this) to force the browser, or `--app` for app mode.
The first run creates a Python virtual environment and installs Flask, pywebview (the desktop window) and
SimConnect on Windows. Everything is saved in `save/operator.db`. In browser mode a console window stays
open while you play; in desktop mode the console hides itself once the window appears.

Requirements: **Python 3.10 or newer from [python.org](https://www.python.org/downloads/windows/)**,
with "Add python.exe to PATH" ticked during setup.

### "Python was not found; run without arguments to install from the Microsoft Store"

Windows ships a placeholder `python` command that opens the Store instead of running Python. `run.bat`
now looks for the `py` launcher and the usual install locations first and skips that placeholder, so the
usual fix is simply to install Python from python.org and run the file again. If you would rather remove
the placeholder: Settings → Apps → Advanced app settings → App execution aliases, and turn off both
"python.exe" and "python3.exe".

Two other things worth knowing: keep the folder somewhere simple such as `C:\Operator` rather than inside
OneDrive or Program Files, and if dependency installation fails it is almost always a firewall or proxy
blocking pip.

## Simulator connection

* **MSFS / P3D** — run Operator on the same PC as the sim. The `SimConnect` Python package is
  installed automatically on Windows. Press *Connect* in the status bar with the sim running.
* **X-Plane** — nothing to install. Operator subscribes to datarefs over UDP port 49000.
  If X-Plane runs on another machine, enter its IP in Settings and make sure the port is reachable.

## SimBrief

Enter your SimBrief username (or numeric pilot ID) in Settings. In Dispatch, *Send to SimBrief* opens
dispatch.simbrief.com pre-filled with the flight (type, registration, airline code and flight number,
city pair, date/STD, pax 0 for ferries, cruise cap when a permit limits altitude, and permit/defect
remarks). Generate the plan there (log in to SimBrief in that tab), then *Fetch OFP* pulls that exact
plan back by its reference — route, fuel, weights, ETE and weather — ready to dispatch.

## What's simulated

**Three lines of business.** Ferry other people's aircraft with your crew and paperwork; fly freight as
contract crew for real cargo carriers on their metal; wet-lease your own aircraft to airlines on ACMI
terms. Each has its own board, economics and failure modes, and you can run all three at once.

**Ferry work** — lease returns, redeliveries, storage runs, reactivations, factory deliveries and
maintenance positioning from real lessors, MROs and operators. Permit paperwork with per-state lead times
(overflight and landing clearances, special flight permits, export certificates), each document readable
as a facsimile, with an expedite option. Deferred defects carry real restrictions — maximum altitude,
speed, gear down, day VMC — enforced from telemetry. ETOPS status per airframe with a 60-minute
diversion check on oceanic sectors, and redelivery inspections that can reject the aircraft.

**Cargo contract flying** — a hundred real freight carriers (FedEx, UPS, Atlas, Kalitta, Cargolux,
Cargojet, ASL, AeroLogic, Amerijet, Northern Air Cargo, Emirates SkyCargo, Nippon Cargo and the rest) hire
your crews when they are short. Published patterns of sectors out of their actual bases, mostly at night,
with their aircraft, fuel and load — including dangerous goods, AOG engines and outsized project cargo
that feed straight into your takeoff performance. Paid per block hour plus a day rate on completion.

**ACMI** — airlines tender for capacity against named competitors. You supply Aircraft, Crew, Maintenance
and Insurance; they pay a block-hour rate with a monthly minimum. Crew flight-time limitations (13 h FDP,
12 h rest, crews rotate automatically), daily rotations with departure times, technical delays, KPIs for
utilisation, completion and on-time performance, delay penalties, seasonal rates, livery reconfiguration,
cabin crew requirements and extension offers from satisfied customers.

**Fleet and finance** — buy or lease from real lessors, engine shop visits with a power-by-the-hour
option, A and C checks, Airworthiness Directives, depreciation and a used-market cycle, ground staff,
loans, an income statement, a balance sheet and a fleet utilisation view.

**Performance and loading** — real runway data for every airport. Takeoff and landing analysis against
your weight, elevation, temperature, wind and runway state, with runway-limited weight and Vref, refusing
a flight the runway cannot take. A full loadsheet with ZFW, TOW, estimated landing weight and a %MAC
centre of gravity you can move with load-distribution sliders, and ballast for a tail-heavy empty ferry.

**Routing** — long sectors are planned with technical stops the type can actually make, using runways long
enough for it and preferring the airfields ferry crews really use. Dispatch offers one leg at a time.

**Flight tracking** — phases, block times, fuel burn, touchdown rate, pitch, bank, crosswind, bounces,
distance down the runway and off the centreline, permit-limit breaches and diversion distance, read live
from the simulator. Or hand the sector to your own crew and let them fly it while the clock runs.

**Safety** — every sector carries a small risk multiplied by crew fatigue and inexperience, deferred
defects, overdue maintenance, airframe age, weather and thin runway margins. Most events are routine.
Serious incidents ground the aircraft and load your insurance; accidents are rare, cost the airframe, can
cost crew, suspend operations and are followed by an investigation that names the contributing factors.
The whole system can be switched off.

**Crew** — individual pilots with type ratings, duty time, rest, hours with your company and a command
upgrade path from first officer to captain, plus seniority pay rises.

**Analytics and history** — month-end snapshots feeding cash and equity, revenue by line of business, cost
breakdown, landing performance with a rolling average, fleet utilisation, reputation and headcount, a
company timeline, and an annual report each New Year that prints to PDF.

**Presentation** — a light and dark theme, a detachable flight window for a second monitor, a Getting
started panel that tracks your progress, per-screen help, a glossary, difficulty presets, milestones, an
ops inbox, save slots with backup and restore, CSV and printable exports, and a Discord webhook.

## Three lines of business

| | Aircraft | Crew | Ground staff | Pays |
|---|---|---|---|---|
| Ferry | client's | yours | dispatcher | fee on delivery |
| Cargo contract flying | carrier's | yours | dispatcher | block hours + day rate on pairing completion |
| ACMI | yours | yours | dispatcher, maintenance controller, cabin crew | block hours + monthly guarantee |

## Flow

1. Establish the company (name, code, base, capital).
2. Hire rated crew; lease or buy aircraft for ACMI work.
3. Hire a dispatcher (and a maintenance controller once you own aircraft). Accept ferry jobs (crew + paperwork) or bid on ACMI tenders (own aircraft, 4 pilots, cabin crew, positioned at the hub).
4. Dispatch a leg, load at the gate, connect, start tracking, fly, shut down, file the PIREP.
5. Month-end posts leases, salaries, insurance, overheads and ACMI minimum guarantees.

## Building the Windows installer

Double-click **`make-installer.bat`**. It creates the Python environment if needed, installs PyInstaller,
builds the application, offers to fetch Inno Setup 6 through winget if you do not have it, compiles the
installer, produces a portable zip, writes a SHA-256 checksum and opens the output folder.

    installer\Output\Operator-Setup-1.0.0.exe        the installer
    installer\Output\Operator-1.0.0-portable.zip     the same build as a folder
    installer\Output\SHA256SUMS.txt

`build.bat` does the same without the extras, and `./build.sh` produces `dist/Operator/` on macOS or Linux.

What the installer does: installs per-user by default (no administrator prompt) with an option to install
for all users, offers Start menu and desktop shortcuts, carries the icon and version resource, registers a
proper uninstaller, and on removal asks whether to keep your saves. Saves live in `save` beside the
executable.

The installer puts Operator in Program Files, offers Start menu and desktop shortcuts, registers a proper
uninstaller, and on removal asks whether to keep your saves. Saves live in a `save` folder beside the
executable.

### Command-line switches

    Operator.exe              desktop window (default)
    Operator.exe --browser    open in your default browser instead
    Operator.exe --app        force app-mode Edge/Chrome
    OPERATOR_PORT=8200        run on a different port

### If the program starts and nothing happens

Every start is written to `operator-log.txt` next to the executable, and a startup failure keeps the
console window open with the reason. The two usual causes:

* **Something else is on port 8123.** Operator now shifts to the next free port automatically and says so;
  if another copy is already running it just opens your browser at the existing one.
* **Antivirus or SmartScreen.** PyInstaller executables are unsigned, so Windows may block or quarantine
  the file. Choose *More info → Run anyway*, or exclude the folder. The one-folder build produced by
  `build.bat` triggers this far less often than a single-file build.

Set a different port with the `OPERATOR_PORT` environment variable if you need to.

## Brand assets

`brand/` holds the mark as SVG (dark, light and a `currentColor` monochrome version), PNG icons from
16 px to 512 px, a Windows `.ico`, and horizontal lockups on light and dark backgrounds.

## Notes

* Real lessors, MROs, storage fields, delivery centres, airlines and cargo operators appear by name, each
  with its own mark. Upload your own company logo from the Company profile page.
* The airport database is the OurAirports public-domain dataset — roughly 5,000 large and medium airports
  with elevations, plus 12,700 runways. Permits, fuel pricing, performance and diversion checks all
  resolve against it. Sectors to fields outside the set still work, with distance taken from the OFP and
  arrival matched to the nearest known airport.
* Performance figures are simplified models tuned to published field lengths — enough to make runway
  choice matter, not a substitute for an aircraft flight manual.
* FSUIPC support uses documented offsets but is untested; SimConnect and X-Plane are the primary paths.
* Not for real-world navigation or flight planning.

## Data credits

Every operator in the game carries a mark: 123 company assets sourced from operator press pages and
media libraries (provenance for each is recorded in `static/operators/company-logo-sources.csv` and
`sources.json`, and shown in the app under System → Credits), around a hundred more normalised from
Wikimedia Commons, and two original placeholder wordmarks where no asset was found — Carlyle Aviation
Partners and Macquarie AirFinance — produced by `tools/make_placeholder_logos.py`.

All names and marks remain the property of their respective owners. They are used to identify the
company within a simulation and imply no sponsorship, endorsement or transfer of rights. Drop a
replacement file into `static/operators/` under the same filename to swap any mark; nothing in the code
needs changing.

Artwork is trimmed of transparent padding and fitted to a common box so a wide wordmark and a tall
roundel read at the same visual weight, and each mark's tone is measured at build time so white-on-
transparent artwork gets a dark plate in the light theme and dark artwork gets a light plate in the dark
theme.

Operator branding in `static/operators/` identifies simulated customers. Most assets are normalised
from Wikimedia Commons with the file page, licence, artist and credit recorded in
`static/operators/sources.json` and reproduced in the app under System → Credits; the remainder are
original placeholder artwork. Real-world names and logos remain the trademarks of their owners and their
presence does not imply sponsorship or endorsement.

Airport and runway data (`airports.json`, `runways.json`, `elevations.json`) is derived from
[OurAirports](https://ourairports.com/data/), released into the public domain. Performance figures are
simplified models tuned to published field lengths — good enough to make runway choice matter, not a
substitute for a real AFM. Airline, lessor, MRO and manufacturer names are used nominatively; no third-party
logos or trademarks are included.
