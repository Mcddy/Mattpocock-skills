# PyInstaller spec for a forge app (Release tier). Copy into the app's release/ folder and edit the three marked lines.
# Build on Windows with build_exe.bat (PyInstaller makes an EXE only on Windows; it does not cross-compile).
import pathlib
HERE = pathlib.Path(SPECPATH)                      # release/
APP = HERE.parent / 'app'                          # EDIT if the server and page live elsewhere
NAME = 'MyApp'                                     # EDIT: the EXE and folder name, no spaces
PAGES = ['index.html']                             # EDIT: the page and any scripts it loads from the app folder
KIT = APP / 'kit' if (APP / 'kit').is_dir() else HERE.parent.parent / 'visual-kit'   # the visual kit the page links
KIT_FILES = ['kit.css', 'kit2.css', 'kit3.css', 'fonts.css', 'illustrations.js', 'kit-dir.js']

datas = [(str(APP / f), '.') for f in PAGES]
datas += [(str(KIT / f), 'kit') for f in KIT_FILES if (KIT / f).exists()]
datas += [(str(KIT / 'fonts' / '*.woff2'), 'kit/fonts')]

a = Analysis([str(HERE / 'launcher.py')], pathex=[str(APP)], datas=datas, hiddenimports=['server'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=NAME, icon=str(HERE / 'icon.ico'), console=False)
coll = COLLECT(exe, a.binaries, a.datas, name=NAME)
