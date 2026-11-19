"""Static reference data for Operator.

Aircraft performance figures are typical published values (cruise TAS,
still-air range with typical payload, average block fuel burn). Lease
rates and values are representative market figures in USD.
"""
import math

# code: name, mfr, cat, rating family, cruise kt, range nm, burn lb/hr,
#       MTOW kg, seats, cargo, value low/high (M USD), lease/mo, ACMI $/BH,
#       maintenance reserve $/FH, VMO kias
AIRCRAFT = {
    "AT76": dict(name="ATR 72-600", mfr="ATR", cat="Turboprop", family="ATR", cruise=275, range_nm=825, burn=1400, mtow_kg=23000, seats=72, cargo=False, value=(11.5, 19.0), lease=95000, rate=1350, mx_fh=210, vmo=250),
    "DH8D": dict(name="De Havilland Dash 8-400", mfr="De Havilland Canada", cat="Turboprop", family="Q400", cruise=360, range_nm=1100, burn=1900, mtow_kg=29574, seats=78, cargo=False, value=(9.5, 16.5), lease=85000, rate=1450, mx_fh=240, vmo=245),
    "CRJ9": dict(name="Bombardier CRJ900", mfr="Bombardier", cat="Regional", family="CRJ", cruise=447, range_nm=1550, burn=2600, mtow_kg=38330, seats=90, cargo=False, value=(13.0, 22.0), lease=120000, rate=1900, mx_fh=330, vmo=330),
    "E190": dict(name="Embraer E190", mfr="Embraer", cat="Regional", family="E-Jet", cruise=447, range_nm=2400, burn=3000, mtow_kg=51800, seats=100, cargo=False, value=(15.0, 26.0), lease=130000, rate=2100, mx_fh=360, vmo=320),
    "E195": dict(name="Embraer E195", mfr="Embraer", cat="Regional", family="E-Jet", cruise=447, range_nm=2200, burn=3200, mtow_kg=52290, seats=118, cargo=False, value=(16.0, 28.0), lease=140000, rate=2200, mx_fh=370, vmo=320),
    "A319": dict(name="Airbus A319-100", mfr="Airbus", cat="Narrowbody", family="A320", cruise=447, range_nm=3750, burn=4700, mtow_kg=75500, seats=144, cargo=False, value=(13.0, 24.0), lease=140000, rate=2700, mx_fh=520, vmo=350),
    "A320": dict(name="Airbus A320-200", mfr="Airbus", cat="Narrowbody", family="A320", cruise=447, range_nm=3300, burn=5300, mtow_kg=78000, seats=180, cargo=False, value=(19.0, 38.0), lease=200000, rate=2900, mx_fh=560, vmo=350),
    "A20N": dict(name="Airbus A320neo", mfr="Airbus", cat="Narrowbody", family="A320", cruise=447, range_nm=3500, burn=4500, mtow_kg=79000, seats=186, cargo=False, value=(40.0, 53.0), lease=330000, rate=3400, mx_fh=540, vmo=350),
    "A321": dict(name="Airbus A321-200", mfr="Airbus", cat="Narrowbody", family="A320", cruise=447, range_nm=3200, burn=6200, mtow_kg=93500, seats=220, cargo=False, value=(27.0, 45.0), lease=260000, rate=3400, mx_fh=610, vmo=350),
    "A21N": dict(name="Airbus A321neo", mfr="Airbus", cat="Narrowbody", family="A320", cruise=447, range_nm=4000, burn=5100, mtow_kg=97000, seats=236, cargo=False, value=(54.0, 66.0), lease=400000, rate=4000, mx_fh=600, vmo=350),
    "B737": dict(name="Boeing 737-700", mfr="Boeing", cat="Narrowbody", family="B737", cruise=450, range_nm=3000, burn=4700, mtow_kg=70080, seats=149, cargo=False, value=(13.0, 22.0), lease=150000, rate=2600, mx_fh=520, vmo=340),
    "B738": dict(name="Boeing 737-800", mfr="Boeing", cat="Narrowbody", family="B737", cruise=450, range_nm=2900, burn=5400, mtow_kg=79010, seats=189, cargo=False, value=(21.0, 40.0), lease=220000, rate=3000, mx_fh=560, vmo=340),
    "B739": dict(name="Boeing 737-900ER", mfr="Boeing", cat="Narrowbody", family="B737", cruise=450, range_nm=2950, burn=5800, mtow_kg=85130, seats=220, cargo=False, value=(27.0, 42.0), lease=250000, rate=3300, mx_fh=590, vmo=340),
    "B38M": dict(name="Boeing 737 MAX 8", mfr="Boeing", cat="Narrowbody", family="B737", cruise=450, range_nm=3500, burn=4600, mtow_kg=82190, seats=189, cargo=False, value=(44.0, 56.0), lease=340000, rate=3600, mx_fh=540, vmo=340),
    "B752": dict(name="Boeing 757-200", mfr="Boeing", cat="Narrowbody", family="B757/767", cruise=460, range_nm=3900, burn=7600, mtow_kg=115680, seats=239, cargo=False, value=(7.5, 16.0), lease=130000, rate=3800, mx_fh=720, vmo=350),
    "B763": dict(name="Boeing 767-300ER", mfr="Boeing", cat="Widebody", family="B757/767", cruise=460, range_nm=5900, burn=11000, mtow_kg=186880, seats=269, cargo=False, value=(11.0, 25.0), lease=250000, rate=5500, mx_fh=980, vmo=360),
    "B76F": dict(name="Boeing 767-300F", mfr="Boeing", cat="Widebody", family="B757/767", cruise=460, range_nm=3250, burn=11000, mtow_kg=186880, seats=0, cargo=True, value=(24.0, 45.0), lease=380000, rate=6800, mx_fh=980, vmo=360),
    "A332": dict(name="Airbus A330-200", mfr="Airbus", cat="Widebody", family="A330/A350", cruise=470, range_nm=7250, burn=12500, mtow_kg=242000, seats=293, cargo=False, value=(28.0, 55.0), lease=350000, rate=6000, mx_fh=1100, vmo=330),
    "A333": dict(name="Airbus A330-300", mfr="Airbus", cat="Widebody", family="A330/A350", cruise=470, range_nm=6350, burn=13000, mtow_kg=242000, seats=335, cargo=False, value=(33.0, 65.0), lease=420000, rate=6500, mx_fh=1150, vmo=330),
    "A339": dict(name="Airbus A330-900", mfr="Airbus", cat="Widebody", family="A330/A350", cruise=470, range_nm=7200, burn=11500, mtow_kg=251000, seats=300, cargo=False, value=(88.0, 116.0), lease=800000, rate=8500, mx_fh=1050, vmo=330),
    "A359": dict(name="Airbus A350-900", mfr="Airbus", cat="Widebody", family="A330/A350", cruise=488, range_nm=8100, burn=12800, mtow_kg=280000, seats=325, cargo=False, value=(108.0, 152.0), lease=1000000, rate=10000, mx_fh=1200, vmo=340),
    "B772": dict(name="Boeing 777-200ER", mfr="Boeing", cat="Widebody", family="B777/787", cruise=490, range_nm=7700, burn=16000, mtow_kg=297550, seats=314, cargo=False, value=(22.0, 45.0), lease=400000, rate=7500, mx_fh=1500, vmo=330),
    "B77W": dict(name="Boeing 777-300ER", mfr="Boeing", cat="Widebody", family="B777/787", cruise=490, range_nm=7370, burn=18000, mtow_kg=351530, seats=396, cargo=False, value=(65.0, 120.0), lease=900000, rate=9500, mx_fh=1700, vmo=330),
    # ---- business aircraft, for charter work
    "PC12": dict(name="Pilatus PC-12 NGX", mfr="Pilatus", cat="Turboprop", family="PC-12",
                 cruise=290, range_nm=1800, burn=430, mtow_kg=4740, seats=8, cargo=False, charter=True,
                 value=(4.5, 6.2), lease=42000, rate=1450, mx_fh=210, vmo=240),
    "BE20": dict(name="Beechcraft King Air 350i", mfr="Textron", cat="Turboprop", family="King Air",
                 cruise=300, range_nm=1800, burn=700, mtow_kg=6800, seats=9, cargo=False, charter=True,
                 value=(3.0, 5.5), lease=38000, rate=1600, mx_fh=240, vmo=263),
    "E55P": dict(name="Embraer Phenom 300E", mfr="Embraer", cat="Light jet", family="Phenom",
                 cruise=440, range_nm=2010, burn=1100, mtow_kg=8150, seats=9, cargo=False, charter=True,
                 value=(9.0, 12.5), lease=78000, rate=2600, mx_fh=310, vmo=320),
    "C25C": dict(name="Cessna Citation CJ4", mfr="Textron", cat="Light jet", family="Citation",
                 cruise=430, range_nm=1930, burn=1050, mtow_kg=7761, seats=9, cargo=False, charter=True,
                 value=(7.0, 10.5), lease=68000, rate=2400, mx_fh=290, vmo=305),
    "H25B": dict(name="Hawker 800XP", mfr="Hawker Beechcraft", cat="Midsize jet", family="Hawker",
                 cruise=447, range_nm=2450, burn=1400, mtow_kg=12700, seats=8, cargo=False, charter=True,
                 value=(2.2, 5.5), lease=52000, rate=2900, mx_fh=300, vmo=335, out_of_production=True),
    "C56X": dict(name="Cessna Citation XLS+", mfr="Textron", cat="Midsize jet", family="Citation",
                 cruise=433, range_nm=2100, burn=1450, mtow_kg=9163, seats=9, cargo=False, charter=True,
                 value=(8.5, 13.0), lease=88000, rate=3100, mx_fh=340, vmo=305),
    "E545": dict(name="Embraer Praetor 600", mfr="Embraer", cat="Super-midsize jet", family="Praetor",
                 cruise=466, range_nm=4018, burn=1750, mtow_kg=19200, seats=12, cargo=False, charter=True,
                 value=(18.0, 24.0), lease=155000, rate=4300, mx_fh=430, vmo=320),
    "CL35": dict(name="Bombardier Challenger 350", mfr="Bombardier", cat="Super-midsize jet", family="Challenger",
                 cruise=470, range_nm=3200, burn=1900, mtow_kg=18416, seats=10, cargo=False, charter=True,
                 value=(15.0, 22.0), lease=150000, rate=4500, mx_fh=440, vmo=320),
    "GLF6": dict(name="Gulfstream G650ER", mfr="Gulfstream", cat="Heavy jet", family="Gulfstream",
                 cruise=516, range_nm=7500, burn=3400, mtow_kg=45178, seats=16, cargo=False, charter=True,
                 value=(40.0, 62.0), lease=390000, rate=9500, mx_fh=780, vmo=340),
    "GL7T": dict(name="Bombardier Global 7500", mfr="Bombardier", cat="Heavy jet", family="Global",
                 cruise=516, range_nm=7700, burn=3500, mtow_kg=51250, seats=17, cargo=False, charter=True,
                 value=(45.0, 70.0), lease=420000, rate=9900, mx_fh=810, vmo=340),
    "FA8X": dict(name="Dassault Falcon 8X", mfr="Dassault", cat="Heavy jet", family="Falcon",
                 cruise=488, range_nm=6450, burn=2900, mtow_kg=33113, seats=14, cargo=False, charter=True,
                 value=(32.0, 48.0), lease=330000, rate=8200, mx_fh=690, vmo=340),

    "B75F": dict(name="Boeing 757-200PF", mfr="Boeing", cat="Narrowbody", family="B757/767",
                 cruise=460, range_nm=3150, burn=6800, mtow_kg=115680, seats=0, cargo=True,
                 value=(9.0, 18.0), lease=210000, rate=5200, mx_fh=820, vmo=350, out_of_production=True),
    "B38F": dict(name="Boeing 737-800BCF", mfr="Boeing", cat="Narrowbody", family="B737",
                 cruise=447, range_nm=2000, burn=5100, mtow_kg=79010, seats=0, cargo=True,
                 value=(16.0, 24.0), lease=230000, rate=4700, mx_fh=700, vmo=340, out_of_production=True),
    "AT7F": dict(name="ATR 72-600F", mfr="ATR", cat="Turboprop", family="ATR",
                 cruise=275, range_nm=900, burn=1250, mtow_kg=23000, seats=0, cargo=True,
                 value=(14.0, 20.0), lease=115000, rate=2100, mx_fh=420, vmo=250),
    # ---- small freighters and classics: feeder work, islands and night mail
    "DC3": dict(name="Douglas DC-3", mfr="Douglas", cat="Turboprop", family="DC-3",
                cruise=150, range_nm=1000, burn=900, mtow_kg=11431, seats=0, cargo=True,
                value=(0.3, 1.2), lease=14000, rate=900, mx_fh=260, vmo=190, out_of_production=True),
    "C208": dict(name="Cessna 208B Grand Caravan", mfr="Textron", cat="Turboprop", family="Caravan",
                 cruise=175, range_nm=900, burn=380, mtow_kg=4110, seats=0, cargo=True,
                 value=(1.4, 2.8), lease=22000, rate=750, mx_fh=150, vmo=175),
    "DHC6": dict(name="De Havilland Twin Otter 300", mfr="Viking", cat="Turboprop", family="Twin Otter",
                 cruise=155, range_nm=700, burn=600, mtow_kg=5670, seats=0, cargo=True,
                 value=(1.8, 4.5), lease=28000, rate=850, mx_fh=210, vmo=170),
    "SF34": dict(name="Saab 340B Cargo", mfr="Saab", cat="Turboprop", family="Saab 340",
                 cruise=280, range_nm=850, burn=900, mtow_kg=13155, seats=0, cargo=True,
                 value=(1.2, 3.0), lease=34000, rate=1100, mx_fh=280, vmo=250, out_of_production=True),
    "AT43": dict(name="ATR 42-300F", mfr="ATR", cat="Turboprop", family="ATR",
                 cruise=265, range_nm=840, burn=1050, mtow_kg=18600, seats=0, cargo=True,
                 value=(1.5, 4.0), lease=42000, rate=1300, mx_fh=330, vmo=250, out_of_production=True),
    "CR2F": dict(name="Bombardier CRJ200 SF", mfr="Bombardier", cat="Regional", family="CRJ",
                 cruise=424, range_nm=1100, burn=2600, mtow_kg=24040, seats=0, cargo=True,
                 value=(3.0, 5.5), lease=48000, rate=2400, mx_fh=380, vmo=315, out_of_production=True),
    "A306": dict(name="Airbus A300-600F", mfr="Airbus", cat="Widebody", family="A300",
                 cruise=460, range_nm=2650, burn=13200, mtow_kg=170500, seats=0, cargo=True,
                 value=(6.0, 13.0), lease=185000, rate=6800, mx_fh=1150, vmo=335, out_of_production=True),
    "B722": dict(name="Boeing 727-200F", mfr="Boeing", cat="Narrowbody", family="B727",
                 cruise=430, range_nm=2100, burn=10500, mtow_kg=95000, seats=0, cargo=True,
                 value=(1.2, 3.5), lease=70000, rate=4200, mx_fh=980, vmo=350, out_of_production=True),
    "E19F": dict(name="Embraer E190F", mfr="Embraer", cat="Regional", family="E-Jet",
                 cruise=447, range_nm=2450, burn=4300, mtow_kg=51800, seats=0, cargo=True,
                 value=(14.0, 20.0), lease=125000, rate=3400, mx_fh=520, vmo=320, out_of_production=True),
    "E95F": dict(name="Embraer E195F", mfr="Embraer", cat="Regional", family="E-Jet",
                 cruise=447, range_nm=2300, burn=4600, mtow_kg=52290, seats=0, cargo=True,
                 value=(15.0, 21.0), lease=132000, rate=3600, mx_fh=545, vmo=320, out_of_production=True),
    "A21F": dict(name="Airbus A321P2F", mfr="Airbus", cat="Narrowbody", family="A320",
                 cruise=455, range_nm=2300, burn=5400, mtow_kg=93500, seats=0, cargo=True,
                 value=(28.0, 38.0), lease=290000, rate=5200, mx_fh=700, vmo=350, out_of_production=True),
    "A33F": dict(name="Airbus A330-300P2F", mfr="Airbus", cat="Widebody", family="A330/A350",
                 cruise=470, range_nm=3400, burn=12500, mtow_kg=233000, seats=0, cargo=True,
                 value=(45.0, 62.0), lease=560000, rate=9200, mx_fh=1300, vmo=330, out_of_production=True),
    "MD11": dict(name="McDonnell Douglas MD-11F", mfr="McDonnell Douglas", cat="Widebody", family="MD-11",
                 cruise=473, range_nm=3600, burn=19000, mtow_kg=286000, seats=0, cargo=True,
                 value=(9.0, 17.0), lease=270000, rate=8600, mx_fh=1450, vmo=365, out_of_production=True),
    "B77F": dict(name="Boeing 777F", mfr="Boeing", cat="Widebody", family="B777/787", cruise=490, range_nm=4970, burn=17500, mtow_kg=347800, seats=0, cargo=True, value=(95.0, 140.0), lease=1100000, rate=13000, mx_fh=1650, vmo=330),
    "B788": dict(name="Boeing 787-8", mfr="Boeing", cat="Widebody", family="B777/787", cruise=488, range_nm=7300, burn=11500, mtow_kg=227930, seats=242, cargo=False, value=(68.0, 100.0), lease=700000, rate=8000, mx_fh=1150, vmo=330),
    "B789": dict(name="Boeing 787-9", mfr="Boeing", cat="Widebody", family="B777/787", cruise=488, range_nm=7600, burn=12300, mtow_kg=254010, seats=296, cargo=False, value=(88.0, 132.0), lease=900000, rate=9000, mx_fh=1200, vmo=330),
    "B744": dict(name="Boeing 747-400F", mfr="Boeing", cat="Widebody", family="B747", cruise=490, range_nm=4400, burn=22000, mtow_kg=396890, seats=0, cargo=True, value=(18.0, 40.0), lease=450000, rate=12000, mx_fh=2100, vmo=365),
    "B748": dict(name="Boeing 747-8F", mfr="Boeing", cat="Widebody", family="B747", cruise=490, range_nm=4390, burn=23000, mtow_kg=447700, seats=0, cargo=True, value=(120.0, 175.0), lease=1400000, rate=15500, mx_fh=2300, vmo=365),
}

FAMILIES = sorted(set(a["family"] for a in AIRCRAFT.values()))

# One type rating covers a whole family, as it does in real life: an A320 rating
# covers the A318 to A321 in both ceo and neo, a B757/767 rating covers both.
FAMILY_TYPES = {f: sorted(k for k, a in AIRCRAFT.items() if a["family"] == f) for f in FAMILIES}
FAMILY_COVERS = {f: ", ".join(AIRCRAFT[t]["name"] for t in ts) for f, ts in FAMILY_TYPES.items()}

