# AVD.spec — PyInstaller onedir 빌드 (D011, D038)
# 빌드: venv\Scripts\pyinstaller AVD.spec --noconfirm
# gaindb(LGPL)·yt_dlp 는 PYZ 에 묶지 않고 _internal\ 아래 평문 .py 로 둔다:
# gaindb 는 사용자가 교체할 수 있어야 하고, yt_dlp 는 앱이 wheel 로 교체한다.

a = Analysis(
    ["main.py"],
    datas=[
        ("gaindb/LICENSE", "gaindb"),
        ("gaindb/NOTICE", "gaindb"),
        ("gaindb/THIRD_PARTY_LICENSES", "gaindb"),
    ],
    module_collection_mode={"gaindb": "py", "yt_dlp": "py"},
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AVD",
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="AVD")
