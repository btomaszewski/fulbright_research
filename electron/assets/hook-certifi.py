from PyInstaller.utils.hooks import collect_data_files
import os
import certifi
import contractions

# Collect contractions data files
datas = collect_data_files('contractions')

# Collect certifi data files and append to datas (not overwrite)
certifi_datas = collect_data_files('certifi')
datas.extend(certifi_datas)

# Add the CA bundle specifically
datas.append((certifi.where(), 'certifi'))