# ICAO|Name|City|Country|lat|lon
_AIRPORTS = """
KATL|Hartsfield-Jackson Atlanta Intl|Atlanta|US|33.6407|-84.4277
KJFK|John F. Kennedy Intl|New York|US|40.6413|-73.7781
KEWR|Newark Liberty Intl|Newark|US|40.6895|-74.1745
KBOS|Logan Intl|Boston|US|42.3656|-71.0096
KORD|O'Hare Intl|Chicago|US|41.9742|-87.9073
KDFW|Dallas/Fort Worth Intl|Dallas|US|32.8998|-97.0403
KDEN|Denver Intl|Denver|US|39.8561|-104.6737
KLAX|Los Angeles Intl|Los Angeles|US|33.9416|-118.4085
KSFO|San Francisco Intl|San Francisco|US|37.6213|-122.3790
KSEA|Seattle-Tacoma Intl|Seattle|US|47.4502|-122.3088
KMIA|Miami Intl|Miami|US|25.7959|-80.2870
KMCO|Orlando Intl|Orlando|US|28.4312|-81.3081
KSFB|Orlando Sanford Intl|Sanford|US|28.7776|-81.2375
KDAB|Daytona Beach Intl|Daytona Beach|US|29.1799|-81.0581
KTPA|Tampa Intl|Tampa|US|27.9755|-82.5332
KFLL|Fort Lauderdale-Hollywood Intl|Fort Lauderdale|US|26.0726|-80.1527
KIAH|George Bush Intercontinental|Houston|US|29.9902|-95.3368
KPHX|Phoenix Sky Harbor Intl|Phoenix|US|33.4373|-112.0078
KLAS|Harry Reid Intl|Las Vegas|US|36.0840|-115.1537
KMSP|Minneapolis-St Paul Intl|Minneapolis|US|44.8848|-93.2223
KDTW|Detroit Metropolitan|Detroit|US|42.2162|-83.3554
KCLT|Charlotte Douglas Intl|Charlotte|US|35.2140|-80.9431
KSLC|Salt Lake City Intl|Salt Lake City|US|40.7899|-111.9791
KSDF|Louisville Muhammad Ali Intl|Louisville|US|38.1744|-85.7360
KMEM|Memphis Intl|Memphis|US|35.0424|-89.9767
KCVG|Cincinnati/Northern Kentucky Intl|Cincinnati|US|39.0488|-84.6678
KIND|Indianapolis Intl|Indianapolis|US|39.7173|-86.2944
KMOB|Mobile Regional|Mobile|US|30.6914|-88.2428
KBFM|Mobile Downtown (Brookley)|Mobile|US|30.6268|-88.0681
KPNS|Pensacola Intl|Pensacola|US|30.4734|-87.1866
KGSO|Piedmont Triad Intl|Greensboro|US|36.0978|-79.9373
KOKC|Will Rogers World|Oklahoma City|US|35.3931|-97.6007
KRFD|Chicago Rockford Intl|Rockford|US|42.1954|-89.0972
KMZJ|Pinal Airpark|Marana|US|32.5106|-111.3275
KROW|Roswell Air Center|Roswell|US|33.3016|-104.5307
KVCV|Southern California Logistics|Victorville|US|34.5975|-117.3830
KMHV|Mojave Air and Space Port|Mojave|US|35.0594|-118.1520
KIGM|Kingman|Kingman|US|35.2595|-113.9380
KGYR|Phoenix Goodyear|Goodyear|US|33.4228|-112.3759
KPAE|Paine Field|Everett|US|47.9063|-122.2815
KRNT|Renton Municipal|Renton|US|47.4931|-122.2158
KCHS|Charleston Intl|Charleston|US|32.8986|-80.0405
KBWI|Baltimore/Washington Intl|Baltimore|US|39.1754|-76.6684
KIAD|Washington Dulles Intl|Washington|US|38.9531|-77.4565
KPHL|Philadelphia Intl|Philadelphia|US|39.8744|-75.2424
KSAN|San Diego Intl|San Diego|US|32.7338|-117.1933
KPDX|Portland Intl|Portland|US|45.5898|-122.5951
KAUS|Austin-Bergstrom Intl|Austin|US|30.1975|-97.6664
KSTL|St. Louis Lambert Intl|St. Louis|US|38.7487|-90.3700
KMCI|Kansas City Intl|Kansas City|US|39.2976|-94.7139
KMKE|Milwaukee Mitchell Intl|Milwaukee|US|42.9472|-87.8966
KPIT|Pittsburgh Intl|Pittsburgh|US|40.4915|-80.2329
KCLE|Cleveland Hopkins Intl|Cleveland|US|41.4117|-81.8498
KRDU|Raleigh-Durham Intl|Raleigh|US|35.8801|-78.7880
KBNA|Nashville Intl|Nashville|US|36.1263|-86.6774
KMSY|Louis Armstrong New Orleans Intl|New Orleans|US|29.9934|-90.2580
KTUL|Tulsa Intl|Tulsa|US|36.1984|-95.8881
KSAT|San Antonio Intl|San Antonio|US|29.5337|-98.4698
PHNL|Daniel K. Inouye Intl|Honolulu|US|21.3187|-157.9225
PANC|Ted Stevens Anchorage Intl|Anchorage|US|61.1743|-149.9983
CYYZ|Toronto Pearson Intl|Toronto|CA|43.6777|-79.6248
CYUL|Montréal-Trudeau Intl|Montréal|CA|45.4706|-73.7408
CYVR|Vancouver Intl|Vancouver|CA|49.1947|-123.1792
CYYC|Calgary Intl|Calgary|CA|51.1215|-114.0076
CYWG|Winnipeg Richardson Intl|Winnipeg|CA|49.9100|-97.2399
CYHZ|Halifax Stanfield Intl|Halifax|CA|44.8808|-63.5086
CYEG|Edmonton Intl|Edmonton|CA|53.3097|-113.5800
CYOW|Ottawa Macdonald-Cartier Intl|Ottawa|CA|45.3225|-75.6692
MMMX|Mexico City Intl|Mexico City|MX|19.4363|-99.0721
MMUN|Cancún Intl|Cancún|MX|21.0365|-86.8771
MMGL|Guadalajara Intl|Guadalajara|MX|20.5218|-103.3111
MSLP|El Salvador Intl|San Salvador|SV|13.4409|-89.0557
MPTO|Tocumen Intl|Panama City|PA|9.0714|-79.3835
MKJP|Norman Manley Intl|Kingston|JM|17.9357|-76.7875
TNCM|Princess Juliana Intl|Sint Maarten|SX|18.0410|-63.1089
TJSJ|Luis Muñoz Marín Intl|San Juan|PR|18.4394|-66.0018
SBGR|São Paulo/Guarulhos Intl|São Paulo|BR|-23.4356|-46.4731
SBKP|Viracopos Intl|Campinas|BR|-23.0075|-47.1345
SBSJ|São José dos Campos|São José dos Campos|BR|-23.2292|-45.8615
SBGL|Rio de Janeiro/Galeão Intl|Rio de Janeiro|BR|-22.8100|-43.2506
SAEZ|Ministro Pistarini Intl|Buenos Aires|AR|-34.8222|-58.5358
SCEL|Arturo Merino Benítez Intl|Santiago|CL|-33.3930|-70.7858
SKBO|El Dorado Intl|Bogotá|CO|4.7016|-74.1469
SPJC|Jorge Chávez Intl|Lima|PE|-12.0219|-77.1143
EGLL|London Heathrow|London|GB|51.4700|-0.4543
EGKK|London Gatwick|London|GB|51.1537|-0.1821
EGGW|London Luton|London|GB|51.8747|-0.3683
EGSS|London Stansted|London|GB|51.8850|0.2350
EGCC|Manchester|Manchester|GB|53.3537|-2.2750
EGNM|Leeds Bradford|Leeds|GB|53.8659|-1.6606
EGBB|Birmingham|Birmingham|GB|52.4539|-1.7480
EGPH|Edinburgh|Edinburgh|GB|55.9500|-3.3725
EGPF|Glasgow|Glasgow|GB|55.8719|-4.4331
EGGD|Bristol|Bristol|GB|51.3827|-2.7191
EGNX|East Midlands|Nottingham|GB|52.8311|-1.3280
EGBP|Cotswold (Kemble)|Kemble|GB|51.6680|-2.0570
EGHH|Bournemouth|Bournemouth|GB|50.7800|-1.8425
EIDW|Dublin|Dublin|IE|53.4264|-6.2499
EINN|Shannon|Shannon|IE|52.7020|-8.9248
LFPG|Paris Charles de Gaulle|Paris|FR|49.0097|2.5479
LFPO|Paris Orly|Paris|FR|48.7262|2.3652
LFMN|Nice Côte d'Azur|Nice|FR|43.6584|7.2159
LFLL|Lyon-Saint Exupéry|Lyon|FR|45.7256|5.0811
LFBO|Toulouse-Blagnac|Toulouse|FR|43.6290|1.3638
LFBD|Bordeaux-Mérignac|Bordeaux|FR|44.8283|-0.7156
LFBT|Tarbes-Lourdes-Pyrénées|Tarbes|FR|43.1787|-0.0064
LFRD|Dinard-Pleurtuit|Dinard|FR|48.5877|-2.0799
LFML|Marseille Provence|Marseille|FR|43.4393|5.2214
LFSB|EuroAirport Basel-Mulhouse|Basel|FR|47.5896|7.5299
EHAM|Amsterdam Schiphol|Amsterdam|NL|52.3086|4.7639
EHEH|Eindhoven|Eindhoven|NL|51.4500|5.3745
EBBR|Brussels|Brussels|BE|50.9014|4.4844
EBLG|Liège|Liège|BE|50.6374|5.4432
EDDF|Frankfurt Main|Frankfurt|DE|50.0379|8.5622
EDDM|Munich|Munich|DE|48.3538|11.7861
EDDH|Hamburg|Hamburg|DE|53.6304|9.9882
EDHI|Hamburg Finkenwerder|Hamburg|DE|53.5353|9.8375
EDDK|Cologne Bonn|Cologne|DE|50.8659|7.1427
EDDL|Düsseldorf|Düsseldorf|DE|51.2895|6.7668
EDDB|Berlin Brandenburg|Berlin|DE|52.3667|13.5033
EDDP|Leipzig/Halle|Leipzig|DE|51.4239|12.2364
EDDS|Stuttgart|Stuttgart|DE|48.6900|9.2220
EDDV|Hannover|Hannover|DE|52.4611|9.6851
EDDN|Nuremberg|Nuremberg|DE|49.4987|11.0669
LSZH|Zürich|Zürich|CH|47.4647|8.5492
LSGG|Geneva|Geneva|CH|46.2381|6.1089
LOWW|Vienna|Vienna|AT|48.1103|16.5697
LOWS|Salzburg|Salzburg|AT|47.7933|13.0043
LKPR|Prague Václav Havel|Prague|CZ|50.1008|14.2600
LKMT|Ostrava Leoš Janáček|Ostrava|CZ|49.6963|18.1111
LHBP|Budapest Ferenc Liszt|Budapest|HU|47.4298|19.2611
LBSF|Sofia|Sofia|BG|42.6967|23.4114
LBBG|Burgas|Burgas|BG|42.5696|27.5152
LROP|Bucharest Henri Coandă|Bucharest|RO|44.5711|26.0850
LYBE|Belgrade Nikola Tesla|Belgrade|RS|44.8184|20.3091
LDZA|Zagreb|Zagreb|HR|45.7429|16.0688
LDSP|Split|Split|HR|43.5389|16.2980
LZIB|Bratislava|Bratislava|SK|48.1700|17.2127
EPWA|Warsaw Chopin|Warsaw|PL|52.1657|20.9671
EPKK|Kraków John Paul II|Kraków|PL|50.0777|19.7848
EETN|Tallinn Lennart Meri|Tallinn|EE|59.4133|24.8328
EVRA|Riga|Riga|LV|56.9236|23.9711
EYVI|Vilnius|Vilnius|LT|54.6341|25.2858
EYKA|Kaunas|Kaunas|LT|54.9639|24.0848
EFHK|Helsinki-Vantaa|Helsinki|FI|60.3172|24.9633
ESSA|Stockholm Arlanda|Stockholm|SE|59.6519|17.9186
ESGG|Gothenburg Landvetter|Gothenburg|SE|57.6628|12.2798
ENGM|Oslo Gardermoen|Oslo|NO|60.1939|11.1004
ENBR|Bergen Flesland|Bergen|NO|60.2934|5.2181
ENZV|Stavanger Sola|Stavanger|NO|58.8767|5.6378
EKCH|Copenhagen Kastrup|Copenhagen|DK|55.6180|12.6508
EKBI|Billund|Billund|DK|55.7403|9.1518
BIKF|Keflavík|Reykjavík|IS|63.9850|-22.6056
LEMD|Madrid-Barajas|Madrid|ES|40.4983|-3.5676
LEBL|Barcelona-El Prat|Barcelona|ES|41.2971|2.0785
LEPA|Palma de Mallorca|Palma|ES|39.5517|2.7388
LEMG|Málaga-Costa del Sol|Málaga|ES|36.6749|-4.4991
LEAL|Alicante-Elche|Alicante|ES|38.2822|-0.5582
LETL|Teruel|Teruel|ES|40.4033|-1.2178
LERL|Ciudad Real Central|Ciudad Real|ES|38.8564|-3.9700
LEIB|Ibiza|Ibiza|ES|38.8729|1.3731
GCLP|Gran Canaria|Las Palmas|ES|27.9319|-15.3866
GCTS|Tenerife South|Tenerife|ES|28.0445|-16.5725
GCLA|La Palma|La Palma|ES|28.6265|-17.7556
LPPT|Lisbon Humberto Delgado|Lisbon|PT|38.7813|-9.1359
LPPR|Porto Francisco Sá Carneiro|Porto|PT|41.2481|-8.6814
LPFR|Faro|Faro|PT|37.0144|-7.9659
LPMA|Madeira|Funchal|PT|32.6979|-16.7745
LIRF|Rome Fiumicino|Rome|IT|41.8003|12.2389
LIMC|Milan Malpensa|Milan|IT|45.6300|8.7231
LIME|Milan Bergamo|Bergamo|IT|45.6739|9.7042
LIPZ|Venice Marco Polo|Venice|IT|45.5053|12.3519
LICJ|Palermo Falcone-Borsellino|Palermo|IT|38.1760|13.0910
LICC|Catania Fontanarossa|Catania|IT|37.4668|15.0664
LIPE|Bologna|Bologna|IT|44.5354|11.2887
LMML|Malta|Luqa|MT|35.8575|14.4775
LGAV|Athens Eleftherios Venizelos|Athens|GR|37.9364|23.9445
LGIR|Heraklion|Heraklion|GR|35.3397|25.1803
LGRP|Rhodes Diagoras|Rhodes|GR|36.4054|28.0862
LGKO|Kos|Kos|GR|36.7933|27.0917
LGTS|Thessaloniki|Thessaloniki|GR|40.5197|22.9709
LTFM|Istanbul|Istanbul|TR|41.2753|28.7519
LTAI|Antalya|Antalya|TR|36.8987|30.8005
LTBS|Dalaman|Dalaman|TR|36.7131|28.7925
LCLK|Larnaca|Larnaca|CY|34.8751|33.6249
LCPH|Paphos|Paphos|CY|34.7180|32.4857
LLBG|Ben Gurion|Tel Aviv|IL|32.0114|34.8867
OJAI|Queen Alia Intl|Amman|JO|31.7226|35.9932
OMAA|Abu Dhabi Intl|Abu Dhabi|AE|24.4331|54.6511
OMDB|Dubai Intl|Dubai|AE|25.2528|55.3644
OMDW|Al Maktoum Intl|Dubai|AE|24.8967|55.1614
OMSJ|Sharjah Intl|Sharjah|AE|25.3286|55.5172
OTHH|Hamad Intl|Doha|QA|25.2731|51.6081
OERK|King Khalid Intl|Riyadh|SA|24.9576|46.6988
OEJN|King Abdulaziz Intl|Jeddah|SA|21.6796|39.1565
OEDF|King Fahd Intl|Dammam|SA|26.4712|49.7979
OBBI|Bahrain Intl|Manama|BH|26.2708|50.6336
OKBK|Kuwait Intl|Kuwait City|KW|29.2266|47.9689
OOMS|Muscat Intl|Muscat|OM|23.5933|58.2844
HECA|Cairo Intl|Cairo|EG|30.1219|31.4056
HEGN|Hurghada Intl|Hurghada|EG|27.1783|33.7994
HAAB|Addis Ababa Bole Intl|Addis Ababa|ET|8.9779|38.7993
HKJK|Jomo Kenyatta Intl|Nairobi|KE|-1.3192|36.9278
FAOR|O. R. Tambo Intl|Johannesburg|ZA|-26.1392|28.2460
FACT|Cape Town Intl|Cape Town|ZA|-33.9648|18.6017
DNMM|Murtala Muhammed Intl|Lagos|NG|6.5774|3.3212
GMMN|Mohammed V Intl|Casablanca|MA|33.3675|-7.5898
GMMX|Marrakesh Menara|Marrakesh|MA|31.6069|-8.0363
DTTA|Tunis-Carthage|Tunis|TN|36.8510|10.2272
DAAG|Algiers Houari Boumediene|Algiers|DZ|36.6910|3.2155
VIDP|Indira Gandhi Intl|Delhi|IN|28.5562|77.1000
VABB|Chhatrapati Shivaji Maharaj Intl|Mumbai|IN|19.0896|72.8656
VOBL|Kempegowda Intl|Bengaluru|IN|13.1986|77.7066
VECC|Netaji Subhas Chandra Bose Intl|Kolkata|IN|22.6547|88.4467
VOMM|Chennai Intl|Chennai|IN|12.9941|80.1709
VCBI|Bandaranaike Intl|Colombo|LK|7.1808|79.8841
VHHH|Hong Kong Intl|Hong Kong|HK|22.3080|113.9185
ZSAM|Xiamen Gaoqi Intl|Xiamen|CN|24.5440|118.1277
ZBAA|Beijing Capital Intl|Beijing|CN|40.0799|116.6031
ZBTJ|Tianjin Binhai Intl|Tianjin|CN|39.1244|117.3462
ZSPD|Shanghai Pudong Intl|Shanghai|CN|31.1434|121.8052
ZGGG|Guangzhou Baiyun Intl|Guangzhou|CN|23.3924|113.2988
RJTT|Tokyo Haneda|Tokyo|JP|35.5494|139.7798
RJAA|Tokyo Narita|Tokyo|JP|35.7720|140.3929
RJBB|Kansai Intl|Osaka|JP|34.4347|135.2440
RKSI|Incheon Intl|Seoul|KR|37.4602|126.4407
RCTP|Taiwan Taoyuan Intl|Taipei|TW|25.0797|121.2342
WSSS|Singapore Changi|Singapore|SG|1.3644|103.9915
WMKK|Kuala Lumpur Intl|Kuala Lumpur|MY|2.7456|101.7099
VTBS|Suvarnabhumi|Bangkok|TH|13.6900|100.7501
WIII|Soekarno-Hatta Intl|Jakarta|ID|-6.1256|106.6559
WADD|Ngurah Rai Intl|Denpasar|ID|-8.7482|115.1672
RPLL|Ninoy Aquino Intl|Manila|PH|14.5086|121.0198
VVTS|Tan Son Nhat Intl|Ho Chi Minh City|VN|10.8188|106.6519
YSSY|Sydney Kingsford Smith|Sydney|AU|-33.9399|151.1753
YMML|Melbourne|Melbourne|AU|-37.6733|144.8433
YBBN|Brisbane|Brisbane|AU|-27.3842|153.1175
YPPH|Perth|Perth|AU|-31.9403|115.9669
YBAS|Alice Springs|Alice Springs|AU|-23.8067|133.9019
YSCB|Canberra|Canberra|AU|-35.3069|149.1950
NZAA|Auckland|Auckland|NZ|-37.0082|174.7920
NZCH|Christchurch|Christchurch|NZ|-43.4894|172.5323
NZWN|Wellington|Wellington|NZ|-41.3272|174.8052
NFFN|Nadi Intl|Nadi|FJ|-17.7554|177.4433
CYQX|Gander Intl|Gander|CA|48.9369|-54.5680
CYYR|Goose Bay|Goose Bay|CA|53.3191|-60.4258
CYFB|Iqaluit|Iqaluit|CA|63.7564|-68.5558
BGSF|Kangerlussuaq|Kangerlussuaq|GL|67.0122|-50.7116
LPLA|Lajes|Terceira|PT|38.7618|-27.0908
LPAZ|Santa Maria|Santa Maria|PT|36.9714|-25.1706
GVAC|Amílcar Cabral Intl|Sal|CV|16.7414|-22.9494
FHAW|Ascension Island|Ascension|SH|-7.9696|-14.3937
FIMP|Sir Seewoosagur Ramgoolam Intl|Mauritius|MU|-20.4302|57.6836
FSIA|Seychelles Intl|Mahé|SC|-4.6743|55.5218
VRMM|Velana Intl|Malé|MV|4.1918|73.5291
OOSA|Salalah|Salalah|OM|17.0387|54.0913
PACD|Cold Bay|Cold Bay|US|55.2061|-162.7254
PAKN|King Salmon|King Salmon|US|58.6768|-156.6492
PMDY|Henderson Field|Midway Atoll|US|28.2017|-177.3811
NSTU|Pago Pago Intl|Pago Pago|AS|-14.3310|-170.7105
NTAA|Faa'a Intl|Papeete|PF|-17.5537|-149.6070
PHTO|Hilo Intl|Hilo|US|19.7214|-155.0485
RJCC|New Chitose|Sapporo|JP|42.7752|141.6923
UHPP|Yelizovo|Petropavlovsk-Kamchatsky|RU|53.1679|158.4536
UHWW|Vladivostok Intl|Vladivostok|RU|43.3990|132.1480
UUEE|Sheremetyevo Intl|Moscow|RU|55.9726|37.4146
UNNT|Tolmachevo|Novosibirsk|RU|55.0126|82.6507
UAAA|Almaty Intl|Almaty|KZ|43.3521|77.0405
UTTT|Tashkent Intl|Tashkent|UZ|41.2579|69.2812
OPKC|Jinnah Intl|Karachi|PK|24.9065|67.1608
OPLA|Allama Iqbal Intl|Lahore|PK|31.5216|74.4036
VGHS|Hazrat Shahjalal Intl|Dhaka|BD|23.8433|90.3978
VNKT|Tribhuvan Intl|Kathmandu|NP|27.6966|85.3591
VYYY|Yangon Intl|Yangon|MM|16.9073|96.1332
ZWWW|Urumqi Diwopu Intl|Urumqi|CN|43.9071|87.4742
ZUUU|Chengdu Shuangliu|Chengdu|CN|30.5785|103.9471
YPDN|Darwin Intl|Darwin|AU|-12.4147|130.8766
YBCS|Cairns|Cairns|AU|-16.8858|145.7553
FALE|King Shaka Intl|Durban|ZA|-29.6144|31.1197
FNLU|Quatro de Fevereiro|Luanda|AO|-8.8584|13.2312
DGAA|Kotoka Intl|Accra|GH|5.6052|-0.1668
GOBD|Blaise Diagne Intl|Dakar|SN|14.6700|-17.0733
HSSK|Khartoum Intl|Khartoum|SD|15.5895|32.5532
HLLT|Tripoli Intl|Tripoli|LY|32.6635|13.1590
SBFZ|Fortaleza Pinto Martins|Fortaleza|BR|-3.7763|-38.5326
SBRF|Recife Guararapes|Recife|BR|-8.1265|-34.9236
SEQM|Mariscal Sucre Intl|Quito|EC|-0.1292|-78.3575
SVMI|Simón Bolívar Intl|Caracas|VE|10.6031|-66.9906
TBPB|Grantley Adams Intl|Bridgetown|BB|13.0746|-59.4925
MDSD|Las Américas Intl|Santo Domingo|DO|18.4297|-69.6689
MUHA|José Martí Intl|Havana|CU|22.9892|-82.4091
UKBB|Boryspil Intl|Kyiv|UA|50.3450|30.8947
OIIE|Imam Khomeini Intl|Tehran|IR|35.4161|51.1522
OAKB|Kabul Intl|Kabul|AF|34.5659|69.2123
UBBB|Heydar Aliyev Intl|Baku|AZ|40.4675|50.0467
UGTB|Tbilisi Intl|Tbilisi|GE|41.6692|44.9547
UMMS|Minsk National|Minsk|BY|53.8825|28.0307
UTDD|Dushanbe Intl|Dushanbe|TJ|38.5433|68.8250
OIMM|Mashhad Intl|Mashhad|IR|36.2352|59.6410
"""

import json as _json
import os as _os
import sys as _sys

_BASE = getattr(_sys, "_MEIPASS", _os.path.dirname(_os.path.abspath(__file__)))

AIRPORTS = {}
# Full large/medium airport set (OurAirports, public domain) if present; curated entries below override names.
_AJ = _os.path.join(_BASE, "airports.json")
if _os.path.exists(_AJ):
    with open(_AJ, encoding="utf-8") as _fh:
        AIRPORTS.update(_json.load(_fh))
_EJ = _os.path.join(_BASE, "elevations.json")
_ELEV = {}
if _os.path.exists(_EJ):
    with open(_EJ, encoding="utf-8") as _fh:
        _ELEV = _json.load(_fh)
for _l in _AIRPORTS.strip().splitlines():
    _p = _l.split("|")
    _old = AIRPORTS.get(_p[0], {}) or _ELEV.get(_p[0], {})
    AIRPORTS[_p[0]] = dict(icao=_p[0], name=_p[1], city=_p[2], country=_p[3], lat=float(_p[4]), lon=float(_p[5]), large=True,
                           elev=_old.get("elev", 0))
MAJOR = [k for k, a in AIRPORTS.items() if a.get("large")]


# Airport coordinates in radians, worked out once: this is the single most-called
# function in the game and converting degrees on every call was most of its cost.
_RAD = {}


def _rad(icao):
    r = _RAD.get(icao)
    if r is None:
        a = AIRPORTS[icao]
        r = _RAD[icao] = (math.radians(a["lat"]), math.radians(a["lon"]),
                          math.cos(math.radians(a["lat"])))
    return r


def gc_nm(a, b):
    """Great-circle distance in nautical miles between two ICAO codes or (lat,lon) tuples."""
    if type(a) is str:
        la1, lo1, cos1 = _rad(a)
    else:
        la1, lo1 = math.radians(a[0]), math.radians(a[1])
        cos1 = math.cos(la1)
    if type(b) is str:
        la2, lo2, cos2 = _rad(b)
    else:
        la2, lo2 = math.radians(b[0]), math.radians(b[1])
        cos2 = math.cos(la2)
    s1 = math.sin((la2 - la1) * 0.5)
    s2 = math.sin((lo2 - lo1) * 0.5)
    h = s1 * s1 + cos1 * cos2 * s2 * s2
    return 6880.13 * math.asin(math.sqrt(h))


LESSORS = [
    dict(name="AerCap", hq="EIDW"),
    dict(name="Avolon", hq="EIDW"),
    dict(name="SMBC Aviation Capital", hq="EIDW"),
    dict(name="Air Lease Corporation", hq="KLAX"),
    dict(name="BOC Aviation", hq="WSSS"),
    dict(name="Aviation Capital Group", hq="KSAN"),
    dict(name="Carlyle Aviation Partners", hq="KMIA"),
    dict(name="DAE Capital", hq="OMDB"),
    dict(name="Macquarie AirFinance", hq="EIDW"),
    dict(name="Aircastle", hq="KJFK"),
    dict(name="BBAM", hq="KSFO"),
    dict(name="Castlelake", hq="KMSP"),
    dict(name="Jackson Square Aviation", hq="KSFO"),
    dict(name="ORIX Aviation", hq="EIDW"),
    dict(name="Griffin Global Asset Management", hq="EIDW"),
    dict(name="Azorra", hq="KFLL"),
    dict(name="TrueNoord", hq="EHAM"),
    dict(name="Nordic Aviation Capital", hq="EKBI"),
]

# MRO providers and their heavy-maintenance stations
MROS = [
    dict(name="Lufthansa Technik", sites=["EDDF", "EDDH", "LHBP", "LBSF", "EINN", "LMML", "RPLL"]),
    dict(name="AAR", sites=["KIND", "KMIA", "KOKC", "KRFD", "CYWG"]),
    dict(name="ST Engineering", sites=["WSSS", "KMOB", "KPNS", "KSAT"]),
    dict(name="HAECO", sites=["VHHH", "KGSO", "ZSAM"]),
    dict(name="Joramco", sites=["OJAI"]),
    dict(name="Delta TechOps", sites=["KATL"]),
    dict(name="Aeroman", sites=["MSLP"]),
    dict(name="Etihad Engineering", sites=["OMAA"]),
    dict(name="Turkish Technic", sites=["LTFM"]),
    dict(name="Sabena technics", sites=["LFBD", "LFRD"]),
    dict(name="Magnetic MRO", sites=["EETN"]),
    dict(name="Czech Airlines Technics", sites=["LKPR"]),
    dict(name="KLM Engineering & Maintenance", sites=["EHAM"]),
    dict(name="AFI KLM E&M", sites=["LFPG", "LFPO"]),
    dict(name="Iberia Maintenance", sites=["LEMD", "LEBL"]),
    dict(name="SR Technics", sites=["LSZH", "LMML"]),
    dict(name="FL Technics", sites=["EYVI", "EYKA"]),
    dict(name="Ameco Beijing", sites=["ZBAA"]),
    dict(name="GAMECO", sites=["ZGGG"]),
    dict(name="MTU Maintenance", sites=["EDDV"]),
    dict(name="TAP M&E", sites=["LPPT", "SBGL"]),
    dict(name="Air France Industries", sites=["LFPG"]),
    dict(name="Ethiopian MRO", sites=["HAAB"]),
    dict(name="Qantas Engineering", sites=["YSSY", "YBBN"]),
    dict(name="Israel Aerospace Industries", sites=["LLBG"]),
]

