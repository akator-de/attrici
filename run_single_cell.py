import os
import numpy as np
import netCDF4 as nc
from datetime import datetime
from pathlib import Path
import pandas as pd
from func_timeout import func_timeout, FunctionTimedOut
import icounter
import icounter.estimator as est
import icounter.datahandler as dh
import settings as s

print("Version", icounter.__version__)

lat = -20.25
lon = -49.75

submitted = False
njobarray = 1
task_id = 0
s.progressbar = True

dh.create_output_dirs(s.output_dir)

gmt_file = s.input_dir / s.dataset / s.gmt_file
ncg = nc.Dataset(gmt_file, "r")
gmt = np.squeeze(ncg.variables["tas"][:])
ncg.close()

input_file = s.input_dir / s.dataset / s.source_file.lower()
# landsea_mask_file = s.input_dir / s.landsea_file

obs_data = nc.Dataset(input_file, "r")
# nc_lsmask = nc.Dataset(landsea_mask_file, "r")
nct = obs_data.variables["time"]
lats = obs_data.variables["lat"][:]
lons = obs_data.variables["lon"][:]

sp = {}
sp["lat"] = lat
sp["lon"] = lon
try:
    sp["index_lat"] = np.where(lats == lat)[0][0]
    sp["index_lon"] = np.where(lons == lon)[0][0]
except IndexError:
    print("lat or lon not present in data, adjust!")
    raise

estimator = est.estimator(s)

TIME0 = datetime.now()

# print( sp["index_lat"], sp["index_lon"])
data = obs_data.variables[s.variable][:, sp["index_lat"], sp["index_lon"]]
df, datamin, scale = dh.create_dataframe(nct[:], nct.units, data, gmt, s.variable)

try:
    trace, dff = func_timeout(
        s.timeout, estimator.estimate_parameters, args=(df, sp["lat"], sp["lon"])
    )
except (FunctionTimedOut, ValueError) as error:
    print("Sampling at", sp["lat"], sp["lon"], " timed out or failed.")
    print(error)
    # continue

df_with_cfact = estimator.estimate_timeseries(dff, trace, datamin, scale)
dh.save_to_disk(df_with_cfact, s, sp["lat"], sp["lon"], dformat=s.storage_format)

obs_data.close()
# nc_lsmask.close()
print(
    "Estimation completed for all cells. It took {0:.1f} minutes.".format(
        (datetime.now() - TIME0).total_seconds() / 60
    )
)