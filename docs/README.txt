================================================================================
  OPERATOR - FERRY, CARGO & ACMI
  Version 1.8.0
================================================================================

  Someone else's aircraft. Your crew. Get it there.

  Operator is a companion program for flight simulators. You run a third-party
  flight operation: ferrying other people's aircraft, flying freight as contract
  crew for real cargo airlines, and wet-leasing your own jets to carriers on ACMI
  terms. Every sector is flown in your simulator and verified from live telemetry.

  It runs entirely on your own PC. No account, no internet connection required
  beyond SimBrief if you choose to use it, and nothing is uploaded anywhere.


--------------------------------------------------------------------------------
  QUICK START
--------------------------------------------------------------------------------

  1. Start Operator from the Start menu or desktop shortcut. It opens in its own
     window. A console window flashes up while the program starts, then hides.

  2. Create your company: name, a two or three letter code, a home base and your
     starting capital. Pick a difficulty if you want longer permit lead times and
     tighter margins.

  3. Follow the "Getting started" panel on the Dashboard. It tracks what you have
     actually done and always shows the next step, with a button to the right
     screen. In short:

       - Hire a flight dispatcher (no flight is released without one).
       - Hire a captain and a first officer with the same type rating.
       - Accept a ferry job that matches that rating. Look for the ones tagged
         "Good first job".
       - Wait for the paperwork, or pay to expedite it.
       - Plan the leg in SimBrief, dispatch it, fly it, file the PIREP.

  4. Later: take cargo pairings to build hours and cash, then lease an aircraft
     and bid for an ACMI contract.


--------------------------------------------------------------------------------
  WHAT YOU DO
--------------------------------------------------------------------------------

  FERRY WORK
  Lessors, MROs and airlines post one-off deliveries: lease returns, redeliveries,
  storage runs, reactivations, factory deliveries and maintenance positioning. The
  client owns the aircraft and pays for its fuel and handling; you supply a rated
  crew and the paperwork, and are paid on delivery.

  Business aircraft are moved by the people who actually move them - management
  companies, operators and the brokers who sell them - and go to the
  manufacturer's own service centre for anything heavy. Positioning for a
  scheduled inspection, collecting the aeroplane afterwards, a pre-purchase
  inspection, a sale delivery, an import on a new registry, or an empty leg
  because it is needed at the other end.

  Accepting a job starts the permit process. Insurance, overflight and landing
  clearances for every state on the route, special flight permits when the
  aircraft carries defects, export certificates on lease returns. Lead times are
  real: nothing for most of Europe, a week for Russia or China. Every document can
  be opened and read.

  Aircraft out of storage carry deferred defects with genuine restrictions -
  maximum altitude, maximum speed, gear down, day VMC only - and those limits are
  checked against what you actually fly.

  Defects are flown, not simulated. Not every add-on models failures, so Operator
  judges the flight on what you did: the altitude you held, the speed you kept,
  whether the gear stayed down, how far you strayed from a diversion airport. A
  study-level aircraft can fail the system for real; anything else simply flies
  the restriction by hand, and both count the same. Every defect carries a "how to
  fly this" note explaining what that means in the cockpit. Long sectors are planned with technical
  stops the type can make, using runways long enough for it.

  CARGO CONTRACT FLYING
  A hundred real freight carriers hire your crews when they are short. Each
  pairing is a published pattern of sectors out of one of their actual bases,
  usually at night, flown on their aircraft with their fuel and their load. You
  are paid a block-hour rate plus a day rate for each crew member when the pattern
  is complete. Loads include dangerous goods, AOG engines and outsized project
  cargo, all of which affect your takeoff performance.

  ACMI (WET LEASE)
  Airlines tender for capacity against named competitors. You supply the Aircraft,
  Crew, Maintenance and Insurance; they pay a rate per block hour with a monthly
  minimum and cover fuel, handling and fees. You need the right type in your
  fleet, two captains and two first officers, cabin crew for passenger work, and
  the aircraft positioned at their hub in their livery before the start date.
  Utilisation, rotation completion and on-time performance are all measured.



  YOUR CERTIFICATE
  An air operator certificate says where you may fly and, if you choose, what you
  may fly. Areas of operation are set when you found the company - the region your
  base is in - and work is only offered inside them.

  You can also have the certificate issued for a single type. Do that and ferry,
  cargo, ACMI and charter work is only offered on that type, nothing else can be
  released under your certificate, and the crew market fills with people rated on
  it. If you want the game to be about one aeroplane, that is how.

  Adding an area or a type later is an amendment: an application to the authority
  with a fee and a wait, listed on the Company profile with the date a decision is
  due. A second type from a manufacturer already on your certificate is cheaper
  and quicker. Leave the type field alone at setup and the certificate carries no
  type restriction at all, which is how it has always worked.


