# PyInstaller spec for Operator.
#   onedir (default): pyinstaller operator.spec          -> dist/Operator/Operator.exe
#   onefile:          pyinstaller operator.spec -- --onefile
# The installer script (installer/operator.iss) expects the onedir build.
import os, sys
here = os.path.abspath('.')
onefile = '--onefile' in sys.argv

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


def _have(mod):
    import importlib.util
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


hidden = ['flask', 'jinja2', 'werkzeug', 'click', 'itsdangerous', 'blinker', 'desktop']
for opt in ('SimConnect', 'webview', 'webview.platforms.edgechromium', 'webview.platforms.winforms',
            'clr_loader', 'pythonnet'):
    if _have(opt.split('.')[0]):
        hidden.append(opt)

datas = [
    (os.path.join(here, 'static'), 'static'),
    (os.path.join(here, 'brand'), 'brand'),
    (os.path.join(here, 'airports.json'), '.'),
    (os.path.join(here, 'runways.json'), '.'),
    (os.path.join(here, 'elevations.json'), '.'),
    (os.path.join(here, 'placeholder_logos.json'), '.'),
    (os.path.join(here, 'logo_tone.json'), '.'),
    (os.path.join(here, 'README.md'), '.'),
]

binaries = []
# The SimConnect package ships SimConnect.dll beside its Python files; PyInstaller
# does not pick that up on its own, and without it MSFS/P3D cannot be reached.
if _have('SimConnect'):
    binaries += collect_dynamic_libs('SimConnect')
    datas += [(src, dst) for src, dst in collect_data_files('SimConnect', include_py_files=False)
              if src.lower().endswith(('.dll', '.manifest', '.json'))]

a = Analysis(['server.py'], pathex=[here], binaries=binaries, datas=datas,
             hiddenimports=hidden,
             hookspath=[], runtime_hooks=[],
             excludes=['tkinter', 'matplotlib', 'numpy', 'PIL', 'pandas', 'scipy', 'pytest', 'cairosvg', 'cairocffi'],
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data)

mac = sys.platform == 'darwin'
icon = os.path.join(here, 'brand', 'operator.icns' if mac else 'favicon.ico')
version = os.path.join(here, 'version_info.txt')

if mac:
    # A macOS application bundle: no console window, opens like any other Mac app.
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Operator',
              debug=False, strip=False, upx=False, console=False, icon=icon)
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, name='Operator')
    app = BUNDLE(coll, name='Operator.app', icon=icon, bundle_identifier='com.operator.ferrycargoacmi',
                 info_plist={
                     'CFBundleName': 'Operator',
                     'CFBundleDisplayName': 'Operator — Ferry, Cargo & ACMI',
                     'CFBundleShortVersionString': '1.0.0',
                     'CFBundleVersion': '1.0.0',
                     'NSHighResolutionCapable': True,
                     'LSMinimumSystemVersion': '11.0',
                     'NSHumanReadableCopyright': 'Third-party names and marks belong to their owners.',
                     'LSApplicationCategoryType': 'public.app-category.simulation',
                 })
elif onefile:
    exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [], name='Operator',
              debug=False, strip=False, upx=False, runtime_tmpdir=None, console=True,
              icon=icon, version=version)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Operator',
              debug=False, strip=False, upx=False, console=True, icon=icon, version=version)
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, name='Operator')