# Business aviation does not use the airline shops. Each manufacturer runs its own
# service network, and an owner's aeroplane goes to one of these for anything heavy.
# Locations are the manufacturers' own published company-owned service centres.
BIZ_SERVICE = {
    "Gulfstream": dict(name="Gulfstream Customer Support",
                       sites=["KSAV", "KATW", "KVNY", "KAFW", "EGLF"]),
    "Bombardier": dict(name="Bombardier Service Centre",
                       sites=["KDAL", "KOPF", "KBDL", "KTUS", "KICT", "EGKB", "EDDB", "WSSL", "ZBTJ", "YMEN"]),
    "Textron": dict(name="Textron Aviation Service Center",
                    sites=["KICT", "KMCO", "KHOU", "KIND", "KIWA", "KMKE", "KSWF", "KSMF", "KSAT", "KTPA",
                           "KGSO", "LEVC", "LFPB", "EDDL", "LKPR", "LSZH", "WSSL", "YMEN"]),
    "Hawker Beechcraft": dict(name="Textron Aviation Service Center",
                              sites=["KICT", "KMCO", "KHOU", "KIND", "KIWA", "KTPA", "LEVC", "LFPB", "EDDL"]),
    "Dassault": dict(name="Dassault Falcon Service",
                     sites=["LFPB", "LFBD", "LSGG", "KLIT", "KRNO"]),
    "Embraer": dict(name="Embraer Services & Support",
                    sites=["SBSJ", "KMLB", "KFXE", "LFPB"]),
    "Pilatus": dict(name="Pilatus Business Aircraft service centre", sites=["KBJC"]),
}

# Who owns and moves business aircraft. These are the parties that actually commission
# a positioning flight: the management companies that run owners' aeroplanes, the
# brokers who sell them, and the finance houses behind them.
BIZ_CLIENTS = [
    "NetJets", "Flexjet", "VistaJet", "Jet Linx", "Executive Jet Management",
    "Gama Aviation", "Luxaviation", "TAG Aviation", "Jet Aviation", "Clay Lacy Aviation",
    "Solairus Aviation", "Priester Aviation", "Elit'Avia", "Comlux", "Global Jet",
]
BIZ_BROKERS = [
    "Duncan Aviation", "Guardian Jet", "Jetcraft", "AMSTAT-listed seller", "QS Partners",
    "Mente Group", "Hagerty Jet Group", "Leviate Air Group", "The Jet Collection",
]

STORAGE = [
    dict(name="Pinal Airpark (Ascent Aviation)", icao="KMZJ"),
    dict(name="Roswell Air Center", icao="KROW"),
    dict(name="Victorville (ComAv)", icao="KVCV"),
    dict(name="Mojave Air & Space Port", icao="KMHV"),
    dict(name="Kingman (Kingman Airline Services)", icao="KIGM"),
    dict(name="Phoenix Goodyear (AerSale)", icao="KGYR"),
    dict(name="Teruel (Tarmac Aerosave)", icao="LETL"),
    dict(name="Tarbes-Lourdes (Tarmac Aerosave)", icao="LFBT"),
    dict(name="Ciudad Real", icao="LERL"),
    dict(name="Cotswold Kemble (Air Salvage Intl)", icao="EGBP"),
    dict(name="Alice Springs (APAS)", icao="YBAS"),
    dict(name="Bournemouth (European Aviation)", icao="EGHH"),
]

# Where new aircraft are collected from
DELIVERY_CENTERS = {
    "Airbus": ["LFBO", "EDHI", "KBFM", "ZBTJ"],
    "Boeing": ["KPAE", "KRNT", "KCHS", "KBFM"],
    "Embraer": ["SBSJ"],
    "ATR": ["LFBO"],
    "Bombardier": ["CYYZ"],
    "De Havilland Canada": ["CYYC"],
}

# Real ACMI / wet-lease customers. hubs: operating bases; network: typical
# destinations; fams: rating families they will accept.
ACMI_CUSTOMERS = [
    dict(name="Lufthansa", iata="LH", hubs=["EDDF", "EDDM"], network=["EGLL", "LFPG", "LEMD", "LIRF", "LOWW", "ESSA", "EHAM", "LGAV", "LTFM", "EIDW", "LEBL", "LPPT", "EDDH", "EDDB", "LSZH", "EPWA"], fams=["A320", "B737", "CRJ", "E-Jet", "Q400", "A330/A350", "B777/787"], cargo=False),
    dict(name="Eurowings", iata="EW", hubs=["EDDK", "EDDL", "EDDS", "EDDH"], network=["LEPA", "LEMG", "LEAL", "LGIR", "LGRP", "LGKO", "LIRF", "LEBL", "LPFR", "EGLL", "LOWW", "LSZH", "GCLP", "GCTS", "LICJ"], fams=["A320", "B737", "E-Jet", "CRJ", "Q400"], cargo=False),
    dict(name="Condor", iata="DE", hubs=["EDDF", "EDDM", "EDDL"], network=["LEPA", "GCTS", "GCLP", "LGIR", "LGRP", "LTAI", "HEGN", "LPFR", "LEMG", "LICC", "LMML", "LCLK", "EGKK"], fams=["A320", "B737", "A330/A350", "B757/767"], cargo=False),
    dict(name="TUI fly", iata="X3", hubs=["EDDH", "EDDL", "EDDV", "EDDS"], network=["LEPA", "GCTS", "GCLP", "LGIR", "LGRP", "LGKO", "LTAI", "HEGN", "LPFR", "LEMG", "LEIB", "LICC"], fams=["A320", "B737", "B757/767", "B777/787"], cargo=False),
    dict(name="TUI Airways", iata="BY", hubs=["EGCC", "EGKK", "EGBB", "EGPF"], network=["LEPA", "GCTS", "GCLP", "LGIR", "LGRP", "LTAI", "LTBS", "HEGN", "LPFR", "LEMG", "LEAL", "LCPH", "LMML", "LEIB"], fams=["B737", "A320", "B757/767", "B777/787"], cargo=False),
    dict(name="KLM", iata="KL", hubs=["EHAM"], network=["EGLL", "LFPG", "EDDF", "LEMD", "LIRF", "ESSA", "ENGM", "EKCH", "EFHK", "LOWW", "LSZH", "EIDW", "EGCC", "LEBL", "LPPT", "LGAV", "EPWA", "LHBP"], fams=["B737", "A320", "E-Jet", "A330/A350", "B777/787"], cargo=False),
    dict(name="Transavia", iata="HV", hubs=["EHAM", "EHEH"], network=["LEPA", "LEMG", "LEAL", "LEBL", "LPFR", "LPPT", "LIRF", "LICJ", "LGAV", "LGIR", "LTAI", "GCTS", "GCLP", "LFMN", "LEIB", "GMMX"], fams=["B737", "A320"], cargo=False),
    dict(name="Air France", iata="AF", hubs=["LFPG", "LFPO"], network=["EGLL", "EDDF", "LEMD", "LIRF", "EHAM", "LSZH", "LOWW", "ESSA", "LFMN", "LFLL", "LFBO", "LFML", "LEBL", "LPPT", "LGAV", "LTFM", "GMMN", "DTTA"], fams=["A320", "E-Jet", "CRJ", "A330/A350", "B777/787"], cargo=False),
    dict(name="easyJet", iata="U2", hubs=["EGKK", "EGGW", "EGCC", "EGGD", "LSGG", "LIMC", "EDDB", "LFPO"], network=["LEPA", "LEMG", "LEAL", "LEBL", "LPFR", "LPPT", "LIRF", "LIPZ", "LGAV", "LFMN", "LFBO", "EHAM", "EDDB", "LSZH", "LKPR", "LHBP", "EPKK", "LDSP", "LIPE"], fams=["A320"], cargo=False),
    dict(name="Jet2", iata="LS", hubs=["EGNM", "EGCC", "EGSS", "EGBB", "EGPH", "EGGD"], network=["LEPA", "LEMG", "LEAL", "LEIB", "LPFR", "GCTS", "GCLP", "LGIR", "LGRP", "LGKO", "LTAI", "LTBS", "LCPH", "LMML", "LICC"], fams=["B737", "A320", "B757/767"], cargo=False),
    dict(name="British Airways", iata="BA", hubs=["EGLL", "EGKK"], network=["LFPG", "EDDF", "EDDM", "LEMD", "LEBL", "LIRF", "LIMC", "EHAM", "LSZH", "LSGG", "LOWW", "ESSA", "EKCH", "EIDW", "EGPH", "EGCC", "LPPT", "LGAV", "LTFM", "LEPA"], fams=["A320", "E-Jet", "A330/A350", "B777/787"], cargo=False),
    dict(name="Virgin Atlantic", iata="VS", hubs=["EGLL", "EGCC"], network=["KJFK", "KBOS", "KMCO", "KMIA", "KLAX", "KSFO", "KATL", "KIAD", "TNCM", "MKJP"], fams=["A330/A350", "B777/787"], cargo=False),
    dict(name="SAS", iata="SK", hubs=["EKCH", "ENGM", "ESSA"], network=["EGLL", "LFPG", "EDDF", "EHAM", "EFHK", "LSZH", "LIRF", "LEMD", "LEBL", "LEPA", "LEMG", "ENBR", "ENZV", "ESGG", "EKBI", "LOWW", "LEAL", "GCLP"], fams=["A320", "B737", "CRJ", "E-Jet", "ATR", "A330/A350"], cargo=False),
    dict(name="Norwegian", iata="DY", hubs=["ENGM", "EKCH", "ESSA"], network=["EGKK", "LEPA", "LEMG", "LEAL", "LEBL", "LIRF", "LFPG", "EHAM", "LGAV", "GCLP", "GCTS", "ENBR", "ENZV", "EFHK", "LKPR", "LHBP"], fams=["B737", "A320"], cargo=False),
    dict(name="Finnair", iata="AY", hubs=["EFHK"], network=["EGLL", "LFPG", "EDDF", "EHAM", "ESSA", "EKCH", "ENGM", "LOWW", "LSZH", "LIRF", "LEMD", "LEBL", "LEPA", "LGAV", "EETN", "EVRA", "EPWA", "LKPR"], fams=["A320", "E-Jet", "ATR", "A330/A350"], cargo=False),
    dict(name="LOT Polish Airlines", iata="LO", hubs=["EPWA", "EPKK"], network=["EGLL", "LFPG", "EDDF", "EHAM", "LOWW", "LIRF", "LEMD", "LEBL", "EKCH", "ESSA", "EFHK", "EVRA", "EYVI", "LKPR", "LHBP", "LROP", "LYBE", "LTFM"], fams=["B737", "E-Jet", "Q400", "B777/787"], cargo=False),
    dict(name="Austrian Airlines", iata="OS", hubs=["LOWW"], network=["EGLL", "LFPG", "EDDF", "EHAM", "LIRF", "LEMD", "LEBL", "LGAV", "LTFM", "LHBP", "LKPR", "LROP", "LYBE", "LDZA", "LDSP", "LBSF", "LZIB", "LOWS"], fams=["A320", "E-Jet", "Q400", "B777/787"], cargo=False),
    dict(name="Brussels Airlines", iata="SN", hubs=["EBBR"], network=["EGLL", "LFMN", "EDDF", "EDDB", "LIRF", "LEMD", "LEBL", "LEPA", "LEMG", "LGAV", "LPPT", "LPFR", "EKCH", "ESSA", "LOWW", "LKPR", "GCTS"], fams=["A320", "A330/A350"], cargo=False),
    dict(name="SWISS", iata="LX", hubs=["LSZH", "LSGG"], network=["EGLL", "LFPG", "EDDF", "EHAM", "LIRF", "LEMD", "LEBL", "LEPA", "LGAV", "LOWW", "EKCH", "ESSA", "LPPT", "LTFM", "EDDB", "EDDH"], fams=["A320", "CRJ", "A330/A350", "B777/787"], cargo=False),
    dict(name="Aer Lingus", iata="EI", hubs=["EIDW", "EINN"], network=["EGLL", "EGCC", "EGBB", "EGPH", "LFPG", "EHAM", "EDDF", "LEMD", "LEBL", "LEPA", "LEMG", "LEAL", "LPFR", "LIRF", "LIMC", "GCTS", "KJFK", "KBOS", "KORD"], fams=["A320", "A330/A350", "ATR"], cargo=False),
    dict(name="Air Serbia", iata="JU", hubs=["LYBE"], network=["EGLL", "LFPG", "EDDF", "EDDB", "LOWW", "LSZH", "LIRF", "LGAV", "LTFM", "LKPR", "LHBP", "LROP", "LBSF", "LDZA", "LDSP", "LEBL"], fams=["A320", "ATR", "E-Jet", "A330/A350"], cargo=False),
    dict(name="Wizz Air", iata="W6", hubs=["LHBP", "EGGW", "LROP", "EPWA", "LBSF"], network=["EGLL", "EGKK", "EHEH", "LIME", "LIRF", "LEBL", "LEMG", "LEAL", "LEPA", "LGAV", "LTFM", "LCLK", "LLBG", "OMDW", "GCTS", "LFPO", "ESSA"], fams=["A320"], cargo=False),
    dict(name="Vueling", iata="VY", hubs=["LEBL", "LEMD", "LIRF", "LFPO"], network=["EGKK", "EGLL", "EHAM", "EBBR", "EDDF", "EDDB", "LSZH", "LIMC", "LIPZ", "LICJ", "LGAV", "LPPT", "LPPR", "LEPA", "LEMG", "LEAL", "LEIB", "GCLP", "GCTS", "GMMN"], fams=["A320"], cargo=False),
    dict(name="Iberia", iata="IB", hubs=["LEMD"], network=["EGLL", "LFPG", "EDDF", "EHAM", "LIRF", "LSZH", "LOWW", "LPPT", "LEBL", "LEPA", "LEMG", "GCLP", "GCTS", "GMMN", "LGAV", "LTFM", "KJFK", "KMIA", "SBGR", "SCEL", "SKBO"], fams=["A320", "A330/A350", "CRJ"], cargo=False),
    dict(name="TAP Air Portugal", iata="TP", hubs=["LPPT", "LPPR"], network=["EGLL", "LFPG", "EDDF", "EHAM", "LIRF", "LEMD", "LEBL", "LSZH", "EBBR", "LPFR", "LPMA", "GMMN", "KJFK", "KBOS", "KMIA", "SBGR", "SBGL"], fams=["A320", "E-Jet", "ATR", "A330/A350"], cargo=False),
    dict(name="airBaltic", iata="BT", hubs=["EVRA", "EETN", "EYVI"], network=["EGLL", "LFPG", "EDDF", "EHAM", "LOWW", "LSZH", "EKCH", "ESSA", "ENGM", "EFHK", "EPWA", "LKPR", "LEBL", "LEMG", "LGAV", "LIRF", "LTFM"], fams=["A320", "Q400"], cargo=False),
    dict(name="Icelandair", iata="FI", hubs=["BIKF"], network=["EGLL", "EGCC", "EGPF", "LFPG", "EHAM", "EDDF", "EKCH", "ENGM", "ESSA", "EFHK", "KJFK", "KBOS", "KIAD", "KORD", "KSEA", "KDEN", "CYYZ", "KMCO"], fams=["B737", "B757/767", "A320"], cargo=False),
    dict(name="Air Canada", iata="AC", hubs=["CYYZ", "CYUL", "CYVR"], network=["KJFK", "KBOS", "KORD", "KLAX", "KSFO", "KDEN", "KMCO", "KMIA", "KLAS", "CYYC", "CYOW", "CYHZ", "CYWG", "CYEG", "EGLL", "LFPG", "EDDF", "MMUN", "TJSJ"], fams=["A320", "B737", "E-Jet", "CRJ", "Q400", "A330/A350", "B777/787"], cargo=False),
    dict(name="WestJet", iata="WS", hubs=["CYYC", "CYVR", "CYYZ"], network=["KLAX", "KLAS", "KPHX", "KSFO", "KSEA", "KDEN", "KMCO", "KFLL", "CYEG", "CYWG", "CYOW", "CYHZ", "CYUL", "MMUN", "MMGL", "EGLL", "EGKK", "EIDW"], fams=["B737", "Q400", "B777/787"], cargo=False),
    dict(name="Sun Country Airlines", iata="SY", hubs=["KMSP"], network=["KMCO", "KFLL", "KTPA", "KLAS", "KPHX", "KSAN", "KDEN", "KSFO", "KSEA", "KBOS", "KJFK", "KIAD", "KDFW", "MMUN", "TJSJ", "MSLP"], fams=["B737"], cargo=False),
    dict(name="Frontier Airlines", iata="F9", hubs=["KDEN", "KLAS", "KMCO"], network=["KLAX", "KSAN", "KSFO", "KSEA", "KPDX", "KSLC", "KPHX", "KDFW", "KIAH", "KATL", "KMIA", "KFLL", "KTPA", "KORD", "KMSP", "KCLE", "KPHL", "MMUN"], fams=["A320"], cargo=False),
    dict(name="Air India", iata="AI", hubs=["VIDP", "VABB"], network=["VOBL", "VECC", "VOMM", "OMDB", "OMAA", "OTHH", "WSSS", "VTBS", "VHHH", "EGLL", "LFPG", "EDDF", "KJFK", "KEWR", "KORD", "KSFO", "YSSY", "YMML"], fams=["A320", "B777/787", "A330/A350"], cargo=False),
    dict(name="IndiGo", iata="6E", hubs=["VIDP", "VABB", "VOBL"], network=["VECC", "VOMM", "OMDB", "OMSJ", "OMAA", "OTHH", "OERK", "OEJN", "WSSS", "WMKK", "VTBS", "VCBI", "LTFM", "EHAM", "EGCC"], fams=["A320", "ATR", "B777/787"], cargo=False),
    dict(name="Qantas", iata="QF", hubs=["YSSY", "YMML", "YBBN"], network=["YPPH", "YSCB", "NZAA", "NZCH", "NZWN", "NFFN", "WSSS", "VHHH", "RJTT", "KLAX", "KDFW", "EGLL", "OMDB", "WIII", "WADD"], fams=["B737", "A320", "Q400", "A330/A350", "B777/787"], cargo=False),
    dict(name="Air New Zealand", iata="NZ", hubs=["NZAA", "NZCH", "NZWN"], network=["YSSY", "YMML", "YBBN", "YPPH", "NFFN", "WSSS", "VHHH", "RJAA", "KLAX", "KSFO", "PHNL", "CYVR"], fams=["A320", "ATR", "Q400", "B777/787"], cargo=False),
    dict(name="Saudia", iata="SV", hubs=["OEJN", "OERK"], network=["OEDF", "HECA", "OMDB", "OTHH", "OKBK", "OBBI", "OJAI", "LTFM", "EGLL", "LFPG", "EDDF", "VIDP", "VABB", "WMKK", "WIII", "FAOR"], fams=["A320", "A330/A350", "B777/787"], cargo=False),
    dict(name="flynas", iata="XY", hubs=["OERK", "OEJN"], network=["OEDF", "HECA", "OMDB", "OMSJ", "OKBK", "OBBI", "OJAI", "LTFM", "LTAI", "VIDP", "VABB", "VECC", "HKJK", "HAAB", "LCLK"], fams=["A320"], cargo=False),
    dict(name="Kenya Airways", iata="KQ", hubs=["HKJK"], network=["HAAB", "FAOR", "FACT", "DNMM", "HECA", "OMDB", "VABB", "ZGGG", "EGLL", "LFPG", "EHAM", "KJFK"], fams=["B737", "E-Jet", "B777/787"], cargo=False),
    dict(name="Ethiopian Airlines", iata="ET", hubs=["HAAB"], network=["HKJK", "FAOR", "FACT", "DNMM", "HECA", "OMDB", "VABB", "ZGGG", "ZBAA", "EGLL", "LFPG", "EDDF", "KIAD", "KEWR", "CYYZ", "SBGR"], fams=["B737", "Q400", "A330/A350", "B777/787"], cargo=False),
    dict(name="Azul", iata="AD", hubs=["SBKP", "SBGL"], network=["SBGR", "SAEZ", "SCEL", "SPJC", "SKBO", "MPTO", "KMCO", "KFLL", "LPPT"], fams=["E-Jet", "ATR", "A320", "A330/A350"], cargo=False),
    dict(name="LATAM Airlines", iata="LA", hubs=["SBGR", "SCEL", "SPJC"], network=["SBGL", "SAEZ", "SKBO", "MPTO", "MMMX", "KMIA", "KJFK", "KLAX", "KMCO", "LEMD", "LFPG", "EDDF", "EGLL"], fams=["A320", "A330/A350", "B777/787"], cargo=False),
    dict(name="Copa Airlines", iata="CM", hubs=["MPTO"], network=["KMIA", "KMCO", "KJFK", "KLAX", "MMMX", "MMUN", "SKBO", "SPJC", "SCEL", "SBGR", "SAEZ", "MSLP", "MKJP", "TJSJ"], fams=["B737"], cargo=False),
    # Cargo customers
    dict(name="DHL Express", iata="D0", hubs=["EDDP", "EBLG", "KCVG", "VHHH"], network=["EGNX", "EHAM", "LFPG", "LEMD", "LIMC", "EPWA", "EFHK", "LTFM", "OBBI", "OMDW", "KJFK", "KLAX", "KMIA", "ZSPD", "WSSS", "RJAA"], fams=["B757/767", "B777/787", "B747", "A330/A350"], cargo=True),
    dict(name="UPS Airlines", iata="5X", hubs=["KSDF", "KRFD", "KPHL", "EDDK"], network=["KMIA", "KLAX", "KDFW", "KORD", "KEWR", "KATL", "CYYZ", "MMMX", "EDDK", "EGSS", "PANC", "RJAA", "VHHH", "ZSPD", "WSSS"], fams=["B757/767", "B777/787", "B747"], cargo=True),
    dict(name="FedEx Express", iata="FX", hubs=["KMEM", "KIND", "KOKC"], network=["KLAX", "KEWR", "KMIA", "KDFW", "KORD", "PANC", "KSEA", "CYYZ", "MMMX", "LFPG", "EDDK", "EGSS", "LIMC", "OMDW", "RJAA", "ZGGG", "VHHH"], fams=["B757/767", "B777/787", "A330/A350"], cargo=True),
    dict(name="Amazon Air", iata="MZN", hubs=["KCVG", "KSAT", "KRFD"], network=["KMIA", "KLAX", "KDFW", "KORD", "KATL", "KEWR", "KSEA", "KPHX", "KDEN", "KTPA", "KBWI", "KCLT", "KSDF"], fams=["B757/767", "B737", "A330/A350"], cargo=True),
    dict(name="Kuehne+Nagel", iata="KN", hubs=["LSZH", "EBLG", "EDDF"], network=["ZSPD", "VHHH", "RJAA", "KORD", "KJFK", "KLAX", "OMDW", "WSSS", "LIMC", "EGSS"], fams=["B747", "B777/787"], cargo=True),
    dict(name="DB Schenker", iata="DBS", hubs=["EDDF", "EDDP"], network=["ZSPD", "VHHH", "RJAA", "KORD", "KATL", "OMDW", "WSSS", "LIMC", "EGSS", "ZGGG"], fams=["B747", "B777/787", "B757/767"], cargo=True),
]

