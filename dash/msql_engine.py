import msql_parser

import pandas as pd
import pymzml
import numpy as np


def process_query(input_query, input_filename):
   parsed_dict = msql_parser.parse_msql(input_query)

   # Let's apply this to real data
   MS_precisions = {
      1: 5e-6,
      2: 20e-6,
      3: 20e-6,
      4: 20e-6,
      5: 20e-6,
      6: 20e-6,
      7: 20e-6,
   }
   run = pymzml.run.Reader(input_filename, MS_precisions=MS_precisions)

   ms1mz_list = []
   ms2mz_list = []
   previous_ms1_scan = 0

   for spec in run:
      # Filtering peaks by mz
      peaks = spec.peaks("raw")

      # Filtering out zero rows
      peaks = peaks[~np.any(peaks < 1.0, axis=1)]

      # Sorting by intensity
      peaks = peaks[peaks[:, 1].argsort()]

      mz, intensity = zip(*peaks)

      mz_list = list(mz)
      i_list = list(intensity)

      if spec.ms_level == 1:
         for i in range(len(mz_list)):
            peak_dict = {}
            peak_dict["i"] = i_list[i]
            peak_dict["mz"] = mz_list[i]
            peak_dict["scan"] = spec.ID

            ms1mz_list.append(peak_dict)

            previous_ms1_scan = spec.ID

      if spec.ms_level == 2:
         msn_mz = spec.selected_precursors[0]["mz"]
         for i in range(len(mz_list)):
            peak_dict = {}
            peak_dict["i"] = i_list[i]
            peak_dict["mz"] = mz_list[i]
            peak_dict["scan"] = spec.ID
            peak_dict["precmz"] = msn_mz
            peak_dict["ms1scan"] = previous_ms1_scan

            ms2mz_list.append(peak_dict)

   # Turning into pandas data frames
   ms1_df = pd.DataFrame(ms1mz_list)
   ms2_df = pd.DataFrame(ms2mz_list)

   # Applying the filtering conditions
   # TODO: need to make sure chaining within the same MS2 level works appropriately
   for condition in parsed_dict["conditions"]:
      print(condition)
      if condition["type"] == "ms2productcondition":
         mz_tol = 0.1
         mz_min = condition["value"] - mz_tol
         mz_max = condition["value"] + mz_tol
         ms2_filtered_df = ms2_df[(ms2_df["mz"] > mz_min) & (ms2_df["mz"] < mz_max)]
         filtered_scans = set(ms2_filtered_df["scan"])
         ms2_df = ms2_df[ms2_df["scan"].isin(filtered_scans)]

         # Filtering the MS1 data now
         ms1_scans = set(ms2_df["ms1scan"])
         ms1_df = ms1_df[ms1_df["scan"].isin(ms1_scans)]

      if condition["type"] == "ms2precursorcondition":
         mz_tol = 0.1
         mz_min = condition["value"] - mz_tol
         mz_max = condition["value"] + mz_tol
         ms2_df = ms2_df[(ms2_df["precmz"] > mz_min) & (ms2_df["precmz"] < mz_max)]

      if condition["type"] == "ms1mzcondition":
         mz_tol = 0.1
         mz_min = condition["value"] - mz_tol
         mz_max = condition["value"] + mz_tol
         ms1_filtered_df = ms1_df[(ms2_df["mz"] > mz_min) & (ms1_df["mz"] < mz_max)]
         filtered_scans = set(ms1_filtered_df["scan"])
         ms1_df = ms1_df[ms1_df["scan"].isin(filtered_scans)]

      if condition["type"] == "ms2neutrallosscondition":
         mz_tol = 0.1
         nl_min = condition["value"] - mz_tol
         nl_max = condition["value"] + mz_tol
         ms2_filtered_df = ms2_df[((ms2_df["precmz"] - ms2_df["mz"]) > nl_min) & ((ms2_df["precmz"] - ms2_df["mz"]) < nl_max)]
         filtered_scans = set(ms2_filtered_df["scan"])
         ms2_df = ms2_df[ms2_df["scan"].isin(filtered_scans)]

         # Filtering the MS1 data now
         ms1_scans = set(ms2_df["ms1scan"])
         ms1_df = ms1_df[ms1_df["scan"].isin(ms1_scans)]

   print(parsed_dict["querytype"])

   # collating the results
   if parsed_dict["querytype"]["function"] is None:
      if parsed_dict["querytype"]["datatype"] == "datams1data":
         return ms1_df
      if parsed_dict["querytype"]["datatype"] == "datams2data":
         return ms2_df
   else:
      print(parsed_dict["querytype"]["function"])
      # Applying function
      if parsed_dict["querytype"]["function"] == "functionscansum":

         # TODO: Fix how this scan is done so the result values for most things actually make sense
         if parsed_dict["querytype"]["datatype"] == "datams1data":
            ms1_df = ms1_df.groupby("scan").sum()
            return ms1_df
         if parsed_dict["querytype"]["datatype"] == "datams2data":
            ms2_df = ms2_df.groupby("scan").sum()

            return ms2_df

      if parsed_dict["querytype"]["function"] == "functionscanmz":
         result_df = pd.DataFrame()
         result_df["precmz"] = ms2_df["precmz"]
         return result_df

      if parsed_dict["querytype"]["function"] == "functionscannum":
         result_df = pd.DataFrame()

         if parsed_dict["querytype"]["datatype"] == "datams1data":
            result_df["scan"] = list(set(ms1_df["scan"]))
         if parsed_dict["querytype"]["datatype"] == "datams2data":
            result_df["scan"] = list(set(ms2_df["scan"]))
         
         return result_df
         


      

      print("APPLYING FUNCTION")