--------------------------------------------------------------------------------
  WHAT MAKES A FLIGHT COUNT
--------------------------------------------------------------------------------

  Operator reads your simulator once a second and reconstructs the flight: block
  off and on, takeoff, top of climb and descent, touchdown and shutdown. The PIREP
  reports touchdown rate, G, pitch, bank, crosswind, bounces, how far down the
  runway you landed and how far off the centreline, fuel burned against plan, any
  overspeed, and whether you stayed inside a permit's limits.

  Before departure it checks whether the flight is possible at all: runway length
  at both ends against your weight, temperature, wind and runway state, the
  runway-limited weight, Vref, and a full loadsheet with zero-fuel weight, takeoff
  weight, landing weight and a centre of gravity you can move by redistributing
  the load or adding ballast.

  If you would rather not fly a sector yourself, hand it to your own crew. How
  well it goes depends on their experience, how much duty they have already done
  and the conditions you sent them into.

  How long they take depends on your clock. On the game clock the clock is yours
  to move, so the sector files at once and the clock jumps by the block time. On a
  real-time or simulator clock the aeroplane is genuinely away: it leaves now,
  arrives at its ETA, and the aircraft and both pilots are committed until it
  lands. Dispatch and the schedule board show it running down, and the PIREP files
  itself on arrival.


--------------------------------------------------------------------------------
  SIMULATOR CONNECTION
--------------------------------------------------------------------------------

  MSFS 2020, MSFS 2024, Prepar3D
    Connects through SimConnect. Operator must run on the same PC as the
    simulator. Press Connect in the status bar with the simulator running.

  X-Plane 11 and 12
    Nothing to install. Operator listens for datarefs over UDP port 49000. If
    X-Plane runs on another machine, enter its IP address in Settings.

  FSUIPC (FSX, P3D, MSFS with FSUIPC7)
    Available as a fallback. Select it in Settings.

  Load the aircraft cold at the gate, press Connect, then Start tracking. Fly the
  sector, taxi in, set the parking brake and shut down, then file the PIREP.


--------------------------------------------------------------------------------
  SIMBRIEF
--------------------------------------------------------------------------------

  Enter your SimBrief username or numeric pilot ID in Settings, and set Weight
  units to match your SimBrief account - pounds or kilograms. Operator sends that
  choice with every plan and warns you if an imported OFP uses the other unit.

  In Dispatch, "Send to SimBrief" opens SimBrief pre-filled with the flight:
  aircraft type and registration, your airline code and flight number, the city
  pair, date and departure time, zero passengers on a ferry, a cruise cap when a
  permit limits altitude, and the permit and defect conditions in the remarks.

  Generate the plan there and Operator pulls it straight back on its own - route,
  cruise level, fuel, weights, ETE and weather. "Fetch OFP" does it manually.


--------------------------------------------------------------------------------
  RUNNING AND SAVING
--------------------------------------------------------------------------------

  Operator opens in its own window with its own taskbar entry. Closing the window
  quits the program.

  Your company lives in a single file:

      <installation folder>\save\operator.db

  Multiple companies are supported through save slots (System > Save files), and
  you can download a backup or restore one at any time. Uninstalling asks whether
  you want to keep your saves.

  Command-line switches, if you ever need them:

      Operator.exe              desktop window (default)
      Operator.exe --browser    open in your web browser instead
      Operator.exe --app        force an app-mode Edge or Chrome window
      Operator.exe --port 9000  listen on a different port
      Operator.exe --lan        reachable from other machines on your network

  There is a Start menu shortcut for browser mode if the window will not open.


  RUNNING IT ON A SERVER
  ----------------------
  By default Operator listens on 127.0.0.1 and nothing outside the PC it runs
  on can reach it. If you would rather keep your company on a machine that is
  always on - a home server, a Proxmox container, a NAS - and open it from
  whatever PC you happen to be flying on:

      ./run.sh --lan                 listen on every interface, port 8123
      ./run.sh --host 0.0.0.0        the same thing, written out
      ./run.sh --host 192.168.1.50   one interface only
      ./run.sh --lan --port 9000     a different port

  It prints the address to use from another machine when it starts. No window
  and no browser are opened, so it is happy on a headless box; add --window if
  you do want one. X-Plane can be on a third machine again - put its address in
  Settings.

  There is no login and no password. Anyone who can reach the address can open
  your company and spend your money, so keep it to a network you trust and do
  not forward the port to the internet.


  Developer tools
      Settings has a Developer tools switch, off by default. Turning it on adds a
      panel at the top of Settings for setting reputation and cash, moving the
      clock, adding jobs to the boards, hiring crew and repositioning aircraft.
      It exists so a feature can be tried without hours of flying first. A save
      that has used it is marked, and the status bar shows a "dev" badge.


