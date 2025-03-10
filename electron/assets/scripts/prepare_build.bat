@echo off
:: Prepare PyInstaller build environment

:: Create temp directory for build
if not exist "%TEMP_BUILD_DIR%\src" mkdir "%TEMP_BUILD_DIR%\src"

:: Copy all Python scripts to temp_build/src
xcopy /Y "%SRC_DIR%\*.py" "%TEMP_BUILD_DIR%\src\"

:: Create a custom hook file for certifi
echo Creating certifi hook for SSL certificate handling...
(
echo from PyInstaller.utils.hooks import collect_data_files
echo import certifi
echo import os
echo.
echo # This will collect all certifi's data files
echo datas = collect_data_files('certifi')
echo.
echo # Add the CA bundle specifically
echo datas.append((certifi.where(), 'certifi'))
) > "%TEMP_BUILD_DIR%\hook-certifi.py"

:: Create a hook for sentence_transformers
echo Creating sentence_transformers hook...
(
echo from PyInstaller.utils.hooks import collect_all
echo.
echo datas, binaries, hiddenimports = collect_all('sentence_transformers')
echo.
echo # Add specific modules that might be missed
echo hiddenimports.extend([
echo     'sentence_transformers.models',
echo     'torch',
echo     'transformers',
echo     'numpy',
echo ])
) > "%TEMP_BUILD_DIR%\hook-sentence_transformers.py"

:: Create a hook for contractions package
echo Creating contractions hook...
(
echo from PyInstaller.utils.hooks import collect_data_files, collect_all
echo.
echo # Collect all data files for contractions package
echo datas, binaries, hiddenimports = collect_all('contractions')
echo.
echo # Add explicit data file
echo import os
echo import contractions
echo import inspect
echo.
echo package_path = os.path.dirname(inspect.getfile(contractions))
echo data_path = os.path.join(package_path, 'data')
echo.
echo if os.path.exists(data_path):
echo     # Add all files in the data directory
echo     for file in os.listdir(data_path):
echo         full_path = os.path.join(data_path, file)
echo         if os.path.isfile(full_path):
echo             datas.append((full_path, os.path.join('contractions', 'data')))
echo             print(f"Added data file: {full_path}")
echo else:
echo     print(f"Warning: Contractions data directory not found at {data_path}")
) > "%TEMP_BUILD_DIR%\hook-contractions.py"

:: Create hook for geopy
echo Creating geopy hook...
(
echo from PyInstaller.utils.hooks import collect_all
echo.
echo datas, binaries, hiddenimports = collect_all('geopy')
echo.
echo # Add specific modules that might be missed
echo hiddenimports.extend([
echo     'geopy.geocoders',
echo     'geopy.geocoders.nominatim',
echo ])
) > "%TEMP_BUILD_DIR%\hook-geopy.py"

:: Create the spec file for PyInstaller
echo Creating PyInstaller spec file...