# Airlines whose aircraft appear in ferry jobs (owners/operators/lessees)
OPERATORS = [c["name"] for c in ACMI_CUSTOMERS if not c["cargo"]] + [
    "Delta Air Lines", "United Airlines", "American Airlines", "Southwest Airlines", "JetBlue", "Alaska Airlines",
    "Spirit Airlines", "Allegiant Air", "Ryanair", "Emirates", "Qatar Airways", "Etihad Airways", "Turkish Airlines",
    "Cathay Pacific", "Singapore Airlines", "Japan Airlines", "All Nippon Airways", "Korean Air", "China Southern",
    "Avianca", "Aeromexico", "Volaris", "GOL", "Air Europa", "ITA Airways", "Pegasus", "SunExpress", "Corendon Airlines",
    "Air Astana", "Royal Jordanian", "Oman Air", "Gulf Air", "EgyptAir", "Royal Air Maroc", "South African Airways",
    "Air Tahiti Nui", "Fiji Airways", "Air Malta", "Aegean Airlines", "Croatia Airlines", "Luxair", "Edelweiss",
    "Bridges Air Cargo", "USA Jet Airlines", "IFL Group", "Air Class Lineas Aereas", "Solar Cargo",
    "Safe Air Company", "Serve Air Cargo", "MNG Airlines", "Aeronaves TSM", "European Air Transport Leipzig", "Air Hong Kong",
    "Astral Aviation", "Qantas Freight",
    "Atlas Air", "Cargolux", "ASL Airlines", "Cargojet", "Kalitta Air", "Western Global Airlines", "AirBridgeCargo",
]

# operator -> main base, for ferry origins/destinations (subset; others use hub tables)
OPERATOR_BASES = {c["name"]: c["hubs"][0] for c in ACMI_CUSTOMERS}
OPERATOR_BASES.update({
    "Bridges Air Cargo": "LMML", "USA Jet Airlines": "KYIP", "IFL Group": "KYIP",
    "Air Class Lineas Aereas": "SUMU", "Solar Cargo": "SVVA", "Safe Air Company": "HKJK",
    "Serve Air Cargo": "FZAA", "MNG Airlines": "LTFM", "Aeronaves TSM": "MMIO", "European Air Transport Leipzig": "EDDP",
    "Air Hong Kong": "VHHH", "Astral Aviation": "HKJK", "Qantas Freight": "YSSY",
    "Delta Air Lines": "KATL", "United Airlines": "KORD", "American Airlines": "KDFW", "Southwest Airlines": "KDAL" if "KDAL" in AIRPORTS else "KPHX",
    "JetBlue": "KJFK", "Alaska Airlines": "KSEA", "Spirit Airlines": "KFLL", "Allegiant Air": "KLAS", "Ryanair": "EIDW",
    "Emirates": "OMDB", "Qatar Airways": "OTHH", "Etihad Airways": "OMAA", "Turkish Airlines": "LTFM", "Cathay Pacific": "VHHH",
    "Singapore Airlines": "WSSS", "Japan Airlines": "RJTT", "All Nippon Airways": "RJTT", "Korean Air": "RKSI",
    "China Southern": "ZGGG", "Avianca": "SKBO", "Aeromexico": "MMMX", "Volaris": "MMMX", "GOL": "SBGR", "Air Europa": "LEMD",
    "ITA Airways": "LIRF", "Pegasus": "LTFM", "SunExpress": "LTAI", "Corendon Airlines": "LTAI", "Air Astana": "OMDB",
    "Royal Jordanian": "OJAI", "Oman Air": "OOMS", "Gulf Air": "OBBI", "EgyptAir": "HECA", "Royal Air Maroc": "GMMN",
    "South African Airways": "FAOR", "Air Tahiti Nui": "KLAX", "Fiji Airways": "NFFN", "Air Malta": "LMML",
    "Aegean Airlines": "LGAV", "Croatia Airlines": "LDZA", "Luxair": "LFPG", "Edelweiss": "LSZH", "Atlas Air": "KMIA",
    "Cargolux": "EBLG", "ASL Airlines": "EBLG", "Cargojet": "CYYZ", "Kalitta Air": "KDTW", "Western Global Airlines": "KTPA",
    "AirBridgeCargo": "EDDF",
})

REG_PREFIXES = ["N", "G-", "D-A", "EI-", "F-H", "OE-I", "PH-B", "9H-", "2-", "VP-C", "M-A", "C-F", "OY-", "SE-R", "LN-", "OH-L", "SP-", "HB-J", "EC-", "CS-T", "I-", "TC-", "A6-", "VT-", "VH-", "ZK-", "PR-", "LV-"]

# The register a tail belongs to, for the paperwork when an aircraft is re-registered.
REGISTERS = {
    "N": ("United States", "Federal Aviation Administration"),
    "G-": ("United Kingdom", "Civil Aviation Authority"),
    "D-": ("Germany", "Luftfahrt-Bundesamt"),
    "EI-": ("Ireland", "Irish Aviation Authority"),
    "F-": ("France", "Direction générale de l'aviation civile"),
    "OE-": ("Austria", "Austro Control"),
    "PH-": ("Netherlands", "Inspectie Leefomgeving en Transport"),
    "9H-": ("Malta", "Transport Malta"),
    "2-": ("Guernsey", "Guernsey Aircraft Registry"),
    "VP-C": ("Cayman Islands", "Civil Aviation Authority of the Cayman Islands"),
    "M-": ("Isle of Man", "Isle of Man Aircraft Registry"),
    "C-": ("Canada", "Transport Canada"),
    "OY-": ("Denmark", "Trafikstyrelsen"),
    "SE-": ("Sweden", "Transportstyrelsen"),
    "LN-": ("Norway", "Luftfartstilsynet"),
    "OH-": ("Finland", "Traficom"),
    "SP-": ("Poland", "Urząd Lotnictwa Cywilnego"),
    "HB-": ("Switzerland", "Federal Office of Civil Aviation"),
    "EC-": ("Spain", "Agencia Estatal de Seguridad Aérea"),
    "CS-": ("Portugal", "Autoridade Nacional da Aviação Civil"),
    "I-": ("Italy", "ENAC"),
    "TC-": ("Türkiye", "Directorate General of Civil Aviation"),
    "A6-": ("United Arab Emirates", "General Civil Aviation Authority"),
    "VT-": ("India", "Directorate General of Civil Aviation"),
    "VH-": ("Australia", "Civil Aviation Safety Authority"),
    "ZK-": ("New Zealand", "Civil Aviation Authority"),
    "PR-": ("Brazil", "ANAC"),
    "PP-": ("Brazil", "ANAC"),
    "LV-": ("Argentina", "ANAC"),
    "ZS-": ("South Africa", "South African Civil Aviation Authority"),
    "5Y-": ("Kenya", "Kenya Civil Aviation Authority"),
    "B-": ("China", "Civil Aviation Administration of China"),
    "JA": ("Japan", "Japan Civil Aviation Bureau"),
    "HL": ("South Korea", "Ministry of Land, Infrastructure and Transport"),
    "9V-": ("Singapore", "Civil Aviation Authority of Singapore"),
    "T7-": ("San Marino", "San Marino Civil Aviation Authority"),
    "P4-": ("Aruba", "Department of Civil Aviation"),
    "LX-": ("Luxembourg", "Direction de l'Aviation Civile"),
    "LZ-": ("Bulgaria", "Civil Aviation Administration"),
    "YR-": ("Romania", "Romanian Civil Aeronautical Authority"),
    "OK-": ("Czechia", "Civil Aviation Authority"),
}


def register_for(reg):
    """Which authority a registration belongs to."""
    reg = (reg or "").upper()
    for pref in sorted(REGISTERS, key=len, reverse=True):
        if reg.startswith(pref):
            return REGISTERS[pref]
    return ("an unlisted register", "the registering authority")

# Superseded by NAME_POOLS and crew_name(); kept so an older save or a third-party
# script that imports them still works.
FIRST_NAMES = ["James", "Michael", "Sarah", "Daniel", "Anna", "Thomas", "Laura", "Mark", "Julia", "Andreas", "Peter", "Elena", "Lars", "Sofia", "Marcus", "Hannah", "Erik", "Nina", "Patrick", "Claire", "Robert", "Emma", "Jonas", "Maria", "Kevin", "Lisa", "Stefan", "Katrin", "Paul", "Ingrid", "Tomasz", "Agnieszka", "Sean", "Aoife", "Miguel", "Lucia", "Henrik", "Astrid", "Yusuf", "Leila", "Raj", "Priya", "Chen", "Mei", "Diego", "Valentina", "Olivier", "Camille", "Matteo", "Giulia"]
LAST_NAMES = ["Walker", "Bauer", "Nielsen", "Schmidt", "Kowalski", "Murphy", "Garcia", "Andersson", "Fischer", "O'Brien", "Rossi", "Jansen", "Lefevre", "Hoffmann", "Larsen", "Novak", "Weber", "Byrne", "Martinez", "Lindqvist", "Meyer", "Brennan", "Costa", "Dubois", "Keller", "Petrov", "Nakamura", "Yilmaz", "Sharma", "Okafor", "Silva", "Ivanova", "Hansen", "Moreau", "Ricci", "Wagner", "Kelly", "Berg", "Fernandez", "Zimmermann"]


# ---------------------------------------------------------------- v2 data
# Overflight / landing permit requirements by country: (lead days, fee USD).
# Countries not listed (EU/EEA, UK, CH, etc.) need no advance permit for a ferry.
PERMIT_COUNTRIES = {
    "RU": (7, 1400), "CN": (7, 1100), "IN": (3, 450), "PK": (3, 400), "BD": (3, 350), "NP": (3, 300), "MM": (4, 350),
    "SA": (3, 650), "EG": (3, 500), "SD": (4, 400), "LY": (5, 500), "DZ": (3, 400), "ET": (2, 300), "KE": (2, 300), "NG": (3, 450),
    "AO": (3, 400), "GH": (2, 300), "SN": (2, 300), "ZA": (1, 250), "MA": (1, 250), "TN": (2, 250), "JO": (2, 300), "IL": (3, 400),
    "AE": (1, 250), "QA": (1, 250), "OM": (2, 300), "KW": (2, 300), "BH": (1, 250), "TR": (1, 200), "KZ": (3, 400), "UZ": (3, 400),
    "BR": (2, 350), "AR": (2, 300), "CL": (1, 250), "PE": (2, 300), "CO": (2, 300), "EC": (2, 300), "VE": (4, 400), "MX": (1, 300),
    "CU": (5, 500), "DO": (1, 200), "ID": (3, 400), "VN": (3, 400), "TH": (2, 300), "MY": (2, 300), "PH": (3, 350), "AU": (1, 300),
    "NZ": (1, 250), "JP": (1, 300), "KR": (1, 300), "TW": (2, 300), "US": (1, 300), "CA": (1, 250), "HK": (1, 250), "SG": (1, 250),
    "LK": (2, 300), "MV": (2, 300), "UA": (3, 400), "IR": (5, 900), "AF": (7, 900), "AZ": (2, 300), "GE": (1, 250), "BY": (5, 500), "TJ": (3, 350), "MU": (2, 300), "SC": (2, 300), "FJ": (2, 300), "PF": (2, 300),
}

# Jet A price factor by country -> region (base price set in Settings, USD/USG)
FUEL_REGION = {
    "US": 0.98, "CA": 1.05, "MX": 1.15, "GL": 1.6, "CV": 1.4, "SH": 1.9, "AS": 1.5, "PF": 1.5,
    "AE": 0.9, "QA": 0.88, "SA": 0.85, "OM": 0.92, "KW": 0.88, "BH": 0.9, "JO": 1.15, "IL": 1.1, "EG": 1.1, "TR": 1.1,
    "IN": 1.2, "PK": 1.2, "BD": 1.2, "LK": 1.25, "NP": 1.35, "CN": 1.05, "HK": 1.05, "TW": 1.05, "JP": 1.1, "KR": 1.05,
    "SG": 1.0, "MY": 1.0, "TH": 1.05, "ID": 1.15, "PH": 1.15, "VN": 1.15, "MM": 1.3, "AU": 1.12, "NZ": 1.15, "FJ": 1.4,
    "BR": 1.25, "AR": 1.2, "CL": 1.2, "PE": 1.2, "CO": 1.15, "EC": 1.2, "VE": 1.3, "PA": 1.15, "SV": 1.2, "JM": 1.3, "DO": 1.25, "CU": 1.5, "BB": 1.4, "PR": 1.15, "SX": 1.35,
    "ZA": 1.15, "KE": 1.35, "ET": 1.3, "NG": 1.35, "AO": 1.4, "GH": 1.35, "SN": 1.35, "SD": 1.5, "LY": 1.3, "DZ": 1.15, "MA": 1.15, "TN": 1.2, "MU": 1.4, "SC": 1.5,
    "RU": 0.95, "KZ": 0.95, "UZ": 1.0, "IS": 1.3,
}
EU_FACTOR = 1.18

# Real ACMI providers that compete for tenders
COMPETITORS = ["SmartLynx Airlines", "Avion Express", "Titan Airways", "Hi Fly", "Wamos Air", "Privilege Style", "AirExplore",
               "Freebird Airlines", "GetJet Airlines", "Electra Airways", "Iberojet", "European Air Charter", "Heston Airlines",
               "Marabu Airlines", "Nordic Aviation Group", "Omni Air International", "Air Atlanta Icelandic"]
CARGO_COMPETITORS = ["Atlas Air", "ASL Airlines", "Cargojet", "Air Atlanta Icelandic", "Kalitta Air", "Western Global Airlines", "Magma Aviation", "Sky Lease Cargo"]

# Minimum-equipment / deferred-defect items that can be carried on a ferry flight
# Which families actually have the systems a defect refers to.
NO_AUTOTHROTTLE = {"CRJ", "ATR", "Q400", "E-Jet", "B727"}   # turboprops, the E-Jet E1 and the 727 have none
NO_ETOPS = {"B747", "MD-11", "B727"}                          # four engines or three: no ETOPS approval to lapse
FOUR_ENGINE = NO_ETOPS                                # kept for compatibility
CEILING_FT = {"ATR": 25000, "Q400": 25000, "CRJ": 41000, "E-Jet": 41000, "B727": 42000, "A300": 40000}

# Deferred defects. "howto" is how to fly the restriction in a simulator, since not every
# add-on models the underlying failure — the permit limits are what matter, not the failure.
# "excludes" names families the item cannot apply to, "min_range" keeps long-range items
# off short-haul aircraft.
SNAGS = [
    dict(code="APU", name="APU inoperative", effect="Ground power and air-start unit required at each departure (+$450/dep)", cost=28000, gpu=True,
         howto="Leave the APU off for the whole sector. Start on external power and an air-start cart, or use the ground services menu; if your aircraft has a failure system, fail the APU."),
    dict(code="A/T", name="Autothrottle inoperative", effect="Manual thrust; crew workload", cost=16000, excludes=NO_AUTOTHROTTLE,
         howto="Do not arm or engage autothrust or autothrottle at any point. Hand-fly the thrust all the way, including the approach."),
    dict(code="PACK", name="One air-conditioning pack inoperative", effect="Maximum FL250", cost=42000, max_alt=25000,
         excludes={"ATR", "Q400"},
         howto="Switch one pack off before departure and leave it off. Plan the OFP at FL250 or below; Operator checks the altitude you actually flew."),
    dict(code="PRESS", name="Pressurisation restricted", effect="Unpressurised ferry: maximum 10,000 ft", cost=65000, max_alt=10000,
         howto="Fly the whole sector at or below 10,000 ft. If your aircraft models it, set the outflow valve manual or fail the pressurisation system; otherwise simply stay low."),
    dict(code="GEAR", name="Landing gear retraction deactivated", effect="Gear-down ferry: maximum 200 kias, gear stays down", cost=90000, gear_down=True, max_ias=200,
         howto="Leave the gear down from before taxi until shutdown and keep the speed at or below 200 kias. Study-level aircraft can fail the retraction; in anything else, just never raise the lever."),
    dict(code="WXR", name="Weather radar inoperative", effect="Day VMC only", cost=22000, day_only=True,
         howto="Fly in daylight and clear of cloud. Set the simulator time and weather accordingly, and leave the radar off."),
    dict(code="HF", name="HF radio inoperative", effect="No oceanic/remote airspace (non-ETOPS routing)", cost=9000, no_oceanic=True, min_range=2500,
         howto="Route so that you stay within about 60 minutes of an airport at all times — the routing Operator plans already does this."),
    dict(code="REV", name="Thrust reverser deactivated", effect="Landing performance penalty; no contaminated runways", cost=18000,
         howto="Do not use reverse thrust on landing; brakes and spoilers only. Avoid a wet or contaminated runway — the landing distance already carries a 10% penalty."),
    dict(code="FQI", name="Fuel quantity indication unreliable", effect="Manual fuel checks; +10% contingency fuel", cost=12000,
         howto="Carry extra contingency fuel in the OFP and cross-check burn against time. No action needed in the aircraft itself."),
    dict(code="ETOPS", name="ETOPS approval lapsed", effect="Non-ETOPS routing: stay within 60 min of a diversion airport", cost=35000, no_oceanic=True,
         min_range=2500, excludes=FOUR_ENGINE,
         howto="Fly the coastal or island routing rather than a direct oceanic track. Operator measures how far from a diversion airport you actually got."),
    dict(code="AC", name="Cabin equipment / slides out of date", effect="No passengers; crew only", cost=14000, excludes={"ATR", "Q400"},
         howto="Nothing to do in the aircraft — the flight is crew-only, which a ferry already is."),
]

ENGINES = {
    # business aircraft: fewer, cheaper engines on longer intervals
    "PC-12": (1, 900000, 4000),
    "King Air": (2, 700000, 4000),
    "Phenom": (2, 1200000, 5000),
    "Citation": (2, 1300000, 5000),
    "DC-3": (2, 180000, 2000),
    "Caravan": (1, 450000, 4000),
    "Twin Otter": (2, 520000, 4000),
    "Saab 340": (2, 700000, 5000),
    "Hawker": (2, 1150000, 5000),
    "Praetor": (2, 2100000, 6000),
    "Challenger": (2, 2300000, 6000),
    "Gulfstream": (2, 4200000, 7500),
    "Global": (2, 4400000, 7500),
    "Falcon": (3, 3200000, 7000),
    "MD-11": (3, 4200000, 16000),
    "B727": (3, 1500000, 12000),
    "A300": (2, 3600000, 18000),  # family -> (engine count, shop-visit cost per engine USD, typical interval FH)
    "ATR": (2, 900000, 7000), "Q400": (2, 1100000, 7000), "CRJ": (2, 1800000, 8000), "E-Jet": (2, 2600000, 9000),
    "A320": (2, 4500000, 9000), "B737": (2, 4300000, 9000), "B757/767": (2, 6500000, 9000),
    "A330/A350": (2, 9500000, 10000), "B777/787": (2, 12000000, 10000), "B747": (4, 7000000, 9000),
}
ENGINE_OEM = {"ATR": "Pratt & Whitney Canada", "Q400": "Pratt & Whitney Canada", "CRJ": "GE Aerospace", "E-Jet": "GE Aerospace",
              "A320": "CFM International", "B737": "CFM International", "B757/767": "Rolls-Royce / Pratt & Whitney",
              "A330/A350": "Rolls-Royce", "B777/787": "GE Aerospace / Rolls-Royce", "B747": "GE Aerospace"}

STAFF = {
    "dispatcher": dict(title="Flight dispatcher", salary=5400, per_aircraft=6, note="One per 6 aircraft, minimum one to dispatch any flight"),
    "mx_controller": dict(title="Maintenance controller", salary=7900, per_aircraft=4, note="One per 4 fleet aircraft"),
    "cabin_crew": dict(title="Cabin crew", salary=3200, per_aircraft=0, note="Passenger ACMI: 2 sets per aircraft (turboprop/regional 2, narrowbody 4, widebody 8 per set)"),
}
CABIN_PER_SET = {"Turboprop": 2, "Regional": 2, "Narrowbody": 4, "Widebody": 8}


def elevation(icao):
    return AIRPORTS.get(icao, {}).get("elev", 0)


def fuel_factor(icao):
    a = AIRPORTS.get(icao)
    if not a:
        return 1.1
    return FUEL_REGION.get(a["country"], EU_FACTOR)


# Finding the nearest airport to a point is done thousands of times when planning a
# route, and scanning five thousand airports each time is most of the work. Bucket them
# into five-degree cells once and search outwards from the cell the point is in.
_GRID = None
_GRID_DEG = 5