--------------------------------------------------------------------------------
  UPDATING
--------------------------------------------------------------------------------

  Run the new installer over the top. There is no need to uninstall first.

  Your company, save slots and settings are kept - saves live in the "save"
  folder inside the installation directory and the installer never touches it.
  Older saves are migrated automatically when the program opens them.

  Close Operator before installing. If it is running, the installer offers to
  close it for you.

  If you use the portable build instead, unzip the new version into a fresh
  folder and copy your old "save" folder across.

  Uninstalling asks whether you want to keep your saves, so removing an old
  version by hand is never necessary and risks deleting your company.


--------------------------------------------------------------------------------
  IF SOMETHING GOES WRONG
--------------------------------------------------------------------------------

  Every start is written to operator-log.txt in the installation folder, and a
  startup failure keeps the console window open with the reason.

  "Windows protected your PC" on install or first run
      The build is not code-signed. Choose "More info" and then "Run anyway".

  The window does not appear
      Try the "Operator (browser)" Start menu shortcut. If that works, your Edge
      WebView2 runtime is missing or blocked; installing Microsoft Edge restores
      it.

  Nothing happens at all
      Another copy may already be running - Operator will open your browser at the
      existing one. If a different program is using port 8123, Operator moves to
      the next free port and says so in the log.

  The simulator will not connect
      MSFS and P3D must be on the same PC as Operator, and the simulator should be
      running and loaded into a flight before you press Connect. For X-Plane, check
      that UDP port 49000 is not blocked by a firewall and that the IP address in
      Settings is correct.

  "SimConnect: failed to load SimConnect.dll"
      The build is missing the SimConnect library. Update to the current release.
      If it persists, install the MSFS SDK (which provides SimConnect.dll) or copy
      SimConnect.dll next to Operator.exe, then press Connect again. Operator also
      searches the SDK and the simulator's own install folders automatically.

  Operator was closed during a flight
      The sector resumes automatically when you reopen it - a snapshot is written
      every twenty seconds. If the panel still waits for telemetry, press Start
      tracking to pick it up from that point, or file a manual PIREP.

  A flight is refused
      The pre-departure checklist on the active flight names the reason:
      paperwork outstanding, crew out of duty hours, aircraft in the wrong place,
      maintenance overdue, or the runway too short for the weight.


--------------------------------------------------------------------------------
  WHICH DOWNLOAD DO I WANT?
--------------------------------------------------------------------------------

  Operator-<version>-Windows-Installer.zip
      Unzip and run the setup. Installs to Program Files with Start menu and
      desktop shortcuts and a proper uninstaller. This is the one most people
      want.

  Operator-<version>-Windows-Portable.zip
      The same program with nothing installed. Unzip anywhere and run
      Operator.exe. Saves live in the save folder beside it.

  Operator-<version>-Source-CrossPlatform.zip
      For running from source on Windows, and the basis of a future macOS and
      Linux release. Needs Python 3.10 or newer; run run.bat, or ./run.sh
      elsewhere. See MAC-AND-LINUX.txt.

  This release is Windows only. A macOS build is planned; note that MSFS and
  Prepar3D cannot be supported on macOS at all, because SimConnect is a Windows
  library. X-Plane works on any platform.


--------------------------------------------------------------------------------
  CREDITS AND LICENSING
--------------------------------------------------------------------------------

  Airport, runway and elevation data are derived from OurAirports
  (ourairports.com), released into the public domain. Coastlines, national
  boundaries and lakes on the moving map come from Natural Earth
  (naturalearthdata.com), also public domain. Both are bundled with the program;
  the map needs no internet connection.

  Airline, lessor, manufacturer, MRO and cargo operator names and logos are the
  property of their respective owners. They appear in this program to identify the
  company being simulated. Their inclusion does not imply any sponsorship,
  endorsement or affiliation, and no rights in them are transferred. The source of
  every mark is listed inside the program under System > Credits.

  This program is not affiliated with, endorsed by or connected to Microsoft,
  Asobo Studio, Laminar Research, Lockheed Martin, Navigraph or SimBrief.

  Provided as-is, without warranty of any kind. Not for real-world navigation or
  flight planning.

================================================================================
