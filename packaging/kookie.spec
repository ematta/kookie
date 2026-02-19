# -*- mode: python ; coding: utf-8 -*-
import importlib.util
import shutil
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# PyInstaller spec execution does not guarantee the source file path constant.
# SPECPATH points to the directory containing this spec file.
project_root = Path(SPECPATH).resolve().parent
libespeak_rel = "libs/libespeak-ng.dylib"
espeak_data_rel = "libs/espeak-ng-data"
model_rel = "assets/kokoro-v0_19.onnx"
voices_rel = "assets/voices.bin"
app_icon_rel = "kookie.png"
block_cipher = None
DYNAMIC_IMPORT_PACKAGES = ["pymupdf"]
DYNAMIC_IMPORT_ALIASES = ["fitz"]


def optional_data(source_rel: str, destination: str) -> list[tuple[str, str]]:
    path = project_root / source_rel
    if path.exists():
        return [(str(path), destination)]
    print(f"Skipping missing asset during packaging: {path}")
    return []


def optional_package_data(package: str) -> list[tuple[str, str]]:
    try:
        return collect_data_files(package)
    except Exception as exc:
        print(f"Skipping package data collection for {package}: {exc}")
        return []


def optional_package_binaries(package: str) -> list[tuple[str, str]]:
    try:
        return collect_dynamic_libs(package)
    except Exception as exc:
        print(f"Skipping dynamic library collection for {package}: {exc}")
        return []


def optional_system_binary(binary_name: str) -> list[tuple[str, str]]:
    resolved = shutil.which(binary_name)
    if resolved is None:
        print(f"Skipping missing system binary during packaging: {binary_name}")
        return []
    return [(resolved, "bin")]


def module_exists(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception as exc:
        print(f"Skipping module presence check for {module_name}: {exc}")
        return False


def optional_hidden_imports(module_names: list[str]) -> list[str]:
    hidden_imports: list[str] = []
    for module_name in module_names:
        if module_exists(module_name):
            hidden_imports.append(module_name)
        else:
            print(f"Skipping missing hidden import during packaging: {module_name}")
    return hidden_imports


def optional_package_submodules(package: str) -> list[str]:
    if not module_exists(package):
        print(f"Skipping submodule collection for missing package: {package}")
        return []
    try:
        return collect_submodules(package)
    except Exception as exc:
        print(f"Skipping submodule collection for {package}: {exc}")
        return []


def optional_dynamic_imports(packages: list[str], aliases: list[str]) -> list[str]:
    hidden_imports = optional_hidden_imports(aliases)
    for package in packages:
        hidden_imports += optional_hidden_imports([package])
        hidden_imports += optional_package_submodules(package)
    return hidden_imports


dynamic_import_binaries = optional_package_binaries("pymupdf")
for dynamic_package in DYNAMIC_IMPORT_PACKAGES:
    if dynamic_package != "pymupdf":
        dynamic_import_binaries += optional_package_binaries(dynamic_package)

dynamic_hiddenimports = optional_dynamic_imports(
    DYNAMIC_IMPORT_PACKAGES,
    DYNAMIC_IMPORT_ALIASES,
)


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[
        (str(project_root / libespeak_rel), "."),
    ]
    + optional_package_binaries("docling")
    + optional_package_binaries("docling_ibm_models")
    + optional_system_binary("ffmpeg")
    + dynamic_import_binaries,
    datas=(
        [(str(project_root / espeak_data_rel), "espeak-ng-data")]
        + optional_data(model_rel, "assets")
        + optional_data(voices_rel, "assets")
        + optional_data(app_icon_rel, ".")
        + optional_package_data("docling")
        + optional_package_data("docling_ibm_models")
    ),
    hiddenimports=[
        "docling",
        "docling.document_converter",
        "docling.datamodel.base_models",
        "docling.datamodel.pipeline_options",
        "docling.pipeline.vlm_pipeline",
        "docling_ibm_models",
        "scipy.special.cython_special",
        "sklearn.utils._typedefs",
        "sklearn.neighbors._partition_nodes",
    ]
    + dynamic_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Kookie",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Kookie",
)

app = BUNDLE(
    coll,
    name="Kookie.app",
    icon=str(project_root / app_icon_rel),
    bundle_identifier="com.ematta.kookie",
)