def _build_grid():
    global _GRID
    _GRID = {}
    for a in AIRPORTS.values():
        key = (int(a["lat"] // _GRID_DEG), int(a["lon"] // _GRID_DEG))
        _GRID.setdefault(key, []).append(a)
    return _GRID


def nearest(lat, lon):
    """The closest airport to a point, and how far away it is.

    Two passes over the grid: expand rings until something is found, then work out
    exactly which cells could still hold anything nearer and check only those. A cell
    is five degrees, so 300 nm of latitude and 300·cos(lat) nm of longitude."""
    grid = _GRID or _build_grid()
    ci, cj = int(lat // _GRID_DEG), int(lon // _GRID_DEG)

    def cells(i_lo, i_hi, j_lo, j_hi):
        for i in range(i_lo, i_hi + 1):
            for j in range(j_lo, j_hi + 1):
                got = grid.get((i, (j + 36) % 72 - 36))
                if got:
                    yield from got

    best, bd = None, 1e9
    for ring in range(0, 37):
        for a in cells(ci - ring, ci + ring, cj - ring, cj + ring):
            d = gc_nm((lat, lon), (a["lat"], a["lon"]))
            if d < bd:
                best, bd = a, d
        if best:
            break
    if not best:
        return None, 1e9

    # now the exact sweep: every cell that could contain something closer than bd
    span_lat = int(bd / (_GRID_DEG * 60)) + 2
    cos_lat = max(0.02, math.cos(math.radians(min(89.0, abs(lat) + bd / 60))))
    span_lon = min(37, int(bd / (_GRID_DEG * 60 * cos_lat)) + 2)
    for a in cells(ci - span_lat, ci + span_lat, cj - span_lon, cj + span_lon):
        d = gc_nm((lat, lon), (a["lat"], a["lon"]))
        if d < bd:
            best, bd = a, d
    return best, bd


def gc_path(o, d, step_nm=150):
    """Points along the great circle between two ICAOs."""
    import math as _m
    A, B = AIRPORTS[o], AIRPORTS[d]
    la1, lo1, la2, lo2 = map(_m.radians, (A["lat"], A["lon"], B["lat"], B["lon"]))
    dist = gc_nm(o, d)
    n = max(1, int(dist / step_nm))
    delta = dist / 3440.065
    pts = []
    for i in range(n + 1):
        f = i / n
        if delta == 0:
            pts.append((A["lat"], A["lon"])); continue
        a = _m.sin((1 - f) * delta) / _m.sin(delta)
        b = _m.sin(f * delta) / _m.sin(delta)
        x = a * _m.cos(la1) * _m.cos(lo1) + b * _m.cos(la2) * _m.cos(lo2)
        y = a * _m.cos(la1) * _m.sin(lo1) + b * _m.cos(la2) * _m.sin(lo2)
        z = a * _m.sin(la1) + b * _m.sin(la2)
        pts.append((_m.degrees(_m.atan2(z, _m.sqrt(x * x + y * y))), _m.degrees(_m.atan2(y, x))))
    return pts


# Both of these walk a great circle calling nearest() at every sample, which is the most
# expensive thing either does. The same city pairs come round again and again while jobs
# are composed, so the answers are kept. Neither depends on anything that changes.
_ROUTE_C = {}
_REMOTE = {}


def route_countries(o, d):
    """Approximate countries overflown: nearest airport within 220 nm of points along the great circle."""
    got = _ROUTE_C.get((o, d))
    if got is not None:
        return got
    seen = []
    for lat, lon in gc_path(o, d):
        a, dn = nearest(lat, lon)
        if a and dn < 220 and a["country"] not in seen:
            seen.append(a["country"])
    for x in (AIRPORTS[o]["country"], AIRPORTS[d]["country"]):
        if x not in seen:
            seen.append(x)
    if len(_ROUTE_C) > 40000:
        _ROUTE_C.clear()
    _ROUTE_C[(o, d)] = seen
    return seen


def max_remoteness(o, d):
    """Largest distance from any airport in the database along the great circle (nm)."""
    got = _REMOTE.get((o, d))
    if got is None:
        got = max(nearest(lat, lon)[1] for lat, lon in gc_path(o, d, 100))
        if len(_REMOTE) > 40000:
            _REMOTE.clear()
        _REMOTE[(o, d)] = got
    return got

CARGO_OPERATORS = {"DHL Express", "UPS Airlines", "FedEx Express", "Amazon Air", "Kuehne+Nagel", "DB Schenker", "Atlas Air", "Cargolux",
                   "ASL Airlines", "Cargojet", "Kalitta Air", "Western Global Airlines", "AirBridgeCargo",
                   # operators of the older and smaller freighters
                   "Bridges Air Cargo", "USA Jet Airlines", "IFL Group", "Air Class Lineas Aereas",
                   "Solar Cargo", "Safe Air Company", "Serve Air Cargo", "MNG Airlines", "Aeronaves TSM",
                   "European Air Transport Leipzig", "Air Hong Kong", "Astral Aviation", "Qantas Freight"}


# ---------------------------------------------------------------- cargo contract flying
# Real cargo operators that hire contract crews, with their main bases, typical fleets
# and the networks they fly. day_rate: USD per crew member per duty day; bh: USD per block hour.
# Regional networks used to assemble each cargo operator's route system
_NET = {
    "NA": ["KMEM", "KSDF", "KIND", "KRFD", "KORD", "KJFK", "KEWR", "KMIA", "KLAX", "KDFW", "KATL", "KSEA", "KDEN", "KPHX", "KBOS", "KPHL", "KMCO", "KBWI", "KCVG", "PANC", "CYYZ", "CYVR", "CYUL", "MMMX"],
    "EU": ["EDDF", "EDDP", "EDDK", "EBLG", "EBBR", "EHAM", "LFPG", "EGSS", "EGNX", "EGLL", "EIDW", "LEMD", "LIMC", "LIRF", "EPWA", "LSZH", "LOWW", "EKCH", "ESSA", "EFHK", "LPPT", "LTFM", "EVRA"],
    "ME": ["OMDW", "OMDB", "OTHH", "OERK", "OEJN", "OBBI", "OKBK", "OOMS", "OJAI", "LLBG", "HECA"],
    "AS": ["VHHH", "ZSPD", "ZGGG", "ZBAA", "RKSI", "RJAA", "RJBB", "RCTP", "WSSS", "WMKK", "VTBS", "WIII", "RPLL", "VVTS", "VIDP", "VABB", "VGHS", "VCBI", "OPKC"],
    "SA": ["SBGR", "SBKP", "SBGL", "SBFZ", "SCEL", "SKBO", "SPJC", "SAEZ", "SEQM", "SVMI", "MPTO", "MDSD", "MKJP", "TJSJ", "MUHA", "MSLP"],
    "AF": ["FAOR", "FACT", "HKJK", "HAAB", "DNMM", "GMMN", "DTTA", "DAAG", "HSSK", "FNLU", "DGAA", "GOBD", "FALE"],
    "OC": ["YSSY", "YMML", "YBBN", "YPPH", "YPDN", "YBCS", "NZAA", "NZCH", "NFFN", "PHNL", "PHTO"],
}

# name, iata, bases, region keys, types, long-haul, logo slug from the branding pack
_CARGO = [
    ("FedEx Express", "FX", ["KMEM", "KIND", "KOAK"], "NA,EU,AS", ["B752", "B763", "B76F", "B77F", "A306", "MD11"], True, "fedex-express"),
    ("UPS Airlines", "5X", ["KSDF", "KRFD", "KPHL", "KONT"], "NA,EU,AS", ["B752", "B763", "B76F", "B744", "B748", "A306"], True, "ups-airlines"),
    ("Atlas Air", "5Y", ["KJFK", "KMIA", "KCVG", "KAFW"], "NA,EU,AS,SA,OC", ["B744", "B748", "B77F", "B763"], True, "atlas-air"),
    ("Polar Air Cargo", "PO", ["KJFK", "KLAX", "KCVG"], "NA,AS,EU", ["B744", "B77F"], True, "polar-air-cargo"),
    ("Kalitta Air", "K4", ["KYIP", "KJFK", "KLAX"], "NA,AS,EU", ["B744", "B77F", "B763"], True, "kalitta-air"),
    ("Western Global Airlines", "KD", ["KTPA", "KMIA", "KAFW"], "NA,SA,EU,ME", ["B744", "B77F", "MD11"], True, "western-global-airlines"),
    ("National Airlines", "N8", ["KIAB", "KJFK", "KMIA"], "NA,ME,EU,AF", ["B744", "B752", "B763"], True, "national-airlines"),
    ("Sky Lease Cargo", "GG", ["KMIA", "KJFK"], "NA,SA,EU,AS", ["B744", "B77F"], True, None),
    ("Air Transport International", "8C", ["KILN", "KCVG", "KAFW"], "NA,SA,OC", ["B763", "B76F", "B752"], False, "air-transport-international"),
    ("ABX Air", "GB", ["KILN", "KCVG"], "NA", ["B763", "B76F"], False, "abx-air"),
    ("Amerijet International", "M6", ["KMIA", "KFLL"], "SA,NA", ["B763", "B76F", "B752"], False, "amerijet-international"),
    ("Northern Air Cargo", "NC", ["PANC", "KMIA"], "NA,SA", ["B752", "B763", "B76F"], False, "northern-air-cargo"),
    ("Aloha Air Cargo", "KH", ["PHNL", "PHTO"], "OC,NA", ["B737", "B763"], False, "aloha-air-cargo"),
    ("Alaska Air Cargo", "AS", ["PANC", "KSEA"], "NA", ["B737", "B738"], False, "alaska-air-cargo"),
    ("Hawaiian Air Cargo", "HA", ["PHNL"], "OC,NA", ["A332", "B763"], False, "hawaiian-air-cargo"),
    ("Sun Country Cargo", "SY", ["KMSP", "KRFD"], "NA", ["B738"], False, "sun-country-cargo"),
    ("Southwest Cargo", "WN", ["KMDW", "KPHX", "KLAS"], "NA", ["B737", "B738"], False, "southwest-cargo"),
    ("United Cargo", "UA", ["KORD", "KEWR", "KIAH"], "NA,EU,AS", ["B763", "B772", "B788"], True, "united-cargo"),
    ("Delta Cargo", "DL", ["KATL", "KDTW", "KMSP"], "NA,EU,AS", ["B763", "A333", "B772"], True, "delta-cargo"),
    ("American Airlines Cargo", "AA", ["KDFW", "KMIA", "KORD"], "NA,EU,SA", ["B763", "B77W", "B788"], True, "american-airlines-cargo"),
    ("Cargojet Airways", "W8", ["CYHM", "CYYZ", "CYVR"], "NA,EU", ["B752", "B763", "B76F", "B77F"], False, "cargojet-airways"),
    ("Air Canada Cargo", "AC", ["CYYZ", "CYUL", "CYVR"], "NA,EU,SA", ["B763", "B77F", "A333"], True, "air-canada-cargo"),
    ("WestJet Cargo", "WS", ["CYYC", "CYYZ"], "NA,EU", ["B738", "B763"], False, "westjet-cargo"),
    ("AeroMexico Cargo", "AM", ["MMMX", "MMGL"], "NA,SA,EU", ["B763", "B788"], True, "aeromexico-cargo"),
    ("Copa Cargo", "CM", ["MPTO"], "SA,NA", ["B737", "B738"], False, "copa-cargo"),
    ("DHL Aero Expreso", "D5", ["MPTO", "KMIA"], "SA,NA", ["B738", "B763", "B76F"], False, "dhl-aero-expreso"),
    ("LATAM Cargo", "UC", ["SCEL", "SBGR", "KMIA"], "SA,NA,EU", ["B763", "B76F", "B77F"], True, "latam-cargo"),
    ("LATAM Cargo Brazil", "M3", ["SBGR", "SBKP"], "SA,NA,EU", ["B763", "B76F"], True, "latam-cargo-brazil"),
    ("LATAM Cargo Colombia", "L7", ["SKBO", "KMIA"], "SA,NA", ["B763", "B76F"], False, "latam-cargo-colombia"),
    ("Avianca Cargo", "QT", ["SKBO", "KMIA"], "SA,NA,EU", ["A332", "B763"], True, "avianca-cargo"),
    ("Azul Cargo Express", "AD", ["SBKP", "SBGR"], "SA,NA", ["A332", "B738", "E95F"], False, "azul-cargo-express"),
    ("GOLLOG Cargo", "G3", ["SBGR", "SBKP"], "SA", ["B738", "B737"], False, "gollog-cargo"),
    ("Aerolíneas Argentinas Cargo", "AR", ["SAEZ"], "SA,EU", ["A333", "B738"], False, "aerolineas-argentinas-cargo"),
    ("Cargolux", "CV", ["ELLX", "EBLG"], "EU,NA,AS,ME,AF,SA", ["B744", "B748"], True, "cargolux"),
    ("Cargolux Italia", "C8", ["LIMC", "ELLX"], "EU,AS,ME", ["B744"], True, "cargolux-italia"),
    ("AeroLogic", "3S", ["EDDP", "EDDF"], "EU,AS,ME,AF,NA", ["B77F", "B748"], True, "aerologic"),
    ("European Air Transport Leipzig", "QY", ["EDDP", "EDDK"], "EU,ME", ["A306", "A33F", "B752", "B763", "B76F"], False, "european-air-transport-leipzig"),
    ("DHL Air UK", "D0", ["EGNX", "EDDP"], "EU", ["B752", "B763", "B76F"], False, "dhl-air-uk"),
    ("DHL Air Austria", "D8", ["LOWW", "EDDP"], "EU,ME", ["B752", "B763", "B76F"], False, "dhl-air-austria"),
    ("Lufthansa Cargo", "LH", ["EDDF"], "EU,NA,AS,ME,AF,SA", ["B77F", "A333"], True, "lufthansa-cargo"),
    ("ASL Airlines Belgium", "3V", ["EBLG", "EBBR"], "EU,ME,AF", ["B738", "B752", "B763", "B76F"], False, "asl-airlines-belgium"),
    ("ASL Airlines Ireland", "AG", ["EIDW", "EBLG"], "EU", ["B738", "B752", "A306", "A21F"], False, "asl-airlines-ireland"),
    ("Challenge Airlines Belgium", "X7", ["EBLG"], "EU,AS,AF,ME", ["B744", "B763", "B76F"], True, "challenge-airlines-belgium"),
    ("Challenge Airlines Israel", "5C", ["LLBG", "EBLG"], "EU,ME,AS", ["B744", "B763"], True, "challenge-airlines-israel"),
    ("Martinair Cargo", "MP", ["EHAM"], "EU,SA,AF,NA", ["B77F", "B744"], True, "martinair-cargo"),
    ("KLM Cargo", "KL", ["EHAM"], "EU,NA,AS,AF,SA", ["B77F", "B789"], True, "klm-cargo"),
    ("Air France Cargo", "AF", ["LFPG"], "EU,NA,AS,AF,SA", ["B77F", "B789"], True, "air-france-cargo"),
    ("British Airways World Cargo", "BA", ["EGLL", "EGSS"], "EU,NA,AS,AF", ["B77W", "B788"], True, "british-airways-world-cargo"),
    ("Iberia Cargo", "IB", ["LEMD"], "EU,SA,NA", ["A332", "A333"], True, "iberia-cargo"),
    ("TAP Air Cargo", "TP", ["LPPT"], "EU,SA,AF,NA", ["A332", "A333"], True, "tap-air-cargo"),
    ("Brussels Airlines Cargo", "SN", ["EBBR"], "EU,AF", ["A333"], True, "brussels-airlines-cargo"),
    ("Austrian Cargo", "OS", ["LOWW"], "EU,AS,NA", ["B763", "B772"], True, "austrian-cargo"),
    ("SWISS WorldCargo", "LX", ["LSZH"], "EU,NA,AS,AF", ["A333", "B77W"], True, "swiss-worldcargo"),
    ("SAS Cargo", "SK", ["EKCH", "ESSA", "ENGM"], "EU,NA,AS", ["A333", "A332"], True, "sas-cargo"),
    ("Finnair Cargo", "AY", ["EFHK"], "EU,AS,NA", ["A333", "A359"], True, "finnair-cargo"),
    ("Icelandair Cargo", "FI", ["BIKF"], "EU,NA", ["B752", "B763"], False, "icelandair-cargo"),
    ("LOT Cargo", "LO", ["EPWA"], "EU,NA,AS", ["B788", "B789"], True, "lot-cargo"),
    ("Turkish Cargo", "TK", ["LTFM"], "EU,ME,AS,AF,NA,SA", ["A332", "B77F", "B744"], True, "turkish-cargo"),
    ("EgyptAir Cargo", "MS", ["HECA"], "ME,EU,AF,AS", ["A332", "B763"], True, "egyptair-cargo"),
    ("Royal Air Maroc Cargo", "AT", ["GMMN"], "AF,EU,ME", ["B738", "B788"], False, "royal-air-maroc-cargo"),
    ("Emirates SkyCargo", "EK", ["OMDW", "OMDB"], "ME,EU,AS,AF,NA,SA", ["B77F", "B744"], True, "emirates-skycargo"),
    ("Qatar Airways Cargo", "QR", ["OTHH"], "ME,EU,AS,AF,NA,SA", ["B77F", "B748", "A333"], True, "qatar-airways-cargo"),
    ("Etihad Cargo", "EY", ["OMAA"], "ME,EU,AS,AF", ["B77F", "A333"], True, "etihad-cargo"),
    ("Saudia Cargo", "SV", ["OEJN", "OERK"], "ME,EU,AS,AF", ["B77F", "B748"], True, "saudia-cargo"),
    ("Gulf Air Cargo", "GF", ["OBBI"], "ME,AS,EU", ["A332"], False, "gulf-air-cargo"),
    ("Oman Air Cargo", "WY", ["OOMS"], "ME,AS,EU", ["A332", "B788"], False, "oman-air-cargo"),
    ("Kuwait Airways Cargo", "KU", ["OKBK"], "ME,AS,EU", ["A332", "B77W"], False, "kuwait-airways-cargo"),
    ("Royal Jordanian Cargo", "RJ", ["OJAI"], "ME,EU,AS", ["A332", "B788"], False, "royal-jordanian-cargo"),
    ("Silk Way West Airlines", "7L", ["UBBB"], "ME,EU,AS,NA", ["B744", "B748", "B77F"], True, "silk-way-west-airlines"),
    ("Cathay Cargo", "CX", ["VHHH"], "AS,NA,EU,ME,OC", ["B77F", "B748"], True, "cathay-cargo"),
    ("Air Hong Kong", "LD", ["VHHH"], "AS", ["A306", "A33F"], False, "air-hong-kong"),
    ("Hong Kong Air Cargo", "RH", ["VHHH"], "AS,EU", ["A332"], False, "hong-kong-air-cargo"),
    ("Korean Air Cargo", "KE", ["RKSI"], "AS,NA,EU,ME", ["B77F", "B748"], True, "korean-air-cargo"),
    ("Asiana Cargo", "OZ", ["RKSI"], "AS,NA,EU", ["B744", "B77F"], True, "asiana-cargo"),
    ("Nippon Cargo Airlines", "KZ", ["RJAA"], "AS,NA,EU,ME", ["B748", "B744"], True, "nippon-cargo-airlines"),
    ("JAL Cargo", "JL", ["RJAA", "RJTT"], "AS,NA,EU", ["B763", "B772"], True, "jal-cargo"),
    ("ANA Cargo", "NH", ["RJAA", "RJBB"], "AS,NA,EU", ["B763", "B77F"], True, "ana-cargo"),
    ("China Airlines Cargo", "CI", ["RCTP"], "AS,NA,EU", ["B744", "B77F"], True, None),
    ("EVA Air Cargo", "BR", ["RCTP"], "AS,NA,EU", ["B77F", "B748"], True, "eva-air-cargo"),
    ("China Cargo Airlines", "CK", ["ZSPD"], "AS,NA,EU", ["B77F", "B763"], True, "china-cargo-airlines"),
    ("China Southern Cargo", "CZ", ["ZGGG", "ZSPD"], "AS,NA,EU,OC", ["B77F", "B748"], True, "china-southern-cargo"),
    ("China Eastern Cargo", "MU", ["ZSPD"], "AS,NA,EU", ["B77F", "B763"], True, "china-eastern-cargo"),
    ("Air China Cargo", "CA", ["ZBAA", "ZSPD"], "AS,NA,EU", ["B77F", "B744"], True, "air-china-cargo"),
    ("SF Airlines", "O3", ["ZSPD", "ZGGG"], "AS", ["B738", "B752", "B763", "B77F"], False, "sf-airlines"),
    ("China Postal Airlines", "CF", ["ZBAA", "ZSPD"], "AS", ["B738", "B752"], False, "china-postal-airlines"),
    ("Suparna Airlines", "Y8", ["ZSPD", "ZGGG"], "AS,EU,ME", ["B744", "B763"], True, "suparna-airlines"),
    ("Singapore Airlines Cargo", "SQ", ["WSSS"], "AS,EU,NA,OC", ["B77F", "B744"], True, "singapore-airlines-cargo"),
    ("Malaysia Airlines Cargo", "MH", ["WMKK"], "AS,OC,EU", ["A333"], False, "malaysia-airlines-cargo"),
    ("Garuda Indonesia Cargo", "GA", ["WIII"], "AS,OC,ME", ["B738", "A333"], False, "garuda-indonesia-cargo"),
    ("Thai Airways Cargo", "TG", ["VTBS"], "AS,EU,OC", ["B77W", "A333"], True, "thai-airways-cargo"),
    ("Vietnam Airlines Cargo", "VN", ["VVTS"], "AS,EU,OC", ["A333", "B789"], False, "vietnam-airlines-cargo"),
    ("Philippine Airlines Cargo", "PR", ["RPLL"], "AS,NA,ME", ["A333", "B77W"], True, "philippine-airlines-cargo"),
    ("Air India Cargo", "AI", ["VIDP", "VABB"], "AS,ME,EU", ["B763", "A332"], False, "air-india-cargo"),
    ("Pakistan International Cargo", "PK", ["OPKC", "OPLA"], "AS,ME,EU", ["B77W", "A332"], False, "pakistan-international-cargo"),
    ("Biman Cargo", "BG", ["VGHS"], "AS,ME", ["B788", "B738"], False, "biman-cargo"),
    ("SriLankan Cargo", "UL", ["VCBI"], "AS,ME", ["A332", "A333"], False, "srilankan-cargo"),
    ("Qantas Freight", "QF", ["YSSY", "YMML", "YBBN"], "OC,AS,NA", ["B763", "A21F", "A33F"], True, "qantas-freight"),
    ("Air New Zealand Cargo", "NZ", ["NZAA", "NZCH"], "OC,AS,NA", ["B77W", "B789"], True, "air-new-zealand-cargo"),
    ("Ethiopian Cargo", "ET", ["HAAB"], "AF,ME,EU,AS,NA", ["B77F", "B738"], True, "ethiopian-cargo"),
    ("Kenya Airways Cargo", "KQ", ["HKJK"], "AF,ME,EU,AS", ["B738", "B788"], False, "kenya-airways-cargo"),
    ("Astral Aviation", "8V", ["HKJK"], "AF,ME", ["B752", "B763", "AT76", "E19F"], False, "astral-aviation"),
    ("South African Airways Cargo", "SA", ["FAOR", "FACT"], "AF,EU,ME", ["A333", "B763"], True, "south-african-airways-cargo"),
    # the small operators keeping the 727 and the E-Jet freighter flying
    ("Bridges Air Cargo", "9H", ["LMML", "EBLG"], "EU,AF", ["E19F", "E95F"], False, None),
    # regional and feeder freight, where a night mail run beats a transatlantic sector
    ("West Atlantic UK", "NPT", ["EGNX", "EGGW", "EGPH"], "EU", ["B75F", "AT43", "SF34"], False, None),
    ("Bluebird Nordic", "BBD", ["BIKF", "EKCH", "EGNX"], "EU", ["B38F", "B75F"], False, None),
    ("Swiftair", "WT", ["LEMD", "LEBL", "LFPG"], "EU,AF", ["AT43", "AT7F", "B38F"], False, None),
    ("Jota Aviation", "ENZ", ["EGMC", "EGNX", "EGSS"], "EU", ["AT43", "B38F"], False, None),
    ("Loganair Cargo", "LM", ["EGPF", "EGPD", "EGNX"], "EU", ["AT43", "SF34"], False, None),
    ("Aer Lingus Regional Cargo", "EI", ["EIDW", "EGNX"], "EU", ["AT43", "AT7F"], False, None),
    ("Air Contractors Feeder", "AG", ["EIDW", "EGNX", "EBLG"], "EU", ["AT43", "AT7F", "B75F"], False, None),
    ("FedEx Feeder Europe", "FX", ["EGNX", "EDDK", "LFPG"], "EU", ["C208", "AT43", "SF34"], False, "fedex-express"),
    ("Mountain Air Cargo", "MTN", ["KAVL", "KCLT", "KMEM"], "NA", ["C208", "AT43"], False, None),
    ("Empire Airlines", "EM", ["KMEM", "KSFF", "KBOI"], "NA", ["C208", "AT43", "AT7F"], False, None),
    ("Kenn Borek Air", "KBA", ["CYZF", "CYYC", "NZCH"], "NA", ["DHC6", "DC3"], False, None),
    ("Buffalo Airways", "BFL", ["CYZF", "CYHY"], "NA", ["DC3"], False, None),
    ("Everts Air Cargo", "VTS", ["PANC", "PAFA"], "NA", ["DC3", "C208"], False, None),
    ("USA Jet Airlines", "U7", ["KYIP", "KDTW"], "NA", ["B722", "B738"], False, None),
    ("IFL Group", "IFL", ["KYIP", "KILN"], "NA", ["B722", "CR2F"], False, None),
    ("Aeronaves TSM", "TSM", ["MMIO", "MMMY"], "NA", ["CR2F", "B738"], False, None),
    ("Air Class Lineas Aereas", "QD", ["SUMU", "SBGR"], "SA", ["B722"], False, None),
    ("Solar Cargo", "4S", ["SVVA", "SKBO"], "SA", ["B722"], False, None),
    ("Safe Air Company", "6S", ["HKJK", "HKNW" if False else "HKJK"], "AF,ME", ["B722"], False, None),
    ("Serve Air Cargo", "SVR", ["FZAA", "FZQA"], "AF", ["B722", "B738"], False, None),
    ("MNG Airlines", "MB", ["LTFM", "LTBA" if False else "LTFM"], "EU,ME,AS", ["A306", "A333"], False, None),
]

CARGO_CARRIERS = []
for _n, _i, _b, _r, _t, _lh, _logo in _CARGO:
    _net = []
    for _k in _r.split(","):
        _net += _NET.get(_k, [])
    _net = [x for x in dict.fromkeys(_net) if x in AIRPORTS and x not in _b]
    _bases = [x for x in _b if x in AIRPORTS] or ["KMEM"]
    CARGO_CARRIERS.append(dict(name=_n, iata=_i, bases=_bases, types=[t for t in _t if t in AIRCRAFT], network=_net, long_haul=_lh, logo=_logo))
CARGO_CARRIERS = [c for c in CARGO_CARRIERS if c["types"] and c["network"]]

OPERATOR_LOGOS = {c["name"]: c["logo"] for c in CARGO_CARRIERS if c["logo"]}
# Placeholder wordmarks generated for operators with no licensed asset in the pack.
# A real file dropped into static/operators/ under the same name simply overrides the artwork.
_TONE = _os.path.join(_BASE, "logo_tone.json")
LOGO_TONE = {}
if _os.path.exists(_TONE):
    with open(_TONE, encoding="utf-8") as _fh:
        LOGO_TONE = _json.load(_fh)

_PLH = _os.path.join(_BASE, "placeholder_logos.json")
PLACEHOLDER_LOGOS = {}
if _os.path.exists(_PLH):
    with open(_PLH, encoding="utf-8") as _fh:
        PLACEHOLDER_LOGOS = _json.load(_fh)
for _n, _f in PLACEHOLDER_LOGOS.items():
    OPERATOR_LOGOS.setdefault(_n, _f)

# Ferry clients and ACMI customers that are the same cargo operator under a shorter name.
# Only cargo entities are branded: a passenger wet lease should not carry a cargo-division mark.
OPERATOR_LOGOS.update({
    "Cargojet": "cargojet-airways",
    "ASL Airlines": "asl-airlines-belgium",
    "DHL Express": "dhl-air-uk",
})

CARGO_LOADS = [
    ("General freight and e-commerce", 0.75, False),
    ("Express parcels", 0.6, False),
    ("Perishables — flowers and seafood", 0.7, False),
    ("Pharmaceuticals, temperature controlled", 0.55, False),
    ("Automotive parts", 0.8, False),
    ("Live animals — horses", 0.5, False),
    ("Oversize project cargo", 0.85, True),
    ("Aircraft engine (AOG)", 0.45, True),
    ("Dangerous goods — lithium batteries", 0.65, True),
    ("Dangerous goods — flammable liquids", 0.6, True),
    ("Mail", 0.5, False),
    ("Humanitarian relief supplies", 0.7, False),
    ("Military charter — palletised freight", 0.8, True),
    ("Semiconductor equipment", 0.55, True),
]


# Airports customarily used as technical stops on ferry flights: fuel, customs,
# handling and support for a crew of two at short notice.
FERRY_STOPS = {
    # North Atlantic / polar
    "BIKF": 3, "CYQX": 3, "CYYR": 2, "BGSF": 2, "CYFB": 1, "EINN": 3, "LPLA": 3, "LPAZ": 2, "CYHZ": 1, "CYUL": 1, "KBGR" : 2,
    # Pacific / Alaska
    "PANC": 3, "PACD": 2, "PAKN": 1, "PMDY": 1, "RJCC": 2, "UHPP": 1, "PHNL": 2, "PHTO": 1, "NSTU": 1, "NFFN": 2, "PGUM": 2,
    # Middle East / Asia corridor
    "OMDB": 3, "OMDW": 2, "OBBI": 2, "OERK": 1, "OJAI": 2, "LTFM": 2, "UBBB": 2, "UAAA": 1, "OPKC": 1, "VABB": 2, "VCBI": 1,
    "VTBS": 2, "WSSS": 3, "VHHH": 2, "RPLL": 1, "WADD": 1, "YPDN": 2, "YBAS": 1,
    # Africa / South Atlantic
    "GVAC": 3, "GOBD": 2, "DNMM": 1, "HAAB": 2, "HKJK": 2, "FAOR": 2, "FNLU": 1, "HECA": 2, "GMMN": 2, "FIMP": 1, "FSIA": 1,
    # Americas
    "SBFZ": 3, "SBGL": 1, "TJSJ": 2, "MDSD": 1, "MMMX": 1, "KBGR2" if False else "KMIA": 2, "KOAK": 1, "SCEL": 1, "SPJC": 1, "MPTO": 1,
    # Europe
    "EGSS": 1, "LFPG": 1, "EDDF": 1, "LEMD": 1, "LGAV": 1, "LMML": 2, "LICJ": 1, "EFHK": 1, "ENZV": 1,
}


def snags_for(type_code):
    """The deferred defects that can genuinely exist on this type."""
    ac = AIRCRAFT.get(type_code) or {}
    fam, rng = ac.get("family"), ac.get("range_nm", 0)
    out = []
    for sn in SNAGS:
        if fam in (sn.get("excludes") or ()):
            continue
        if rng < (sn.get("min_range") or 0):
            continue
        ceiling = CEILING_FT.get(fam)
        if sn.get("max_alt") and ceiling and sn["max_alt"] >= ceiling - 2000:
            continue                       # a cap above the type's ceiling restricts nothing
        # the selection metadata stays out of the saved job
        out.append({k: v for k, v in sn.items() if k not in ("excludes", "min_range")})
    return out


# What each operator actually flies, by type-rating family. Jobs only pair an operator
# with an aircraft from its own fleet: Southwest is a 737 operator, Allegiant an A320
# operator, and neither has ever taken an E-Jet.
OPERATOR_FLEETS = {
    # ---- Europe
    "Lufthansa": {"A320", "A330/A350", "B747", "B777/787", "CRJ", "E-Jet"},   # CityLine
    "Eurowings": {"A320"},
    "Condor": {"A320", "A330/A350"},
    "TUI fly": {"B737"},
    "TUI Airways": {"B737", "B777/787"},
    "KLM": {"B737", "A330/A350", "B777/787", "E-Jet"},
    "Transavia": {"B737", "A320"},
    "Air France": {"A320", "A330/A350", "B777/787", "E-Jet"},
    "easyJet": {"A320"},
    "Jet2": {"B737", "A320", "B757/767"},      # 757s appear on wet lease in summer
    "British Airways": {"A320", "A330/A350", "B747", "B777/787"},
    "Virgin Atlantic": {"A330/A350", "B777/787"},
    "SAS": {"A320", "A330/A350", "E-Jet", "ATR", "CRJ"},   # SAS Link and Xfly
    "Norwegian": {"B737"},
    "Finnair": {"A320", "A330/A350", "E-Jet"},
    "LOT Polish Airlines": {"B737", "B777/787", "E-Jet"},
    "Austrian Airlines": {"A320", "B777/787", "E-Jet"},
    "Brussels Airlines": {"A320", "A330/A350"},
    "SWISS": {"A320", "A330/A350", "B777/787"},
    "Aer Lingus": {"A320", "A330/A350"},
    "Air Serbia": {"A320", "ATR", "E-Jet"},
    "Wizz Air": {"A320"},
    "Vueling": {"A320"},
    "Iberia": {"A320", "A330/A350"},
    "TAP Air Portugal": {"A320", "A330/A350", "E-Jet"},
    "airBaltic": {"A320"},
    "Icelandair": {"B737", "B757/767"},
    "Air Europa": {"B737", "B777/787"},
    "ITA Airways": {"A320", "A330/A350"},
    "Pegasus": {"A320", "B737"},
    "SunExpress": {"B737"},
    "Corendon Airlines": {"B737"},
    "Air Malta": {"A320"},
    "Aegean Airlines": {"A320", "ATR"},
    "Croatia Airlines": {"A320", "Q400"},
    "Luxair": {"B737", "Q400", "E-Jet"},
    "Edelweiss": {"A320", "A330/A350"},
    "Ryanair": {"B737"},

    # ---- North America
    "Air Canada": {"A320", "A330/A350", "B737", "B777/787", "E-Jet", "CRJ", "Q400"},   # Jazz
    "WestJet": {"B737", "B777/787", "Q400"},
    "Sun Country Airlines": {"B737"},
    "Frontier Airlines": {"A320"},
    "Delta Air Lines": {"A320", "A330/A350", "B737", "B757/767", "B777/787", "CRJ", "E-Jet"},   # Delta Connection
    "United Airlines": {"A320", "B737", "B757/767", "B777/787", "CRJ", "E-Jet"},
    "American Airlines": {"A320", "B737", "B777/787", "CRJ", "E-Jet"},
    "Southwest Airlines": {"B737"},
    "JetBlue": {"A320"},                       # last E190 retired in 2025
    "Alaska Airlines": {"B737", "A320", "E-Jet"},
    "Spirit Airlines": {"A320"},
    "Allegiant Air": {"A320", "B737"},
    "Volaris": {"A320"},
    "Aeromexico": {"B737", "B777/787"},
    "Copa Airlines": {"B737"},

    # ---- South America
    "Azul": {"A320", "A330/A350", "ATR", "E-Jet"},
    "LATAM Airlines": {"A320", "B777/787", "B767" if False else "B757/767"},
    "GOL": {"B737"},
    "Avianca": {"A320", "B777/787"},

    # ---- Middle East, Africa, Asia-Pacific
    "Emirates": {"A330/A350", "B777/787"},
    "Qatar Airways": {"A320", "A330/A350", "B777/787"},
    "Etihad Airways": {"A320", "A330/A350", "B777/787"},
    "Saudia": {"A320", "A330/A350", "B777/787"},
    "flynas": {"A320"},
    "Oman Air": {"B737", "A330/A350", "B777/787"},
    "Gulf Air": {"A320", "B777/787"},
    "Royal Jordanian": {"A320", "B777/787", "E-Jet"},
    "EgyptAir": {"A320", "B737", "A330/A350", "B777/787"},
    "Royal Air Maroc": {"B737", "B777/787", "E-Jet"},
    "Turkish Airlines": {"A320", "A330/A350", "B737", "B777/787"},
    "Air Astana": {"A320", "B757/767", "E-Jet"},
    "Kenya Airways": {"B737", "B777/787", "E-Jet"},
    "Ethiopian Airlines": {"A330/A350", "B737", "B777/787", "Q400"},
    "South African Airways": {"A320", "A330/A350"},
    "Air India": {"A320", "A330/A350", "B777/787"},
    "IndiGo": {"A320", "ATR"},
    "Qantas": {"A320", "A330/A350", "B737", "B777/787", "Q400"},   # QantasLink
    "Air New Zealand": {"A320", "B777/787", "ATR", "Q400"},
    "Air Tahiti Nui": {"B777/787"},
    "Fiji Airways": {"A320", "A330/A350", "B737"},
    "Cathay Pacific": {"A320", "A330/A350", "B777/787"},
    "Singapore Airlines": {"A320", "A330/A350", "B737", "B777/787"},
    "Japan Airlines": {"A320", "A330/A350", "B737", "B777/787"},
    "All Nippon Airways": {"A320", "B737", "B777/787"},
    "Korean Air": {"A320", "A330/A350", "B737", "B747", "B777/787"},
    "China Southern": {"A320", "A330/A350", "B737", "B777/787"},

    # ---- freight
    "Atlas Air": {"B747", "B777/787", "B757/767"},
    "Bridges Air Cargo": {"E-Jet"},
    "USA Jet Airlines": {"B727", "B737"},
    "IFL Group": {"B727", "CRJ"},
    "Aeronaves TSM": {"CRJ", "B737"},
    "Air Class Lineas Aereas": {"B727"},
    "Solar Cargo": {"B727"},
    "Safe Air Company": {"B727"},
    "Serve Air Cargo": {"B727", "B737"},
    "MNG Airlines": {"A300", "A330/A350"},
    "European Air Transport Leipzig": {"A300", "A330/A350", "B757/767"},
    "Air Hong Kong": {"A300", "A330/A350"},
    "Astral Aviation": {"B757/767", "ATR", "E-Jet"},
    "Qantas Freight": {"B757/767", "A320", "A330/A350"},
    "Cargolux": {"B747"},
    "ASL Airlines": {"B737", "B757/767", "A330/A350", "A300", "A320"},
    "Cargojet": {"B757/767", "B777/787"},
    "Kalitta Air": {"B747", "B757/767", "B777/787"},
    "Western Global Airlines": {"B747", "B777/787", "MD-11"},
    "AirBridgeCargo": {"B747", "B777/787"},
}


# The ACMI customer list and the operator fleet list must agree: reconcile them once,
# with OPERATOR_FLEETS as the source of truth for who flies what.
for _c in ACMI_CUSTOMERS:
    _known = OPERATOR_FLEETS.get(_c["name"])
    if _known:
        _kept = [f for f in _c["fams"] if f in _known]
        if _kept:
            _c["fams"] = _kept


def operators_for(type_code, pool=None):
    """Operators that fly this exact aircraft, not merely something on the same rating."""
    src = pool if pool is not None else OPERATORS
    out = [o for o in src if type_code in OPERATOR_TYPES.get(o, ())]
    if out:
        return out
    # no explicit fleet recorded: fall back to the rating grouping
    fam = (AIRCRAFT.get(type_code) or {}).get("family")
    out = [o for o in src if fam in OPERATOR_FLEETS.get(o, set()) and o not in OPERATOR_TYPES]
    return out or list(src)


def types_for(operator):
    """What this operator flies."""
    if operator in OPERATOR_TYPES:
        return list(OPERATOR_TYPES[operator])
    fams = OPERATOR_FLEETS.get(operator, set())
    return [t for t, a in AIRCRAFT.items() if a["family"] in fams]


# ---------------------------------------------------------------- private charter
# Real charter brokers place most on-demand work. You quote, they compare, and the
# client picks; win or lose depends on your price against the going rate, your
# reputation, and how new and comfortable the cabin is.
# Where business aviation actually operates from.
CHARTER_HUBS = ["KTEB", "KHPN", "KVNY", "KOPF", "KAPA", "KDAL", "KLAS", "KMIA", "KBED", "KPDK",
                "KIAD", "KSNA", "KSJC", "KBFI", "CYYZ", "CYUL", "MMTO" if False else "MMMX",
                "LFPB", "EGLF", "EGGW", "EGLC", "LSGG", "LSZH", "LIML", "EDDM", "EDDB", "LEMD",
                "LEPA", "LIRA", "LOWW", "EKCH", "ESSB" if False else "ESSA", "EIDW", "LFMN",
                "OMDW", "OTHH", "OERK", "LTFM", "VHHH", "WSSS", "RJTT", "VABB", "YSSY", "YMML",
                "FAOR", "SBSP", "SKBO", "SAEZ", "MMUN"]
CHARTER_HUBS = [h for h in CHARTER_HUBS if h in AIRPORTS]

BROKERS = [
    # Real charter brokers and marketplaces. They place the work; you fly it.
    dict(name="Air Charter Service", weight=3, fussy=1.00, note="the largest broker by volume, everything from light jets to freighters"),
    dict(name="Air Partner", weight=2, fussy=1.05, note="part of Wheels Up; corporate and group work"),
    dict(name="Chapman Freeborn", weight=2, fussy=0.95, note="broad broker, strong on group and cargo"),
    dict(name="Avinode marketplace", weight=3, fussy=0.90, note="the industry's booking marketplace: fast, price-led"),
    dict(name="Paramount Business Jets", weight=2, fussy=1.05, note="vets operators closely and expects paperwork"),
    dict(name="Jet Linx", weight=1, fussy=1.10, note="membership operator that sources lift locally"),
    dict(name="XO", weight=2, fussy=1.00, note="Vista's digital marketplace; app-driven and price-transparent"),
    dict(name="FXAir", weight=1, fussy=1.05, note="formerly PrivateFly, now part of the Directional group"),
    dict(name="Direct client", weight=2, fussy=1.15, note="no broker in the middle: the client is judging you directly"),
]

# Competing operators — who you lose trips to.
CHARTER_COMPETITORS = ["NetJets", "Flexjet", "VistaJet", "Wheels Up", "flyExclusive", "Jet Linx",
                       "Solairus Aviation", "Luxaviation", "GlobeAir", "Air Hamburg", "ExecuJet",
                       "Clay Lacy Aviation", "Gama Aviation", "PlaneSense", "Airshare"]

# What a client is like to fly for. Sensitivities drive both the odds of winning the
# work and what they notice afterwards.
CHARTER_CLIENTS = [
    dict(kind="Corporate group", story="a board party travelling to a site visit",
         price=1.00, cares=dict(punctual=0.45, comfort=0.30, cabin=0.25), tolerance=1.0),
    dict(kind="Private owner", story="a family trip with luggage and a dog",
         price=1.05, cares=dict(punctual=0.25, comfort=0.45, cabin=0.30), tolerance=0.9),
    dict(kind="Investment fund", story="due diligence visits, several cities in as few days as possible",
         price=1.15, cares=dict(punctual=0.60, comfort=0.25, cabin=0.15), tolerance=0.75),
    dict(kind="Sports team", story="a squad, coaching staff and their kit",
         price=0.92, cares=dict(punctual=0.50, comfort=0.25, cabin=0.25), tolerance=1.1),
    dict(kind="Film production", story="crew, camera equipment and a tight shooting schedule",
         price=0.98, cares=dict(punctual=0.55, comfort=0.20, cabin=0.25), tolerance=1.0),
    dict(kind="Government delegation", story="an official visit with protocol requirements",
         price=1.25, cares=dict(punctual=0.55, comfort=0.20, cabin=0.25), tolerance=0.7),
    dict(kind="Medical transfer", story="a patient with a medical escort and equipment",
         price=1.10, cares=dict(punctual=0.65, comfort=0.30, cabin=0.05), tolerance=0.6),
    dict(kind="Tour operator", story="a group connecting to a cruise departure",
         price=0.88, cares=dict(punctual=0.55, comfort=0.20, cabin=0.25), tolerance=1.2),
    dict(kind="Music tour", story="a band, management and instruments between show nights",
         price=1.02, cares=dict(punctual=0.45, comfort=0.35, cabin=0.20), tolerance=1.0),
    dict(kind="Head of state visit", story="a state visit with security and strict timings",
         price=1.35, cares=dict(punctual=0.70, comfort=0.20, cabin=0.10), tolerance=0.5),
]

# The shape of the work. Each archetype flies differently and pays differently.
CHARTER_TRIPS = [
    dict(key="one_way", label="One-way", weight=5, mult=1.00, days=0, stops=0,
         desc="A single sector. You position in empty and go home empty unless you can sell the leg."),
    dict(key="day_return", label="Day return", weight=5, mult=1.85, days=0, stops=0, same_day=True,
         desc="Out in the morning, wait on the ground, home the same evening. The crew's day is long."),
    dict(key="overnight", label="Overnight", weight=4, mult=1.95, days=2, stops=0, same_day=True,
         desc="Out one day, back another. Crew hotel and per diem are yours to pay."),
    dict(key="roadshow", label="Multi-city roadshow", weight=3, mult=2.9, days=3, stops=2, same_day=True,
         desc="Several cities in as few days as possible. Every sector counts and the schedule is unforgiving."),
    dict(key="tour", label="Tour leg", weight=2, mult=1.5, days=1, stops=1, same_day=False,
         desc="One leg of a longer itinerary, handed to you because the regular operator is short."),
    dict(key="urgent", label="Short notice", weight=3, mult=1.35, days=0, stops=0, urgent=True,
         desc="Wheels up within a day or two. Pays well because nobody else can cover it."),
    dict(key="medevac", label="Medical transfer", weight=1, mult=1.5, days=0, stops=0, urgent=True,
         desc="A patient and escort, on a schedule set by a hospital rather than a diary."),
    dict(key="group", label="Group charter", weight=2, mult=1.25, days=0, stops=0,
         desc="More passengers than a light jet will take. Cabin size decides whether you can bid at all."),
    dict(key="long_range", label="Long range", weight=2, mult=1.15, days=1, stops=0,
         desc="Intercontinental, with customs at both ends and a crew close to their duty limit."),
    dict(key="event", label="Event peak", weight=2, mult=1.6, days=1, stops=0, event=True,
         desc="Everyone wants the same airport on the same day. Rates rise, slots are scarce."),
]

CHARTER_EVENTS = [
    ("the Monaco Grand Prix", ["LFMN", "LIML"]), ("the Davos forum", ["LSZH", "LSGG"]),
    ("the Super Bowl", ["KLAS", "KMIA", "KDAL"]), ("the Cannes festival", ["LFMN", "LFMD" if False else "LFMN"]),
    ("the Masters", ["KATL", "KCLT"]), ("the Farnborough air show", ["EGLF", "EGGW"]),
    ("Art Basel", ["LSZH", "KMIA"]), ("the Ryder Cup", ["EIDW", "KORD"]),
    ("a heads-of-state summit", ["LFPB", "EBBR"]), ("the Dubai air show", ["OMDW", "OMDB"]),
]

# Requirements a trip may carry. Each is checked against the aircraft you would fly.
CHARTER_EXTRAS = [
    dict(text="skis and boards in the baggage hold", mult=1.05, need="baggage"),
    dict(text="golf clubs for four", mult=1.00, need="baggage"),
    dict(text="a dog travelling in the cabin", mult=1.05, need=None),
    dict(text="catering from a named restaurant", mult=1.10, need=None),
    dict(text="customs and immigration on arrival", mult=1.05, need="customs"),
    dict(text="a cabin attendant throughout", mult=1.15, need="attendant"),
    dict(text="wi-fi that works over the ocean", mult=1.10, need="wifi"),
    dict(text="a wheelchair and assistance at both ends", mult=1.05, need=None),
    dict(text="press waiting at the destination", mult=1.10, need=None),
    dict(text="discretion: no tail number published", mult=1.05, need=None),
    dict(text="a short runway at the destination", mult=1.10, need="short_field"),
    dict(text="an early departure before the noise curfew lifts", mult=1.08, need="curfew"),
]

# Short, demanding fields that charter clients nonetheless want to use.
SHORT_FIELDS = ["KASE", "LSZS", "LFLJ" if False else "LSGS", "EGLC", "LOWI", "LIRQ", "KTEB", "EGKB", "LFMD" if False else "LFMN"]



# When each type was actually built, so a listing cannot be older than the aeroplane.
# (first year of delivery, last year of production or None if still in production)
BUILD_YEARS = {
    "A319": (1996, 2021), "A320": (1988, 2021), "A321": (1994, 2021), "A20N": (2016, None), "A21N": (2017, None),
    "A21F": (1994, 2021), "A332": (1998, 2022), "A333": (1999, 2019), "A339": (2018, None), "A359": (2015, None),
    "A33F": (1999, 2019), "A306": (1984, 2007),
    "B737": (1997, 2004), "B738": (1998, 2019), "B739": (2001, 2019), "B38M": (2017, None),
    "B744": (1989, 2005), "B748": (2011, 2023), "B752": (1983, 2004), "B763": (1986, 2014), "B76F": (1995, 2014),
    "B772": (1995, 2013), "B77W": (2004, None), "B77F": (2009, None), "B788": (2011, None), "B789": (2014, None),
    "B722": (1967, 1984), "MD11": (1990, 2000),
    "DC3": (1936, 1945), "C208": (1990, None), "DHC6": (1965, None), "SF34": (1989, 1999), "AT43": (1985, 1996), "B75F": (1987, 2004), "B38F": (1998, 2019), "AT7F": (2010, None),
    "E190": (2005, 2018), "E195": (2006, 2018), "E19F": (2005, 2018), "E95F": (2006, 2018),
    "CRJ9": (2003, 2020), "CR2F": (1991, 2006), "AT76": (2010, None), "DH8D": (2000, 2021),
    # business aircraft
    "PC12": (2019, None),        # NGX
    "BE20": (2009, None),        # 350i
    "E55P": (2020, None),        # Phenom 300E
    "C25C": (2010, None),        # CJ4
    "C56X": (2008, None),
    "H25B": (1995, 2005),        # 800XP; the 850XP followed        # XLS+
    "E545": (2019, None),        # Praetor 600
    "CL35": (2014, None),        # Challenger 350
    "GLF6": (2014, None),        # G650ER
    "GL7T": (2018, None),        # Global 7500
    "FA8X": (2016, None),        # Falcon 8X
}


def build_year_range(code, now_year):
    lo, hi = BUILD_YEARS.get(code, (now_year - 25, None))
    return lo, min(hi or now_year, now_year)


# What each operator actually flies, aircraft by aircraft. Type ratings group aircraft
# that a pilot can fly on one licence - a B757/767 rating covers both - but airlines do
# not follow those groupings, so fleets are listed by type. Jet2 flies 737s and A321neos
# and has never operated a 767.
OPERATOR_TYPES = {
    # ---- Europe
    "Lufthansa": ["A319", "A320", "A20N", "A321", "A21N", "A333", "A359", "B744", "B748", "B789", "CRJ9", "E190", "E195"],
    "Eurowings": ["A319", "A320", "A20N", "A321"],
    "Condor": ["A320", "A21N", "A339"],
    "TUI fly": ["B738", "B38M"],
    "TUI Airways": ["B738", "B38M", "B789"],
    "KLM": ["B737", "B738", "B739", "A332", "A333", "B772", "B77W", "B789", "E190", "E195"],
    "Transavia": ["B737", "B738", "A20N", "A21N"],
    "Air France": ["A319", "A320", "A321", "A20N", "A21N", "A332", "A333", "A359", "B772", "B77W", "B789", "E190", "E195"],
    "easyJet": ["A319", "A320", "A20N", "A321", "A21N"],
    "Jet2": ["B738", "A21N"],
    "British Airways": ["A319", "A320", "A20N", "A321", "A21N", "A359", "B772", "B77W", "B788", "B789"],
    "Virgin Atlantic": ["A333", "A339", "A359", "B789"],
    "SAS": ["A319", "A320", "A20N", "A321", "A21N", "A333", "A359", "E195", "AT76"],
    "Norwegian": ["B738", "B38M"],
    "LOT Polish Airlines": ["B737", "B738", "B38M", "B789", "E190", "E195"],
    "Austrian Airlines": ["A320", "A321", "A20N", "B763", "B772", "E195"],
    "Brussels Airlines": ["A319", "A320", "A21N", "A333"],
    "SWISS": ["A320", "A20N", "A321", "A21N", "A333", "A359", "B77W"],
    "Aer Lingus": ["A320", "A21N", "A332", "A333"],
    "Air Serbia": ["A319", "A320", "A21N", "AT76", "E195"],
    "Wizz Air": ["A320", "A20N", "A321", "A21N"],
    "Vueling": ["A319", "A320", "A21N"],
    "Iberia": ["A320", "A20N", "A321", "A21N", "A333", "A359"],
    "TAP Air Portugal": ["A320", "A20N", "A321", "A21N", "A333", "A339", "E190", "E195"],
    "airBaltic": ["A20N"],
    "Icelandair": ["B752", "B763", "B38M"],
    "Air Europa": ["B738", "B788", "B789"],
    "ITA Airways": ["A320", "A20N", "A321", "A21N", "A333", "A359"],
    "Pegasus": ["A320", "A20N", "A21N", "B738"],
    "SunExpress": ["B738", "B38M"],
    "Corendon Airlines": ["B738", "B38M"],
    "Air Malta": ["A320", "A20N"],
    "Aegean Airlines": ["A320", "A20N", "A321", "A21N", "AT76"],
    "Croatia Airlines": ["A319", "A320", "DH8D"],
    "Luxair": ["B737", "B738", "DH8D", "E190", "E195"],
    "Edelweiss": ["A320", "A21N", "A333"],
    "Ryanair": ["B738", "B38M"],

    # ---- North America
    "Air Canada": ["A319", "A320", "A321", "A20N", "A21N", "A333", "B38M", "B763", "B772", "B77W", "B788", "B789", "CRJ9", "DH8D"],
    "WestJet": ["B737", "B738", "B38M", "B788", "DH8D"],
    "Sun Country Airlines": ["B738"],
    "Frontier Airlines": ["A320", "A20N", "A21N"],
    "Delta Air Lines": ["A319", "A320", "A321", "A21N", "A332", "A333", "A339", "A359", "B737", "B738", "B739", "B752", "B763", "CRJ9", "E195"],
    "United Airlines": ["A319", "A320", "A21N", "B737", "B738", "B739", "B38M", "B752", "B763", "B772", "B77W", "B788", "B789", "CRJ9"],
    "American Airlines": ["A319", "A320", "A321", "A21N", "B738", "B38M", "B772", "B77W", "B788", "B789", "CRJ9"],
    "Southwest Airlines": ["B737", "B738", "B38M"],
    "JetBlue": ["A320", "A321", "A20N", "A21N"],
    "Alaska Airlines": ["B738", "B739", "B38M", "E190"],
    "Spirit Airlines": ["A319", "A320", "A20N", "A21N"],
    "Allegiant Air": ["A319", "A320", "B38M"],
    "Volaris": ["A320", "A20N", "A321", "A21N"],
    "Aeromexico": ["B738", "B38M", "B788", "B789"],
    "Copa Airlines": ["B738", "B38M"],

    # ---- South America
    "Azul": ["A20N", "A339", "AT76", "E195", "E95F"],
    "LATAM Airlines": ["A319", "A320", "A20N", "A321", "A21N", "B763", "B772", "B77W", "B788", "B789"],
    "GOL": ["B737", "B738", "B38M"],
    "Avianca": ["A319", "A320", "A20N", "A321", "B788", "B789"],

    # ---- Middle East, Africa, Asia-Pacific
    "Emirates": ["A359", "B77W", "B77F"],
    "Qatar Airways": ["A320", "A21N", "A333", "A359", "B77W", "B77F", "B788", "B789"],
    "Etihad Airways": ["A320", "A21N", "A359", "B77W", "B788", "B789"],
    "Saudia": ["A320", "A21N", "A333", "B77W", "B789"],
    "flynas": ["A320", "A20N", "A21N"],
    "Oman Air": ["B738", "B38M", "A333", "B789"],
    "Gulf Air": ["A20N", "A21N", "B789"],
    "Royal Jordanian": ["A320", "A321", "A20N", "B788", "E195"],
    "EgyptAir": ["A320", "A20N", "A21N", "B738", "A333", "B77W", "B789"],
    "Royal Air Maroc": ["B737", "B738", "B38M", "B788", "B789", "E190"],
    "Turkish Airlines": ["A319", "A320", "A321", "A20N", "A21N", "A333", "A359", "B738", "B38M", "B77W", "B789", "B77F"],
    "Air Astana": ["A320", "A20N", "A321", "A21N", "B763", "E190"],
    "Kenya Airways": ["B738", "B77F", "B788", "E190"],
    "Ethiopian Airlines": ["A359", "B738", "B38M", "B77W", "B77F", "B788", "B789", "DH8D"],
    "South African Airways": ["A320", "A333"],
    "Air India": ["A319", "A320", "A321", "A20N", "A21N", "A359", "B772", "B77W", "B788", "B789"],
    "IndiGo": ["A320", "A20N", "A21N", "AT76"],
    "Qantas": ["A320", "A21N", "A332", "A333", "A359", "B738", "B789", "DH8D"],
    "Air New Zealand": ["A320", "A21N", "B789", "AT76", "DH8D"],
    "Air Tahiti Nui": ["B789"],
    "Fiji Airways": ["A332", "A333", "A359", "B738", "B38M"],
    "Cathay Pacific": ["A21N", "A333", "A359", "B77W", "B77F"],
    "Singapore Airlines": ["A320", "A21N", "A333", "A359", "B738", "B38M", "B77W", "B77F", "B788", "B789"],
    "Japan Airlines": ["A359", "B738", "B763", "B772", "B77W", "B788", "B789", "E190"],
    "All Nippon Airways": ["A320", "A21N", "B738", "B763", "B772", "B77W", "B788", "B789"],
    "Korean Air": ["A20N", "A321", "A333", "A359", "B744", "B748", "B77W", "B77F", "B738", "B38M"],
    "China Southern": ["A320", "A20N", "A321", "A21N", "A333", "A359", "B738", "B38M", "B77W", "B77F", "B789"],

    # ---- freight
    "Atlas Air": ["B744", "B748", "B77F", "B763", "B76F"],
    "Cargolux": ["B744", "B748", "B77F"],
    "ASL Airlines": ["B738", "B752", "B76F", "A306", "A21F", "A333"],
    "Cargojet": ["B752", "B763", "B76F", "B77F"],
    "Kalitta Air": ["B744", "B748", "B76F", "B77F"],
    "Western Global Airlines": ["B744", "B77F", "MD11"],
    "AirBridgeCargo": ["B744", "B748", "B77F"],
    "Bridges Air Cargo": ["E19F", "E95F"],
    "USA Jet Airlines": ["B722", "B738"],
    "IFL Group": ["B722", "CR2F"],
    "Aeronaves TSM": ["CR2F", "B738"],
    "Air Class Lineas Aereas": ["B722"],
    "Solar Cargo": ["B722"],
    "Safe Air Company": ["B722"],
    "Serve Air Cargo": ["B722", "B738"],
    "MNG Airlines": ["A306", "A33F"],
    "European Air Transport Leipzig": ["A306", "A33F", "B752", "B763", "B76F"],
    "Air Hong Kong": ["A306", "A33F"],
    "Astral Aviation": ["B752", "B763", "AT76", "E19F"],
    "Qantas Freight": ["B763", "A21F", "A33F"],
}


# Everything else follows from the type lists: the rating-level fleet is simply the
# ratings those aircraft need.
for _op, _types in OPERATOR_TYPES.items():
    OPERATOR_FLEETS[_op] = {AIRCRAFT[t]["family"] for t in _types if t in AIRCRAFT}

# and an ACMI customer cannot tender a type it does not fly
for _c in ACMI_CUSTOMERS:
    _known = OPERATOR_FLEETS.get(_c["name"])
    if _known:
        _kept = [f for f in _c["fams"] if f in _known]
        if _kept:
            _c["fams"] = _kept


# A cargo crew pairing means flying a freighter. Carriers listed with passenger
# variants are corrected to the freighter they actually operate; a division that
# moves freight only in the holds of passenger aircraft (United Cargo, Delta Cargo
# and the like) has no aircraft to crew and offers no pairings.
FREIGHTER_EQUIVALENT = {
    "B752": "B75F", "B763": "B76F", "B737": "B38F", "B738": "B38F", "B739": "B38F", "B38M": "B38F",
    "B772": "B77F", "B77W": "B77F", "B788": None, "B789": None, "A359": None,
    "A332": "A33F", "A333": "A33F", "A339": None, "A319": "A21F", "A320": "A21F", "A321": "A21F",
    "A20N": "A21F", "A21N": "A21F", "E190": "E19F", "E195": "E95F", "CRJ9": "CR2F", "AT76": "AT7F",
    "DH8D": None, "B744": "B744", "B748": "B748",
}

for _c in CARGO_CARRIERS:
    _has_freighter = any(AIRCRAFT.get(t, {}).get("cargo") for t in _c["types"])
    _fixed = []
    for _t in _c["types"]:
        if AIRCRAFT.get(_t, {}).get("cargo"):
            if _t not in _fixed:
                _fixed.append(_t)
            continue
        # only a genuine freight operator has the freighter version; a passenger
        # airline's cargo division carries freight in the hold and crews nothing
        _eq = FREIGHTER_EQUIVALENT.get(_t) if _has_freighter else None
        if _eq and _eq in AIRCRAFT and _eq not in _fixed:
            _fixed.append(_eq)
    _c["types"] = _fixed
    _c["belly_only"] = not _fixed

# Divisions that do operate their own freighters, whatever the passenger fleet says.
REAL_FREIGHTER_DIVISIONS = {
    "Aloha Air Cargo": ["B38F", "B75F"],            # 737-800BCF and 737 classics out of Honolulu
    "Alaska Air Cargo": ["B38F"],                   # dedicated 737-700F fleet
    "WestJet Cargo": ["B38F"],                      # 737-800BCF
    "Avianca Cargo": ["A33F"],                      # A330-200F out of Bogotá and Miami
    "Aerolíneas Argentinas Cargo": ["B38F"],        # 737-800BCF
    "China Postal Airlines": ["B38F", "B75F"],
    "Hong Kong Air Cargo": ["A33F"],
    "JAL Cargo": ["B76F"],                          # 767-300F
    "EgyptAir Cargo": ["A306", "B76F"],
    "Kenya Airways Cargo": ["B77F"],
    "Malaysia Airlines Cargo": ["A33F"],
    "SriLankan Cargo": ["A33F"],
    "Air India Cargo": ["B76F"],
}
for _c in CARGO_CARRIERS:
    _own = REAL_FREIGHTER_DIVISIONS.get(_c["name"])
    if _own:
        _c["types"] = [t for t in _own if t in AIRCRAFT]
        _c["belly_only"] = False

CARGO_CARRIERS_WITH_AIRCRAFT = [c for c in CARGO_CARRIERS if c["types"]]


# Nobody owns every add-on. Operator records what you fly, not which product you
# bought, so any aircraft of roughly the right size and speed will do. These are the
# obvious stand-ins, listed in the interface so the choice is never a guess.
SIM_SUBSTITUTES = {
    # ---- business aircraft
    "H25B": dict(addon="FlightFX Hawker 800XP (MSFS 2024 Marketplace)",
                 also=["Cessna Citation XLS+", "Learjet 45/75", "Citation Latitude", "Hawker 900XP"]),
    "C56X": dict(addon="Flysimware Citation Excel/XLS, or the default Citation CJ4",
                 also=["Hawker 800XP", "Learjet 45/75", "Phenom 300"]),
    "C25C": dict(addon="Default Cessna Citation CJ4 (MSFS)",
                 also=["Phenom 300", "Citation M2", "Learjet 35/45"]),
    "E55P": dict(addon="Default Embraer Phenom 300 (MSFS)",
                 also=["Citation CJ4", "Citation M2", "Learjet 35"]),
    "CL35": dict(addon="Hot Start Challenger 650 (X-Plane) or Citation Longitude (MSFS default)",
                 also=["Citation Longitude", "Praetor 600", "Gulfstream G550", "Hawker 800XP for shorter sectors"]),
    "E545": dict(addon="Citation Longitude (MSFS default) as the nearest super-midsize",
                 also=["Challenger 350", "Citation X", "Gulfstream G550"]),
    "GLF6": dict(addon="Default Gulfstream G550 or the FlightFX Citation X for MSFS; Hot Start Challenger for X-Plane",
                 also=["Global 7500", "Falcon 8X", "Bombardier Global Express"]),
    "GL7T": dict(addon="Default Gulfstream G550 stands in well",
                 also=["G650ER", "Falcon 8X", "Boeing BBJ"]),
    "FA8X": dict(addon="Default Gulfstream G550, or any long-range heavy jet",
                 also=["G650ER", "Global 7500", "Falcon 900"]),
    "PC12": dict(addon="Carenado or SimWorks Studios PC-12 (MSFS), Hot Start TBM or default TBM 930",
                 also=["TBM 930/960", "King Air 350i", "Kodiak 100"]),
    "BE20": dict(addon="Black Square Starship / Analog King Air, or the default King Air 350i",
                 also=["PC-12", "TBM 960", "Beechcraft Baron for short hops"]),

    # ---- airliners and freighters people often lack
    "MD11": dict(addon="Rotate MD-11 (X-Plane)", also=["Boeing 767-300F", "Airbus A300-600F", "any trijet or widebody freighter"]),
    "B722": dict(addon="Captain Sim or FlyJSim 727 (X-Plane)", also=["737-200", "737-800BCF", "any narrowbody freighter"]),
    "A306": dict(addon="iniBuilds A300-600F (MSFS)", also=["767-300F", "A330-200F", "any widebody freighter"]),
    "B75F": dict(addon="Just Flight / FlyByWire 757 or the PMDG 757 when available",
                 also=["767-300F", "737-800BCF", "any narrowbody freighter"]),
    "B38F": dict(addon="PMDG 737-800BDSF (MSFS)", also=["737-800", "757-200PF", "any narrowbody freighter"]),
    "B76F": dict(addon="Kuro or Captain Sim 767 (MSFS), FlightFactor 767 (X-Plane)",
                 also=["A300-600F", "757-200PF", "777F"]),
    "B77F": dict(addon="PMDG 777F (MSFS), FlightFactor 777 (X-Plane)", also=["747-400F", "767-300F", "MD-11F"]),
    "CR2F": dict(addon="Aerosoft CRJ550/700 (MSFS)", also=["ERJ-145", "Dash 8", "any regional jet"]),
    "E19F": dict(addon="E-Jets by X-Crafts (X-Plane) or the Embraer E195 (MSFS)",
                 also=["E195", "CRJ900", "any regional jet"]),
    "E95F": dict(addon="E-Jets by X-Crafts (X-Plane) or the Embraer E195 (MSFS)",
                 also=["E190", "CRJ900", "any regional jet"]),
    "A21F": dict(addon="Fenix or default A321neo", also=["A321", "737-800BCF", "757-200PF"]),
    "A33F": dict(addon="iniBuilds A330 (MSFS), JARDesign or ToLiss A330 (X-Plane)",
                 also=["A330-300", "767-300F", "777F"]),
    "DC3": dict(addon="Aeroplane Heaven or PMDG DC-3 (MSFS); Leading Edge DC-3 (X-Plane)",
                also=["Beech 18", "C-47 Skytrain", "any classic piston twin"]),
    "C208": dict(addon="SimWorks Studios or Carenado Caravan (MSFS), Thranda Caravan (X-Plane)",
                 also=["Kodiak 100", "PC-12", "Twin Otter"]),
    "DHC6": dict(addon="Aerosoft Twin Otter (MSFS), Thranda Twin Otter (X-Plane)",
                 also=["Caravan", "Kodiak 100", "Beech 18"]),
    "SF34": dict(addon="No current Saab 340 — fly a Dash 8 or ATR instead",
                 also=["Dash 8-400", "ATR 42/72", "Beechcraft 1900"]),
    "AT43": dict(addon="Default ATR 72-600 (MSFS) flown light, or Carenado ATR (X-Plane)",
                 also=["ATR 72-600", "Dash 8-400", "Saab 340"]),
    "H25B": dict(addon="FlightFX Hawker 800XP (MSFS 2024 Marketplace)",
                 also=["Citation XLS+", "Learjet 45/75", "Citation Latitude"]),
    "AT7F": dict(addon="Hans Hartmann or Carenado ATR 72 (X-Plane), default ATR 72-600 (MSFS)",
                 also=["ATR 72-600", "Dash 8-400", "any freight turboprop"]),
}


def substitutes(type_code):
    """What to fly in the simulator for a given aircraft."""
    entry = SIM_SUBSTITUTES.get(type_code)
    if entry:
        return entry
    ac = AIRCRAFT.get(type_code) or {}
    cat = ac.get("cat", "")
    generic = {
        "Turboprop": ["ATR 72", "Dash 8-400", "King Air 350"],
        "Regional": ["CRJ900", "E190", "E195"],
        "Narrowbody": ["737-800", "A320neo", "757-200"],
        "Widebody": ["767-300", "A330-300", "777-300ER"],
        "Light jet": ["Citation CJ4", "Phenom 300"],
        "Midsize jet": ["Citation XLS+", "Hawker 800XP", "Learjet 45"],
        "Super-midsize jet": ["Citation Longitude", "Challenger 350"],
        "Heavy jet": ["Gulfstream G550", "Global 7500"],
    }.get(cat, [])
    return dict(addon=None, also=generic)


# Money is held in US dollars, the currency business aviation actually trades in —
# lease rates, block-hour rates and aircraft values are all quoted in dollars. The
# display currency is a presentation choice, converted at a fixed rate so a company's
# books stay consistent.
CURRENCIES = {
    "USD": dict(name="US dollar", symbol="$", rate=1.00, locale="en-US"),
    "GBP": dict(name="Pound sterling", symbol="£", rate=0.79, locale="en-GB"),
    "EUR": dict(name="Euro", symbol="€", rate=0.92, locale="de-DE"),
    "CAD": dict(name="Canadian dollar", symbol="C$", rate=1.37, locale="en-CA"),
    "AUD": dict(name="Australian dollar", symbol="A$", rate=1.52, locale="en-AU"),
    "CHF": dict(name="Swiss franc", symbol="CHF ", rate=0.88, locale="de-CH"),
    "JPY": dict(name="Japanese yen", symbol="¥", rate=152.0, locale="ja-JP"),
    "BRL": dict(name="Brazilian real", symbol="R$", rate=5.45, locale="pt-BR"),
    "ZAR": dict(name="South African rand", symbol="R", rate=18.2, locale="en-ZA"),
    "INR": dict(name="Indian rupee", symbol="₹", rate=83.5, locale="en-IN"),
    "AED": dict(name="UAE dirham", symbol="AED ", rate=3.67, locale="en-AE"),
    "SGD": dict(name="Singapore dollar", symbol="S$", rate=1.35, locale="en-SG"),
    "NZD": dict(name="New Zealand dollar", symbol="NZ$", rate=1.66, locale="en-NZ"),
    "SEK": dict(name="Swedish krona", symbol="kr ", rate=10.6, locale="sv-SE"),
    "NOK": dict(name="Norwegian krone", symbol="kr ", rate=10.9, locale="nb-NO"),
    "PLN": dict(name="Polish złoty", symbol="zł ", rate=3.95, locale="pl-PL"),
}

# A sensible default for a company's home country, from its base airport.
CURRENCY_BY_COUNTRY = {
    "GB": "GBP", "IE": "EUR", "DE": "EUR", "FR": "EUR", "ES": "EUR", "IT": "EUR", "NL": "EUR",
    "BE": "EUR", "AT": "EUR", "PT": "EUR", "FI": "EUR", "GR": "EUR", "MT": "EUR", "LU": "EUR",
    "HR": "EUR", "SK": "EUR", "SI": "EUR", "EE": "EUR", "LV": "EUR", "LT": "EUR", "CY": "EUR",
    "CA": "CAD", "AU": "AUD", "NZ": "NZD", "CH": "CHF", "JP": "JPY", "BR": "BRL", "ZA": "ZAR",
    "IN": "INR", "AE": "AED", "SG": "SGD", "SE": "SEK", "NO": "NOK", "PL": "PLN",
}


# Names are drawn as a whole person, not a first name crossed with an unrelated
# surname: pairing "Chen" with "Martinez" or "Giulia" with "Petrov" reads as a glitch.
# Each pool holds given names and surnames that belong together, and a crew is drawn
# mostly from where the company is based, with the mix of nationalities any real
# operator has on its roster.
NAME_POOLS = {
    "british": dict(
        first=["James", "Oliver", "Harry", "Thomas", "Jack", "George", "Charlie", "William", "Daniel", "Andrew",
               "Emily", "Charlotte", "Sophie", "Hannah", "Olivia", "Rachel", "Laura", "Katie", "Rebecca", "Alice",
               "Callum", "Rhys", "Gareth", "Fraser", "Duncan", "Eleanor", "Imogen", "Freya"],
        last=["Walker", "Hughes", "Bennett", "Clarke", "Harrison", "Thompson", "Whitfield", "Ashworth", "Pearson",
              "Hollis", "Maddox", "Braithwaite", "Redfern", "Chadwick", "Morgan", "Llewellyn", "Fairbairn",
              "Kinsella", "Sinclair", "Faulkner", "Whittaker", "Ellery", "Prentice", "Rowntree"]),
    "irish": dict(
        first=["Sean", "Ciaran", "Declan", "Eoin", "Padraig", "Fergal", "Niall", "Ruairi", "Cormac",
               "Aoife", "Niamh", "Siobhan", "Orla", "Sinead", "Roisin", "Maeve", "Clodagh"],
        last=["Murphy", "O'Brien", "Byrne", "Kelly", "Brennan", "Gallagher", "Doherty", "Fitzgerald", "Keane",
              "Donnelly", "MacCarthy", "Hegarty", "Concannon", "Rafferty", "Sheridan"]),
    "german": dict(
        first=["Andreas", "Stefan", "Matthias", "Lukas", "Sebastian", "Tobias", "Florian", "Jens", "Dirk", "Kai",
               "Katrin", "Ingrid", "Birgit", "Franziska", "Annika", "Heike", "Sabine", "Lena", "Maike"],
        last=["Bauer", "Schmidt", "Fischer", "Hoffmann", "Weber", "Keller", "Wagner", "Zimmermann", "Brandt",
              "Neumann", "Krüger", "Vogel", "Schreiber", "Reinhardt", "Lindemann", "Hartmann", "Stellwag"]),
    "dutch": dict(
        first=["Bram", "Sander", "Joost", "Wouter", "Thijs", "Maarten", "Ruben", "Femke", "Sanne", "Marieke",
               "Anouk", "Jeroen", "Pieter"],
        last=["Jansen", "de Vries", "van Dijk", "Bakker", "Visser", "Hendriks", "van Leeuwen", "Mulder",
              "de Boer", "Wijnands", "Bosman", "Kuiper"]),
    "nordic": dict(
        first=["Lars", "Henrik", "Erik", "Magnus", "Jonas", "Anders", "Nils", "Bjørn", "Mikkel", "Oskar",
               "Astrid", "Ingrid", "Sigrid", "Elin", "Freja", "Maja", "Tuva", "Hanne"],
        last=["Nielsen", "Andersson", "Larsen", "Lindqvist", "Hansen", "Berg", "Dahl", "Sørensen", "Kristiansen",
              "Ahlgren", "Nyström", "Haugen", "Lindholm", "Virtanen", "Mäkinen", "Järvinen"]),
    "polish": dict(
        first=["Tomasz", "Paweł", "Krzysztof", "Marcin", "Jakub", "Bartosz", "Grzegorz",
               "Agnieszka", "Magdalena", "Katarzyna", "Zofia", "Aleksandra"],
        last=["Kowalski", "Nowak", "Wiśniewski", "Wójcik", "Kamiński", "Lewandowski", "Zieliński",
              "Szymański", "Woźniak", "Dąbrowski", "Mazurek"]),
    "slavic": dict(
        first=["Ivan", "Dmitri", "Viktor", "Milan", "Luka", "Marek", "Tomáš", "Bojan",
               "Elena", "Katarina", "Milena", "Irina", "Ana"],
        last=["Petrov", "Ivanova", "Novak", "Horvat", "Popescu", "Kovač", "Nowicki", "Jelínek",
              "Marković", "Dimitrov", "Sokolov", "Varga"]),
    "italian": dict(
        first=["Matteo", "Marco", "Alessandro", "Luca", "Davide", "Francesco", "Stefano",
               "Giulia", "Chiara", "Francesca", "Valentina", "Alessia", "Martina"],
        last=["Rossi", "Ricci", "Conti", "Greco", "Marchetti", "Ferrari", "Bianchi", "Esposito",
              "Romano", "Gallo", "Lombardi", "Moretti"]),
    "french": dict(
        first=["Olivier", "Julien", "Thibault", "Mathieu", "Guillaume", "Romain", "Antoine",
               "Camille", "Céline", "Amélie", "Élodie", "Manon", "Chloé"],
        last=["Lefèvre", "Dubois", "Moreau", "Laurent", "Girard", "Bonnet", "Rousseau",
              "Marchand", "Perrin", "Lemaire", "Fontaine", "Charpentier"]),
    "iberian": dict(
        first=["Miguel", "Diego", "Javier", "Alejandro", "Carlos", "Rubén", "Sergio", "João", "Tiago", "Rui",
               "Lucía", "Carmen", "Marta", "Beatriz", "Inês", "Sofia"],
        last=["García", "Fernández", "Martínez", "López", "Sánchez", "Romero", "Navarro", "Iglesias",
              "Costa", "Silva", "Pereira", "Almeida", "Carvalho"]),
    "latin_american": dict(
        first=["Santiago", "Mateo", "Emiliano", "Rodrigo", "Nicolás", "Andrés", "Tomás",
               "Valentina", "Camila", "Isabela", "Daniela", "Mariana"],
        last=["Ramírez", "Gutiérrez", "Herrera", "Vargas", "Castillo", "Mendoza", "Ortega",
              "Salazar", "Cabrera", "Quintero", "Rojas"]),
    "brazilian": dict(
        first=["Lucas", "Gustavo", "Rafael", "Thiago", "Bruno", "Felipe", "Juliana", "Larissa", "Beatriz", "Renata"],
        last=["Oliveira", "Souza", "Lima", "Ribeiro", "Barbosa", "Cardoso", "Moreira", "Nascimento", "Teixeira"]),
    "north_american": dict(
        first=["Michael", "David", "Ryan", "Brandon", "Tyler", "Jason", "Kevin", "Scott", "Chad", "Dustin",
               "Ashley", "Jennifer", "Megan", "Courtney", "Brittany", "Danielle", "Kayla"],
        last=["Miller", "Davis", "Wilson", "Anderson", "Reynolds", "Coleman", "Sutton", "Brooks", "Hayes",
              "Sullivan", "Fletcher", "Barrett", "Whitaker", "Lansing", "Dunbar", "Carrick"]),
    "turkish": dict(
        first=["Mehmet", "Emre", "Kerem", "Burak", "Serkan", "Onur", "Deniz", "Elif", "Zeynep", "Merve"],
        last=["Yılmaz", "Demir", "Kaya", "Çelik", "Şahin", "Arslan", "Doğan", "Aydın", "Koç", "Özdemir"]),
    "arabic": dict(
        first=["Yusuf", "Omar", "Khalid", "Tariq", "Hassan", "Faisal", "Rashid", "Nadia", "Leila", "Amira", "Huda"],
        last=["Al-Rashid", "Al-Mansouri", "Haddad", "Nassar", "Khoury", "Zahran", "Al-Sayed",
              "Farouk", "Bakr", "Hamdan"]),
    "south_asian": dict(
        first=["Raj", "Arjun", "Vikram", "Rohan", "Karthik", "Sanjay", "Imran", "Priya", "Anjali", "Meera",
               "Divya", "Fatima"],
        last=["Sharma", "Patel", "Nair", "Reddy", "Iyer", "Chowdhury", "Malhotra", "Kapoor",
              "Rahman", "Fernandes", "Sethi", "Bhatia"]),
    "chinese": dict(
        first=["Wei", "Jun", "Hao", "Ming", "Feng", "Yang", "Lei", "Mei Lin", "Xiuying", "Yan", "Jing", "Hui"],
        last=["Chen", "Li", "Zhang", "Wang", "Liu", "Huang", "Zhao", "Wu", "Zhou", "Xu", "Lin", "Ma"]),
    "japanese": dict(
        first=["Takeshi", "Hiroshi", "Kenji", "Daisuke", "Sho", "Ryo", "Yuki", "Akira", "Naoko", "Aya", "Rina"],
        last=["Nakamura", "Tanaka", "Watanabe", "Yamamoto", "Sato", "Suzuki", "Kobayashi", "Ito",
              "Matsumoto", "Fujita", "Ogawa"]),
    "korean": dict(
        first=["Min-jun", "Ji-hoon", "Seung-woo", "Dae-hyun", "Joon-ho", "Ji-woo", "Seo-yeon", "Hye-jin", "Soo-min"],
        last=["Kim", "Park", "Choi", "Lee", "Jung", "Kang", "Cho", "Yoon", "Shin", "Han"]),
    "vietnamese": dict(
        first=["Van Minh", "Quang", "Duc", "Hoang", "Thanh", "Thi Lan", "Ngoc", "Mai"],
        last=["Nguyen", "Tran", "Pham", "Le", "Hoang", "Vu", "Dang", "Bui"]),
    "thai": dict(
        first=["Somchai", "Anan", "Chaiwat", "Nattapong", "Siriporn", "Ploy", "Nutthida"],
        last=["Suwan", "Chaiyaphum", "Rattanakosin", "Wongsawat", "Srisai", "Thongchai", "Pattanasak"]),
    "indonesian": dict(
        first=["Budi", "Agus", "Wayan", "Rizky", "Dimas", "Siti", "Nur", "Dewi"],
        last=["Wijaya", "Santoso", "Hidayat", "Kusuma", "Pratama", "Setiawan", "Halim"]),
    "filipino": dict(
        first=["Jose Antonio", "Ramon", "Emilio", "Paolo", "Maria Teresa", "Angelica", "Liza"],
        last=["Dela Cruz", "Reyes", "Bautista", "Santos", "Mendoza", "Aquino", "Villanueva"]),
    "west_african": dict(
        first=["Kwame", "Chidi", "Emeka", "Kofi", "Adewale", "Tunde", "Amara", "Ngozi", "Adaeze", "Aisha"],
        last=["Okafor", "Adeyemi", "Mensah", "Achebe", "Okonkwo", "Diallo", "Traoré", "Boateng",
              "Adebayo", "Nwosu"]),
    "east_african": dict(
        first=["Abebe", "Dawit", "Tesfaye", "Juma", "Otieno", "Amani", "Zuri", "Makeda"],
        last=["Mwangi", "Bekele", "Tesfaye", "Kimani", "Wanjiru", "Hailu", "Njoroge", "Abdi"]),
    "southern_african": dict(
        first=["Sipho", "Thabo", "Tendai", "Bongani", "Lesedi", "Zanele", "Nomvula", "Ayanda"],
        last=["Nkosi", "Dlamini", "Mabaso", "Moyo", "Ndlovu", "Botha", "van der Merwe", "Khumalo"]),
    "oceania": dict(
        first=["Jack", "Cooper", "Lachlan", "Angus", "Hamish", "Tane", "Ruby", "Matilda", "Isla", "Tegan"],
        last=["Whitcombe", "Callaghan", "Hargreaves", "McKenzie", "Fitzpatrick", "Ngata", "Waititi",
              "Kirkland", "Beauchamp", "Thornton"]),
}

# Where a company's crews come from: mostly local, with the international spread any
# real operator has.
HOME_POOL = {
    "GB": "british", "IE": "irish", "DE": "german", "AT": "german", "CH": "german", "NL": "dutch",
    "BE": "dutch", "DK": "nordic", "SE": "nordic", "NO": "nordic", "FI": "nordic", "IS": "nordic",
    "PL": "polish", "CZ": "slavic", "SK": "slavic", "HU": "slavic", "RO": "slavic", "BG": "slavic",
    "HR": "slavic", "RS": "slavic", "RU": "slavic", "UA": "slavic", "IT": "italian", "FR": "french",
    "ES": "iberian", "PT": "iberian", "MX": "latin_american", "CO": "latin_american", "AR": "latin_american",
    "CL": "latin_american", "PE": "latin_american", "PA": "latin_american", "UY": "latin_american",
    "VE": "latin_american", "BR": "brazilian", "US": "north_american", "CA": "north_american",
    "TR": "turkish", "AE": "arabic", "QA": "arabic", "SA": "arabic", "OM": "arabic", "KW": "arabic",
    "BH": "arabic", "JO": "arabic", "EG": "arabic", "MA": "arabic", "IN": "south_asian",
    "PK": "south_asian", "BD": "south_asian", "LK": "south_asian", "CN": "chinese", "HK": "chinese",
    "JP": "japanese", "KR": "korean", "TW": "chinese", "SG": "chinese",
    "MY": "indonesian", "TH": "thai", "VN": "vietnamese", "PH": "filipino",
    "ID": "indonesian", "ZA": "southern_african", "KE": "east_african", "NG": "west_african",
    "ET": "east_african", "GH": "west_african", "CD": "west_african",
    "AU": "oceania", "NZ": "oceania", "FJ": "oceania",
}

# The rest of a roster: aviation is an international business, so a British operator
# still employs Poles, Spaniards and South Africans.
NEIGHBOURS = {
    "british": ["irish", "polish", "north_american", "south_asian", "nordic", "west_african"],
    "irish": ["british", "polish", "iberian", "slavic"],
    "german": ["polish", "dutch", "slavic", "turkish", "italian", "nordic"],
    "dutch": ["german", "british", "polish", "indonesian"],
    "nordic": ["german", "polish", "british", "slavic"],
    "polish": ["slavic", "german", "british", "nordic"],
    "slavic": ["polish", "german", "italian", "turkish"],
    "italian": ["slavic", "french", "iberian", "east_african"],
    "french": ["west_african", "arabic", "iberian", "italian", "dutch"],
    "iberian": ["latin_american", "brazilian", "french", "italian", "west_african"],
    "latin_american": ["iberian", "brazilian", "north_american"],
    "brazilian": ["iberian", "latin_american", "italian"],
    "north_american": ["latin_american", "chinese", "south_asian", "british", "filipino"],
    "turkish": ["arabic", "slavic", "german"],
    "arabic": ["south_asian", "east_african", "turkish", "british", "filipino"],
    "south_asian": ["arabic", "british", "filipino", "chinese"],
    "chinese": ["japanese", "korean", "filipino", "north_american"],
    "japanese": ["chinese", "korean", "filipino"],
    "korean": ["chinese", "japanese", "filipino"],
    "vietnamese": ["thai", "chinese", "filipino"],
    "thai": ["vietnamese", "indonesian", "chinese"],
    "indonesian": ["filipino", "thai", "dutch"],
    "filipino": ["indonesian", "chinese", "north_american", "arabic"],
    "west_african": ["east_african", "french", "british", "arabic"],
    "east_african": ["west_african", "arabic", "south_asian", "british"],
    "southern_african": ["east_african", "british", "dutch", "west_african"],
    "oceania": ["british", "filipino", "chinese", "south_asian"],
}


# Given names that take a feminine surname form in Polish and the Slavic languages.
FEMALE_GIVEN = {
    "Agnieszka", "Magdalena", "Katarzyna", "Zofia", "Aleksandra", "Elena", "Katarina", "Milena", "Irina", "Ana",
}

# Polish and Slavic surnames agree with the bearer: Kowalski for a man, Kowalska for a
# woman; Petrov becomes Petrova.
def feminise(surname):
    for male, female in (("ski", "ska"), ("cki", "cka"), ("dzki", "dzka"), ("ński", "ńska"),
                         ("ov", "ova"), ("ev", "eva"), ("in", "ina")):
        if surname.endswith(male):
            return surname[: -len(male)] + female
    return surname


def crew_name(rng, country=None, home_share=0.55):
    """A plausible whole person: given name and surname from the same tradition,
    drawn mostly from the company's own country."""
    home = HOME_POOL.get((country or "").upper())
    pool_key = None
    if home and rng.random() < home_share:
        pool_key = home
    elif home and rng.random() < 0.75:
        pool_key = rng.choice(NEIGHBOURS.get(home, []) or [home])
    if not pool_key:
        pool_key = rng.choice(list(NAME_POOLS))
    pool = NAME_POOLS[pool_key]
    given, surname = rng.choice(pool["first"]), rng.choice(pool["last"])
    for _ in range(6):                       # no "Mei Lin Lin" or "Tran Minh Tran"
        if surname not in given.split() and given.split()[0] != surname:
            break
        surname = rng.choice(pool["last"])
    if pool_key in ("polish", "slavic") and given in FEMALE_GIVEN:
        surname = feminise(surname)
    return f"{given} {surname}", pool_key


# ICAO aerodrome reference code: the letter is the wingspan band an aircraft falls in,
# and it is how charter brokers and airports describe what will fit. Code C is the
# 24-36 m band — the 737s, A320s, E-Jets and turboprops that fly most group charter.
WINGSPAN_M = {
    "PC12": 16.3, "BE20": 17.7, "C208": 15.9, "DHC6": 19.8, "DC3": 29.0,
    "E55P": 16.2, "C25C": 15.5, "C56X": 17.2, "H25B": 15.7, "E545": 21.5, "CL35": 21.0,
    "GLF6": 30.4, "GL7T": 31.7, "FA8X": 26.3,
    "CR2F": 21.2, "CRJ9": 24.9, "SF34": 21.4, "AT43": 24.6, "AT76": 27.1, "AT7F": 27.1, "DH8D": 28.4,
    "E190": 28.7, "E195": 28.7, "E19F": 28.7, "E95F": 28.7,
    "B722": 32.9, "B737": 34.3, "B738": 35.8, "B739": 35.8, "B38M": 35.9, "B38F": 35.8,
    "A319": 35.8, "A320": 35.8, "A321": 35.8, "A20N": 35.8, "A21N": 35.8, "A21F": 35.8,
    "B752": 38.1, "B75F": 38.1, "B763": 47.6, "B76F": 47.6, "A306": 44.8,
    "A332": 60.3, "A333": 60.3, "A339": 64.0, "A33F": 60.3, "A359": 64.8,
    "B772": 60.9, "B77W": 64.8, "B77F": 64.8, "B788": 60.1, "B789": 60.1,
    "B744": 64.4, "B748": 68.4, "MD11": 51.7,
}


def aerodrome_code(type_code):
    """A to F by wingspan, as ICAO Annex 14 defines it."""
    span = WINGSPAN_M.get(type_code)
    if span is None:
        return "C"
    for letter, limit in (("A", 15), ("B", 24), ("C", 36), ("D", 52), ("E", 65), ("F", 80)):
        if span < limit:
            return letter
    return "F"


CODE_DESCRIPTION = {
    "A": "up to 15 m wingspan", "B": "15 to 24 m", "C": "24 to 36 m — most narrowbodies and turboprops",
    "D": "36 to 52 m", "E": "52 to 65 m — most widebodies", "F": "65 to 80 m",
}


# Group charter: a whole aircraft hired for one party. This is what most of the world's
# charter flying actually is — holiday series, teams, troops, pilgrims and work crews —
# and it is flown on airliners, not business jets.
GROUP_CLIENTS = [
    dict(kind="Tour operator", story="a holiday charter, full aircraft, fixed dates",
         min_pax=90, price=0.92, cares=dict(punctual=0.55, comfort=0.20, cabin=0.25), tolerance=1.2,
         needs=["cabin crew", "hold baggage for every passenger"]),
    dict(kind="Cruise line", story="passengers joining a ship, and the ship will not wait",
         min_pax=120, price=1.05, cares=dict(punctual=0.70, comfort=0.15, cabin=0.15), tolerance=0.6,
         needs=["cabin crew", "hold baggage for every passenger"]),
    dict(kind="Football club", story="the first team, staff and kit to an away fixture",
         min_pax=45, price=1.12, cares=dict(punctual=0.55, comfort=0.30, cabin=0.15), tolerance=0.8,
         needs=["cabin crew", "kit in the hold", "a late-night return after the match"]),
    dict(kind="Government charter", story="an official delegation and press corps",
         min_pax=60, price=1.30, cares=dict(punctual=0.65, comfort=0.20, cabin=0.15), tolerance=0.6,
         needs=["cabin crew", "security screening", "protocol arrangements"]),
    dict(kind="Troop rotation", story="a military rotation with duffle and equipment",
         min_pax=100, price=1.15, cares=dict(punctual=0.60, comfort=0.15, cabin=0.25), tolerance=0.9,
         needs=["cabin crew", "heavy hold load", "clearances for the destination"]),
    dict(kind="Pilgrimage charter", story="a Hajj or Umrah group travelling together",
         min_pax=150, price=1.00, cares=dict(punctual=0.50, comfort=0.25, cabin=0.25), tolerance=1.1,
         needs=["cabin crew", "extra hold baggage", "catering to requirement"]),
    dict(kind="Mining rotation", story="a fly-in fly-out shift change to a remote strip",
         min_pax=70, price=1.18, cares=dict(punctual=0.65, comfort=0.15, cabin=0.20), tolerance=0.7,
         needs=["cabin crew", "a short and rough runway at one end"]),
    dict(kind="Music tour", story="the band, the crew and the production to the next show",
         min_pax=50, price=1.10, cares=dict(punctual=0.50, comfort=0.30, cabin=0.20), tolerance=0.9,
         needs=["cabin crew", "flight cases in the hold", "an overnight turn"]),
    dict(kind="Airline disruption cover", story="stranded passengers from a cancelled service",
         min_pax=110, price=1.25, cares=dict(punctual=0.80, comfort=0.10, cabin=0.10), tolerance=0.4,
         needs=["cabin crew", "wheels up within a day"]),
    dict(kind="Incentive travel", story="a company taking its staff somewhere warm",
         min_pax=80, price=1.08, cares=dict(punctual=0.45, comfort=0.35, cabin=0.20), tolerance=1.0,
         needs=["cabin crew", "catering to requirement"]),
]

# What a whole aircraft costs to hire by the block hour, all in: crew, fuel, handling
# and the operator's margin. These are the rates group charter actually places at.
GROUP_HOURLY = {
    "Turboprop": 3100, "Regional": 4800, "Narrowbody": 8600, "Widebody": 19500,
}


# An air operator certificate names the areas the holder may operate in. A new AOC
# covers the region it was issued in; anything further is an amendment to the
# operations specifications, which the authority charges for and takes time over.
REGIONS = {
    "EU": dict(name="Europe", blurb="EASA states, the UK, the Balkans and Türkiye"),
    "NA": dict(name="North America", blurb="the United States, Canada, Mexico and the Caribbean"),
    "SA": dict(name="South America", blurb="the continent and its island territories"),
    "AF": dict(name="Africa", blurb="the continent, Madagascar and the Atlantic islands"),
    "ME": dict(name="Middle East", blurb="the Gulf, the Levant and Iran"),
    "AS": dict(name="Asia", blurb="South, Central, East and South-East Asia"),
    "OC": dict(name="Oceania", blurb="Australia, New Zealand and the Pacific"),
}

_REGION_BY_COUNTRY = {
    "EU": ["GB", "IE", "FR", "DE", "ES", "PT", "IT", "NL", "BE", "LU", "CH", "AT", "DK", "SE", "NO", "FI",
           "IS", "PL", "CZ", "SK", "HU", "RO", "BG", "GR", "HR", "SI", "RS", "BA", "ME", "MK", "AL", "EE",
           "LV", "LT", "MT", "CY", "UA", "BY", "MD", "TR", "RU", "GI", "FO", "GL", "AD", "MC", "SM", "LI", "XK"],
    "NA": ["US", "CA", "MX", "GT", "BZ", "SV", "HN", "NI", "CR", "PA", "CU", "JM", "HT", "DO", "BS", "BB",
           "TT", "PR", "VI", "AG", "LC", "GD", "KN", "DM", "VC", "AW", "CW", "SX", "BM", "KY", "TC", "VG", "AI", "MS"],
    "SA": ["BR", "AR", "CL", "PE", "CO", "VE", "EC", "BO", "PY", "UY", "GY", "SR", "GF", "FK"],
    "AF": ["ZA", "KE", "NG", "ET", "GH", "EG", "MA", "DZ", "TN", "LY", "SD", "SS", "TZ", "UG", "RW", "BI",
           "CD", "CG", "GA", "CM", "CI", "SN", "ML", "BF", "NE", "TD", "MR", "GN", "SL", "LR", "TG", "BJ",
           "AO", "ZM", "ZW", "MZ", "MW", "BW", "NA", "LS", "SZ", "MG", "MU", "SC", "RE", "CV", "DJ", "SO", "ER", "GM", "GW", "ST", "GQ"],
    "ME": ["AE", "SA", "QA", "KW", "BH", "OM", "YE", "JO", "LB", "SY", "IQ", "IR", "IL", "PS"],
    "AS": ["CN", "HK", "MO", "TW", "JP", "KR", "KP", "MN", "IN", "PK", "BD", "LK", "NP", "BT", "MV", "AF",
           "KZ", "UZ", "TM", "TJ", "KG", "TH", "VN", "KH", "LA", "MM", "MY", "SG", "ID", "PH", "BN", "TL", "GE", "AM", "AZ"],
    "OC": ["AU", "NZ", "FJ", "PG", "NC", "PF", "WS", "TO", "VU", "SB", "CK", "GU", "MP", "MH", "FM", "PW",
           "NR", "TV", "KI", "AS", "NF", "NU", "WF", "UM"],
}
# dependencies and the odd corners, so no airport is outside every area
_REGION_BY_COUNTRY["EU"] += ["GG", "JE", "IM"]
_REGION_BY_COUNTRY["NA"] += ["BL", "BQ", "GP", "MQ", "MF", "PM"]
_REGION_BY_COUNTRY["AF"] += ["CF", "KM", "YT", "SH", "EH", "IO"]
_REGION_BY_COUNTRY["AS"] += ["CC", "CX"]
_REGION_BY_COUNTRY["SA"] += ["AQ"]
REGION_OF_COUNTRY = {c: r for r, cs in _REGION_BY_COUNTRY.items() for c in cs}


def region_of(icao):
    """Which AOC area an airport sits in."""
    a = AIRPORTS.get(icao)
    if not a:
        return None
    return REGION_OF_COUNTRY.get(a["country"])


# What the authority charges to add an area, and how long it takes them. Adding the
# region next door is routine; the other side of the world means proving your
# procedures, your crews' licences and your maintenance arrangements all over again.
AREA_APPLICATION = dict(near=dict(fee=38000, days=21, rep=0),
                        far=dict(fee=145000, days=45, rep=55))

# Adding a type to an operations specification is not a form: it is a training
# programme, a maintenance programme, manuals, a proving flight and an inspector
# who wants to watch. The bigger the aeroplane, the longer all of that takes.
TYPE_APPLICATION = {
    "Turboprop":          dict(fee=36000,  days=28, rep=0),
    "Light jet":          dict(fee=42000,  days=28, rep=0),
    "Midsize jet":        dict(fee=48000,  days=32, rep=0),
    "Super-midsize jet":  dict(fee=56000,  days=35, rep=10),
    "Heavy jet":          dict(fee=72000,  days=40, rep=15),
    "Regional":           dict(fee=62000,  days=40, rep=10),
    "Narrowbody":         dict(fee=98000,  days=52, rep=25),
    "Widebody":           dict(fee=185000, days=70, rep=45),
}
# A second type from a manufacturer you already run is cheaper and quicker: the
# training organisation, the maintenance programme and the inspector are the same.
SAME_MFR_DISCOUNT = 0.72

ADJACENT_REGIONS = {
    "EU": ["AF", "ME", "NA"], "NA": ["SA", "EU"], "SA": ["NA", "AF"],
    "AF": ["EU", "ME"], "ME": ["EU", "AF", "AS"], "AS": ["ME", "OC"], "OC": ["AS"],
}
