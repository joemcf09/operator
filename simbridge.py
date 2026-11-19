"""Simulator telemetry bridge.

Two back-ends:
  * MSFS 2020 / MSFS 2024 / Prepar3D -> SimConnect (python 'SimConnect' package, Windows only)
  * X-Plane 11 / 12                   -> native UDP RREF dataref subscription (port 49000)
  * FSUIPC (FSX / P3D / MSFS with FSUIPC7) -> 'fsuipc' python package, best-effort fallback

Both produce the same normalised sample dictionary once per second:
  lat, lon, alt_ft, agl_ft, ias, gs, vs, hdg, on_ground, fuel_lbs, g, eng_on,
  park_brake, gear, paused, ts
"""
import os
import socket
import struct
import sys
import threading
import time

LBS_PER_KG = 2.20462
MS_TO_KT = 1.94384
M_TO_FT = 3.28084

XP_DATAREFS = [
    "sim/flightmodel/position/latitude",
    "sim/flightmodel/position/longitude",
    "sim/flightmodel/position/elevation",
    "sim/flightmodel/position/y_agl",
    "sim/flightmodel/position/indicated_airspeed",
    "sim/flightmodel/position/groundspeed",
    "sim/flightmodel/position/vh_ind_fpm",
    "sim/flightmodel/position/mag_psi",
    "sim/flightmodel/failures/onground_any",
    "sim/flightmodel/weight/m_fuel_total",
    "sim/flightmodel/forces/g_nrml",
    "sim/flightmodel/engine/ENGN_running[0]",
    "sim/cockpit2/controls/parking_brake_ratio",
    "sim/flightmodel2/gear/deploy_ratio[0]",
    "sim/time/paused",
    "sim/flightmodel/position/theta",
    "sim/flightmodel/position/phi",
    "sim/cockpit2/gauges/indicators/wind_speed_kts",
    "sim/cockpit2/gauges/indicators/wind_heading_deg_mag",
    "sim/time/zulu_time_sec",
    "sim/time/local_date_days",
]


def vs_units(samples, need=8):
    """Work out whether a simulator reports vertical speed in fpm or ft/s.

    samples: (reported, derived_fpm) pairs taken while genuinely climbing or descending.
    Both MSFS and X-Plane report feet per minute, so that is the assumption unless the
    evidence is overwhelming. A single bad altitude reading can make the derived rate
    enormous, so pairs are only counted when both figures are plausible, and a decision
    needs a clear majority of them agreeing.
    """
    votes = {1.0: 0, 60.0: 0, 1 / 60.0: 0}
    counted = 0
    for reported, derived in samples:
        if not (400 < abs(derived) < 6000) or abs(reported) < 1e-6:
            continue                       # implausible climb rate, or nothing reported
        ratio = abs(reported) / abs(derived)
        if 0.4 <= ratio <= 2.5:
            votes[1.0] += 1                # already feet per minute
        elif 1 / 90 <= ratio <= 1 / 35:
            votes[60.0] += 1               # reported in feet per second
        elif 35 <= ratio <= 90:
            votes[1 / 60.0] += 1           # reported pre-multiplied
        else:
            continue                       # nothing sensible: ignore this pair
        counted += 1
    if counted < need:
        return None
    best = max(votes, key=votes.get)
    if votes[best] < 6 or votes[best] < counted * 0.7:
        return None                        # no clear answer yet, keep watching
    return best


def angle_scale(peak):
    """Radians or degrees? Attitude in radians never gets far past 0.6 in normal flight,
    so once we have seen a rotation or a turn the answer is unambiguous."""
    return 57.29578 if peak < 1.5 else 1.0