:: Generate process.spec file
(
echo # -*- mode: python ; coding: utf-8 -*-
echo import certifi  # Import certifi for SSL certificate path
echo import os
echo import contractions
echo import inspect
echo.
echo block_cipher = None
echo.
echo # Get contractions package path and data files
echo contractions_path = os.path.dirname(inspect.getfile(contractions))
echo contractions_data_path = os.path.join(contractions_path, 'data')
echo contractions_dict_path = os.path.join(contractions_data_path, 'contractions_dict.json')
echo contractions_slang_path = os.path.join(contractions_data_path, 'slang_dict.json')
echo.
echo # Path to this spec file's directory
echo spec_dir = os.path.dirname(os.path.abspath(SPEC))
echo.
echo # Define paths relative to spec file
echo vector_model_path = os.path.join(spec_dir, '..', '%VECTOR_MODEL_PACKAGE%')
echo ner_model_path = os.path.join(spec_dir, '..', '%NER_MODEL_PACKAGE%')
echo spacy_model_tarball = os.path.join(spec_dir, '..', '%SPACY_MODEL_DIR%/en_core_web_sm.tar.gz')
echo.
echo a = Analysis(
echo     ['src/wrapper.py'],
echo     pathex=['src'],
echo     binaries=[],
echo     datas=[
echo         ('src/processJson.py', '.'),  # Explicitly include processJson.py in the root
echo         (spacy_model_tarball, '.'),  # Include spaCy model as a tarball in the root
echo         (vector_model_path, '%VECTOR_MODEL_PACKAGE%'),
echo         (ner_model_path, '%NER_MODEL_PACKAGE%'),
echo         (certifi.where(), 'certifi'),  # Include SSL certificates
echo         (contractions_dict_path, os.path.join('contractions', 'data')),  # Include contractions dictionary
echo         (contractions_slang_path, os.path.join('contractions', 'data')),  # Include slang dictionary
echo     ],
echo     hiddenimports=[
echo         'en_core_web_sm',
echo         'src.frameExtraction',
echo         'src.videoAnalysis',
echo         'src.imageAnalysis',
echo         'src.aiLoader',
echo         'src.helpers',
echo         'src.cleanJson',
echo         'src.vectorImplementation',
echo         'src.nerImplementation',
echo         'src.processJson',
echo         'dotenv',
echo         'numpy',
echo         'pandas',
echo         'json',
echo         'pathlib', 
echo         'shutil',
echo         'torch',
echo         'transformers',
echo         'PIL',
echo         'cv2',
echo         'tempfile',
echo         'subprocess',
echo         'openai',
echo         'spacy',
echo         'geopy',
echo         'geopy.geocoders',
echo         'geopy.geocoders.nominatim',
echo         'sentence_transformers',
echo         'certifi',
echo         'tarfile',
echo         'contractions',
echo         'contractions.contractions',
echo         'contractions.data',
echo         'logging',
echo     ],
echo     hookspath=['.'],
echo     hooksconfig={},
echo     runtime_hooks=[],
echo     excludes=[],
echo     win_no_prefer_redirects=False,
echo     win_private_assemblies=False,
echo     cipher=block_cipher,
echo     noarchive=False,
echo )
echo.
echo pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
echo.
echo exe = EXE(
echo     pyz,
echo     a.scripts,
echo     a.binaries,
echo     a.zipfiles,
echo     a.datas,
echo     name='%OUTPUT_NAME%',
echo     debug=False,
echo     bootloader_ignore_signals=False,
echo     strip=False,
echo     upx=True,
echo     upx_exclude=[],
echo     runtime_tmpdir=None,
echo     console=True,
echo     disable_windowed_traceback=False,
echo )
) > "%TEMP_BUILD_DIR%\process.spec"

:: Create a custom hook file for module dependencies 
(
echo from PyInstaller.utils.hooks import collect_all, collect_submodules
echo.
echo # Collect all for important packages
echo datas, binaries, hiddenimports = collect_all('spacy')
echo datas2, binaries2, hiddenimports2 = collect_all('openai')
echo datas3, binaries3, hiddenimports3 = collect_all('sentence_transformers')
echo datas4, binaries4, hiddenimports4 = collect_all('certifi')
echo datas5, binaries5, hiddenimports5 = collect_all('contractions')
echo datas6, binaries6, hiddenimports6 = collect_all('geopy')
echo.
echo # Combine all collected items
echo datas.extend(datas2)
echo datas.extend(datas3)
echo datas.extend(datas4)
echo datas.extend(datas5)
echo datas.extend(datas6)
echo binaries.extend(binaries2)
echo binaries.extend(binaries3)
echo binaries.extend(binaries4)
echo binaries.extend(binaries5)
echo binaries.extend(binaries6)
echo hiddenimports.extend(hiddenimports2)
echo hiddenimports.extend(hiddenimports3)
echo hiddenimports.extend(hiddenimports4)
echo hiddenimports.extend(hiddenimports5)
echo hiddenimports.extend(hiddenimports6)
echo.
echo # Add more specific hidden imports
echo hiddenimports.extend([
echo     'en_core_web_sm',
echo     'src.frameExtraction',
echo     'src.videoAnalysis',
echo     'src.imageAnalysis',
echo     'src.aiLoader',
echo     'src.helpers',
echo     'src.cleanJson',
echo     'src.vectorImplementation',
echo     'src.nerImplementation',
echo     'src.processJson',
echo     'dotenv',
echo     'numpy',
echo     'pandas',
echo     'json',
echo     'pathlib',
echo     'shutil',
echo     'torch',
echo     'transformers',
echo     'PIL',
echo     'cv2',
echo     'tempfile',
echo     'subprocess',
echo     'certifi',
echo     'tarfile',
echo     'sentence_transformers.models',
echo     'contractions',
echo     'contractions.contractions',
echo     'geopy',
echo     'geopy.geocoders',
echo     'geopy.geocoders.nominatim',
echo     'logging',
echo ])
) > "%TEMP_BUILD_DIR%\hook-src.py"