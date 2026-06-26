# gui/build.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gui/main.py'],
    pathex=[],
    binaries=[],
    datas=[('gui/styles', 'styles'), ('gui/resources', 'resources')],
    hiddenimports=['src', 'src.config', 'src.logger', 'src.run', 'src.fetcher', 'src.parser', 'src.speed_tester', 'src.ffmpeg_validator', 'src.generator', 'src.merger', 'src.blacklist_filter', 'src.demo_filter', 'src.database', 'src.alias_matcher', 'src.classifier', 'src.logo_matcher', 'src.generator_enhanced', 'src.special_categories', 'src.stable.manager', 'src.source_pool.discoverer', 'src.candidate.observer', 'src.quality.monitor', 'src.overseas_filter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyd = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyd,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='IPTV_Collector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台窗口以便查看日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='gui/resources/icon.ico'
)