class SimBridge:
    def __init__(self):
        self.source = None          # 'msfs' | 'xplane'
        self.connected = False
        self.status = "Disconnected"
        self.sample = None
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()
        self.xp_host = "127.0.0.1"
        self.xp_port = 49000
        self.dll_used = None
        self.last_data = 0.0
        self._winner = None
        self._only = None           # restrict to one simulator when the user chose it
        self.xp_diag = {}

    # ------------------------------------------------------------ control
    def connect(self, source="auto", xp_host="127.0.0.1", xp_port=49000):
        self.disconnect()
        self.xp_host, self.xp_port = xp_host, int(xp_port)
        self._stop.clear()
        self.status = "Connecting"
        self._thread = threading.Thread(target=self._run, args=(source,), daemon=True)
        self._thread.start()

    def disconnect(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None
        self.connected = False
        self.source = None
        self.status = "Disconnected"
        self.sample = None

    def get(self):
        with self._lock:
            # A link that has gone quiet still looks "connected" otherwise, which is
            # misleading when the simulator has been closed or the flight unloaded.
            if self.sample and self.last_data and time.time() - self.last_data > 20 and self.connected:
                self.status = "No data from the simulator for 20 seconds — is it still running?"
            return dict(self.sample) if self.sample else None

    def info(self):
        return dict(connected=self.connected, source=self.source, status=self.status, sample=self.get(),
                    diag=getattr(self, "xp_diag", {}))

    # ------------------------------------------------------------ workers
    LABEL = {"msfs": "Connected to MSFS/P3D via SimConnect", "xplane": "Connected to X-Plane via UDP",
             "fsuipc": "Connected via FSUIPC"}

    def _log_first_packet(self, size):
        try:
            print(f"[simbridge] first X-Plane packet received ({size} bytes)")
        except Exception:
            pass

    def _claim(self, who):
        """First listener with real data owns the connection; the others stand down."""
        with self._lock:
            if self._only and who != self._only:
                return False
            if self._winner is None:
                self._winner = who
                self.source = who
                self.connected = True
                self.status = self.LABEL.get(who, "Connected")
                if who == "msfs" and self.dll_used:
                    self.status += f" (DLL: {os.path.basename(self.dll_used)})"
            return self._winner == who

    def _run(self, source):
        self._winner = None
        self._only = None if source == "auto" else source
        if source == "fsuipc":
            self._run_fsuipc()
            return
        if source == "msfs":
            self._run_msfs(fallback_ok=False)
            return
        if source == "xplane":
            self._run_xplane()
            return

        # auto: listen for both at once rather than guessing. MSFS can accept a
        # connection without sending anything, and X-Plane sends without being asked,
        # so the only reliable test is which one actually produces a sample.
        self.status = "Looking for a simulator…"
        threads = [threading.Thread(target=self._run_xplane, daemon=True),
                   threading.Thread(target=self._run_msfs, kwargs={"fallback_ok": True}, daemon=True)]
        for t in threads:
            t.start()
        while any(t.is_alive() for t in threads) and not self._stop.is_set():
            time.sleep(0.3)

    @staticmethod
    def _simconnect_dll_candidates():
        """Places a usable SimConnect.dll may live, best first."""
        import glob
        out = []
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        out += [os.path.join(base, "SimConnect", "SimConnect.dll"), os.path.join(base, "SimConnect.dll")]
        try:
            import SimConnect as _sc
            out.append(os.path.join(os.path.dirname(_sc.__file__), "SimConnect.dll"))
        except Exception:
            pass
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local = os.environ.get("LOCALAPPDATA", "")
        out += [
            r"C:\MSFS SDK\SimConnect SDK\lib\SimConnect.dll",
            r"C:\MSFS 2024 SDK\SimConnect SDK\lib\SimConnect.dll",
            os.path.join(pf, "MSFS SDK", "SimConnect SDK", "lib", "SimConnect.dll"),
            os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32", "SimConnect.dll"),
        ]
        # Store and Steam installations keep a copy inside the package folder
        for pat in (
            os.path.join(local, "Packages", "Microsoft.Limitless_*", "LocalCache", "**", "SimConnect.dll"),
            os.path.join(local, "Packages", "Microsoft.FlightSimulator_*", "LocalCache", "**", "SimConnect.dll"),
            os.path.join(pf86, "Steam", "steamapps", "common", "**", "SimConnect.dll"),
            os.path.join(pf, "WindowsApps", "Microsoft.Limitless_*", "**", "SimConnect.dll"),
        ):
            try:
                out += sorted(glob.glob(pat, recursive=True))[:3]
            except Exception:
                pass
        seen, uniq = set(), []
        for p in out:
            if p and p not in seen and os.path.exists(p):
                seen.add(p)
                uniq.append(p)
        return uniq

    def _run_msfs(self, fallback_ok):
        try:
            from SimConnect import SimConnect, AircraftRequests
        except Exception:
            if not fallback_ok:                 # only worth saying when MSFS was asked for
                self.status = "SimConnect module not installed (pip install SimConnect)"
            return False

        # SimConnect blocks rather than failing when the simulator is not running, which
        # would leave "Connecting" on screen for ever and stop auto-detection reaching
        # X-Plane. Attempt it on a worker thread and give up after a few seconds.
        def _open(box, path=None):
            try:
                box["sm"] = SimConnect(library_path=path) if path else SimConnect()
                box["dll"] = path
            except Exception as exc:
                box["err"] = str(exc)

        def _try(path=None, timeout=6.0):
            box = {}
            t = threading.Thread(target=_open, args=(box,), kwargs={"path": path}, daemon=True)
            t.start()
            t.join(timeout)
            if t.is_alive():
                box["err"] = "timed out waiting for SimConnect"
            return box

        self.status = "Looking for a simulator…"
        sm = None
        errors = []
        first = _try()
        sm, err = first.get("sm"), first.get("err")
        if err:
            errors.append(err)
        # a frozen build may be missing the bundled DLL: look for a usable copy
        if sm is None and any(k in (err or "").lower() for k in ("dynlib", "dll")):
            for dll in self._simconnect_dll_candidates():
                box = _try(dll)
                if box.get("sm"):
                    sm, self.dll_used = box["sm"], dll
                    break
                errors.append(f"{os.path.basename(dll)}: {box.get('err')}")
        if sm is None:
            msg = errors[-1] if errors else "unknown error"
            if "timed out" in msg.lower():
                self.status = ("MSFS/P3D did not respond" if not fallback_ok
                               else "MSFS/P3D not running")
                return False
            if "not running" in msg.lower() or "0x" in msg or "open" in msg.lower():
                self.status = "MSFS/P3D not running, or SimConnect refused the connection"
            elif any(k in msg.lower() for k in ("dynlib", "dll", "not found")):
                self.status = ("SimConnect.dll could not be loaded. Install the MSFS SDK, or copy SimConnect.dll "
                               "next to Operator.exe, then press Connect again.")
            else:
                self.status = "MSFS not running" if fallback_ok else f"SimConnect: {msg}"
            return False
        aq = AircraftRequests(sm, _time=200)
        vs_scale = None          # 1 = already fpm, 60 = reported in feet per second
        prev_alt = prev_t = None
        derived_hist = []
        att_peak = 0.0           # largest attitude magnitude seen, for the radians/degrees test
        # source and connected are set by _claim when real data arrives
        # source and connected are set by _claim when real data arrives
        # No probe here: the sample loop below claims the connection the moment real data
        # arrives, so a session that opens but stays silent simply never wins, and the
        # X-Plane listener running alongside it can take over instead.
        if not fallback_ok:
            self.status = "SimConnect open — waiting for data (is a flight loaded?)"

        def g(name, default=0.0):
            try:
                v = aq.get(name)
                return default if v is None else v
            except Exception:
                return default

        try:
            while not self._stop.is_set():
                if self._winner and self._winner != "msfs":
                    return                      # another simulator answered first

                now_t = time.time()
                alt = g("PLANE_ALTITUDE")
                vs_raw = g("VERTICAL_SPEED")

                # rate of climb straight from the altitude trace: independent of whatever
                # units the simulator reports, and the yardstick we calibrate against
                derived = None
                if prev_alt is not None and prev_t is not None and now_t > prev_t:
                    derived = (alt - prev_alt) / (now_t - prev_t) * 60.0
                prev_alt, prev_t = alt, now_t

                if vs_scale is None and derived is not None and abs(derived) > 400:
                    derived_hist.append((vs_raw, derived))
                    vs_scale = vs_units(derived_hist)
                    if vs_scale is not None:
                        self.status = (self.status.split(" — ")[0] +
                                       f" — vertical speed in {'ft/s' if vs_scale == 60.0 else 'fpm'}")

                vs = vs_raw * (vs_scale if vs_scale is not None else 1.0)
                # the altitude trace is the referee: if the scaled figure disagrees wildly
                # with what the aeroplane is actually doing, the trace wins
                if derived is not None and abs(derived) < 6000:
                    if abs(vs) > 12000 or abs(vs) > 3 * max(300.0, abs(derived)):
                        vs = derived

                hdg_raw = abs(g("PLANE_HEADING_DEGREES_MAGNETIC"))
                pitch_raw, bank_raw = g("PLANE_PITCH_DEGREES"), g("PLANE_BANK_DEGREES")
                att_peak = max(att_peak, abs(pitch_raw), abs(bank_raw))
                asc = angle_scale(att_peak)
                pitch, bank = -pitch_raw * asc, -bank_raw * asc

                gal = g("FUEL_TOTAL_QUANTITY")
                wpg = g("FUEL_WEIGHT_PER_GALLON", 6.7) or 6.7
                s = dict(
                    lat=g("PLANE_LATITUDE"), lon=g("PLANE_LONGITUDE"),
                    alt_ft=alt, agl_ft=g("PLANE_ALT_ABOVE_GROUND"),
                    ias=g("AIRSPEED_INDICATED"), gs=g("GROUND_VELOCITY"),
                    vs=vs,
                    hdg=(g("PLANE_HEADING_DEGREES_MAGNETIC") * (57.29578 if hdg_raw <= 6.3 else 1.0)) % 360,
                    on_ground=bool(g("SIM_ON_GROUND")),
                    fuel_lbs=gal * wpg, g=g("G_FORCE", 1.0),
                    eng_on=bool(g("GENERAL_ENG_COMBUSTION:1")),
                    park_brake=bool(g("BRAKE_PARKING_POSITION")),
                    gear=float(g("GEAR_HANDLE_POSITION", 1.0)),
                    paused=False, ts=time.time(),
                    pitch=pitch, bank=bank,
                    wind_kt=g("AMBIENT_WIND_VELOCITY"), wind_dir=g("AMBIENT_WIND_DIRECTION"),
                    zulu_sec=g("ZULU_TIME"), zulu_doy=int(g("ZULU_DAY_OF_YEAR")), zulu_year=int(g("ZULU_YEAR")),
                )
                # only a sample with real numbers in it counts as a working link
                if s.get("lat") is None or s.get("lon") is None or s.get("alt_ft") is None \
                        or (s["lat"] == 0 and s["lon"] == 0):
                    time.sleep(0.5)
                    continue
                if not self._claim("msfs"):
                    return
                with self._lock:
                    self.sample = s
                    self.last_data = time.time()
                time.sleep(1.0)
        except Exception as e:
            self.status = f"SimConnect lost: {e}"
        finally:
            try:
                sm.exit()
            except Exception:
                pass
            if self._winner in (None, "msfs"):      # do not clear another source's connection
                self.connected = False
        return True

    def _run_fsuipc(self):
        """Fallback via FSUIPC offsets (needs 'pip install fsuipc' and FSUIPC4/5/6/7 running). Untested here; offsets per FSUIPC SDK."""
        try:
            import fsuipc
        except Exception:
            self.status = "fsuipc module not installed (pip install fsuipc)"
            return
        try:
            conn = fsuipc.FSUIPC()
        except Exception as e:
            self.status = f"FSUIPC not running: {e}"
            return
        prep = conn.prepare_data([(0x0560, "l"), (0x0568, "l"), (0x0570, "l"), (0x0020, "u"), (0x02BC, "d"), (0x02B4, "d"), (0x02C8, "d"),
                                  (0x0580, "u"), (0x0366, "H"), (0x0AF4, "H"), (0x126C, "d"), (0x11BA, "H"), (0x0BC8, "H"), (0x0BEC, "d"),
                                  (0x0894, "H"), (0x0578, "d"), (0x057C, "d"), (0x0E90, "H"), (0x0E92, "H"), (0x0264, "H"), (0x023B, "b"), (0x023C, "b"), (0x023D, "b")], True)
        self.source, self.connected, self.status = "fsuipc", True, "Connected via FSUIPC"
        try:
            while not self._stop.is_set():
                r = conn.read(prep)
                lat = r[0] * 90.0 / (10001750.0 * 65536.0 * 65536.0)
                lon = r[1] * 360.0 / (65536.0 ** 4)
                alt_m = r[2] / 65536.0 / 65536.0
                s = dict(lat=lat, lon=lon, alt_ft=alt_m * M_TO_FT, agl_ft=(alt_m - r[3] / 256.0) * M_TO_FT, ias=r[4] / 128.0,
                         gs=r[5] / 65536.0 * MS_TO_KT, vs=r[6] / 256.0 * 60 * M_TO_FT, hdg=r[7] * 360.0 / (65536.0 ** 2) % 360,
                         on_ground=r[8] == 1, fuel_lbs=r[10] * (r[9] / 256.0) if r[10] < 100000 else 0.0, g=r[11] / 624.0 if r[11] else 1.0,
                         eng_on=r[12] != 0, park_brake=r[14] > 30000, gear=r[13] / 16383.0, paused=r[19] == 1,
                         pitch=-r[15] * 360.0 / (65536.0 ** 2), bank=-r[16] * 360.0 / (65536.0 ** 2), wind_kt=r[17], wind_dir=r[18] * 360.0 / 65536.0,
                         zulu_sec=r[20] * 3600 + r[21] * 60 + r[22], zulu_doy=0, zulu_year=0, ts=time.time())
                if not self._claim("fsuipc"):
                    return
                with self._lock:
                    self.sample = s
                    self.last_data = time.time()
                time.sleep(1.0)
        except Exception as e:
            self.status = f"FSUIPC lost: {e}"
        finally:
            try:
                conn.close()
            except Exception:
                pass
            if self._winner in (None, "fsuipc"):      # do not clear another source's connection
                self.connected = False

    def _run_xplane(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        sock.bind(("0.0.0.0", 0))
        dest = (self.xp_host, self.xp_port)

        def subscribe(freq):
            for i, dr in enumerate(XP_DATAREFS):
                msg = struct.pack("<5sii400s", b"RREF\x00", freq, i, dr.encode())
                sock.sendto(msg, dest)

        subscribe(1)
        # source and connected are set by _claim when real data arrives
        local_port = sock.getsockname()[1]
        started = time.time()
        packets = 0
        subs = 1
        self.status = f"Waiting for X-Plane on {self.xp_host}:{self.xp_port}"
        self.xp_diag = dict(local_port=local_port, packets=0, subscriptions=1, datarefs=len(XP_DATAREFS))
        values = {}
        last_rx = 0
        began = time.time()
        warned = False
        try:
            while not self._stop.is_set():
                if self._winner and self._winner != "xplane":
                    return                      # another simulator answered first
                if not warned and not self.connected and time.time() - began > 20 and self._only == "xplane":
                    warned = True
                    self.status = (f"No data from X-Plane on {self.xp_host}:{self.xp_port} after 20 seconds — "
                                   "check the aircraft is loaded, and that Operator is allowed through the firewall")
                try:
                    data, _ = sock.recvfrom(4096)
                except socket.timeout:
                    if self.connected and time.time() - last_rx > 6 and self._winner in (None, "xplane"):
                        self.connected = False
                        self.status = "X-Plane stopped sending data"
                    if time.time() - last_rx > 15:
                        subscribe(1)
                        subs += 1
                    # nothing at all after a while: say what is most likely wrong
                    if not packets and not self.connected and time.time() - started > 12 \
                            and self._winner in (None, "xplane"):
                        self.status = (f"No reply from X-Plane. Asked {self.xp_host}:{self.xp_port} for data "
                                       f"{subs} time(s) and heard nothing on port {local_port}. "
                                       "Check X-Plane is running with a flight loaded, that Settings → Network → "
                                       "\"Accept incoming connections\" is ticked, and that Windows Firewall is not "
                                       "blocking Operator.")
                    self.xp_diag.update(packets=packets, subscriptions=subs, waiting_s=int(time.time() - started))
                    continue
                if not data.startswith(b"RREF"):
                    continue
                packets += 1
                if packets == 1:
                    self._log_first_packet(len(data))
                last_rx = time.time()
                self.xp_diag.update(packets=packets, waiting_s=0)
                body = data[5:]
                for off in range(0, len(body) - 7, 8):
                    idx, val = struct.unpack("<if", body[off:off + 8])
                    values[idx] = val
                if len(values) < 10:
                    continue
                # the claim below decides who owns the link
                v = lambda i, d=0.0: values.get(i, d)
                s = dict(
                    lat=v(0), lon=v(1), alt_ft=v(2) * M_TO_FT, agl_ft=v(3) * M_TO_FT,
                    ias=v(4), gs=v(5) * MS_TO_KT, vs=v(6), hdg=v(7) % 360,
                    on_ground=v(8) > 0.5, fuel_lbs=v(9) * LBS_PER_KG, g=v(10, 1.0),
                    eng_on=v(11) > 0.5, park_brake=v(12) > 0.5, gear=v(13, 1.0),
                    paused=v(14) > 0.5, ts=time.time(),
                    pitch=v(15), bank=v(16), wind_kt=v(17), wind_dir=v(18),
                    zulu_sec=v(19), zulu_doy=int(v(20)) + 1, zulu_year=0,
                )
                if s.get("lat") is None or s.get("lon") is None:
                    continue
                if not self._claim("xplane"):
                    return
                with self._lock:
                    self.sample = s
                    self.last_data = time.time()
        finally:
            try:
                subscribe(0)
            except Exception:
                pass
            sock.close()
            if self._winner in (None, "xplane"):      # do not clear another source's connection
                self.connected = False
