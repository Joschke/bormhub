import streamlit as st
import os 
import pandas as pd
import numpy as np
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys

st.set_page_config(layout="wide")

# the bormhub folder goes in the same dropbox folder where notes are synced
current_path = os.path.abspath("")
directory = os.path.dirname(current_path)
results_directory = rf"{directory}\bormhub_results"
notes_directory = rf"{directory}\Notes"
filename_list = ['Lifting 2025', 'Lifting 2024', '5x5']
path_list = [ rf"{notes_directory}\{x}.md" for x in filename_list ]

def borm_calc(rep,weight_c):
    # https://stackoverflow.com/questions/26071855/remove-everything-but-leave-numbers-and-dots
    weight_c = float(re.sub('[^\d\.]', '', weight_c))
    if rep == 0:
        return float(0)
    # if reps <= 10, use Brzycki formula for borm
    elif rep <= 10:
        return weight_c*36/(37-rep)
    # if reps > 10, use Epley formula
    else:
        return weight_c*(1+0.0333*rep)
    
def borm_list_maker(rep_count,weight_c):
    borm_list = []
    for rep in rep_count:
        borm_list.append(borm_calc(rep,weight_c))
    return borm_list

def flatten(xss):
    return [x for xs in xss for x in xs]

full_file_df = pd.concat( [ pd.read_csv(csv, sep="      ", header=None) for csv in path_list ] )

results = {}
borm_results = {}
rep_results = {}
date_c = "nah"
lift_c = "nah"
weight_c = "nah"
rep_c = "nah"

bodyweight_exercises = []

date_flag = "### "
lift_flag = "> "
weight_flag = ">> "
bodyweight_flag = "bw"

for idx, row in full_file_df.iterrows():
    info:str = row[0]
    # print(info)

    rep_count = pd.to_numeric(info, errors="coerce")

    if info.startswith(date_flag):
        date_c = info[len(date_flag):]
        results[date_c] = {}
        borm_results[date_c] = {}
        rep_results[date_c] = {}

    elif info.startswith(lift_flag):
        lift_c = info[len(lift_flag):]
        if lift_flag not in results[date_c]:
            results[date_c][lift_c] = []
            borm_results[date_c][lift_c] = []
            rep_results[date_c][lift_c] = []

    elif info.startswith(weight_flag):
        weight_c = info[len(weight_flag):]

    elif np.isnan(rep_count):
        if info.startswith("L ") | info.startswith("R "):
            rep_count = info.replace(" ","")
            if info.startswith("L "):
                rep_count = rep_count[1:].split('R')
            else:
                rep_count = rep_count[1:].split('L')
                # reverse so L is always first
                rep_count = list(reversed(rep_count))

            rep_count = [ float(x) for x in rep_count ]
            borm = borm_list_maker(rep_count,weight_c)

            results[date_c][lift_c].append({'Weight': weight_c, 'Reps': rep_count, 'Borm': borm})
            
    elif not np.isnan(rep_count):
        rep_count = float(rep_count)
        borm = borm_calc(rep_count,weight_c)
        
        results[date_c][lift_c].append({'Weight': weight_c, 'Reps': rep_count, 'Borm': borm})

# results

# set up dataframes for each lift
lift_count_dict = {}
for date in results:
    for lift in results[date]:
        lift_count_dict[lift] = lift_count_dict.get(lift, 0) + 1

lift_count_df = pd.DataFrame.from_dict(lift_count_dict,orient='index',columns=['Days performed'])
# lift_count_df = lift_count_df.sort_values(['Days performed'], ascending=[False])
lift_count_df

# this function could be simpler
def liftanalyser(current_lift):
    date_list = []
    weight_list = []
    borm_list = []
    borm_rep_list = []
    borm_weight_list = []
    bodyweight_check = False
    unilateral_check = False

    for date in results:
        for lift in results[date]:
            if lift == current_lift:
                date_list.append(date)

                # check if it's a unilateral lift first
                reps = results[date][lift][0]['Reps']
                if type(reps) is list:
                    unilateral_check = True

                max_weight = 0

                if unilateral_check:
                    max_borm = [0,0]
                    reps_during_borm_set = [0,0]
                    weight_during_borm_set = [0,0]
                else:
                    max_borm = 0
                    reps_during_borm_set = 0
                    weight_during_borm_set = 0

                for set in results[date][lift]:
                    weight = set['Weight']
                    reps = set["Reps"]
                    borm = set['Borm']

                    # if type(reps) is list:
                    #     reps = sum(reps)

                    # check if it's a bodyweight lift
                    if bodyweight_check == False and weight.endswith("bw"):
                        bodyweight_check = True

                    # else it's a weighted lift
                    else:
                        clean_weight = float(re.sub('[^\d\.]', '', weight))

                        # check if this weight exceeds max_weight
                        # also check if reps is more than 0, otherwise it doesn't count as a max weight
                        if clean_weight > max_weight and reps:
                            max_weight = clean_weight

                        # check if this is the borm set
                        if unilateral_check:
                            for i in range(len(borm)):
                                if borm[i] > max_borm[i]:
                                    max_borm[i] = borm[i]
                                    reps_during_borm_set[i] = reps[i]
                                    weight_during_borm_set[i] = clean_weight

                        elif type(borm) == float:
                            if borm > max_borm and reps:
                                max_borm = borm
                                reps_during_borm_set = reps
                                weight_during_borm_set = clean_weight
                        else: 
                            sys.exit(f"Strange borm: {borm}")
                    
                weight_list.append(max_weight)
                borm_weight_list.append(weight_during_borm_set)
                borm_rep_list.append(reps_during_borm_set)
                borm_list.append(max_borm)

    date_list = pd.to_datetime(date_list, format="%Y-%m-%d")
    lift_df = pd.DataFrame({'Weight': weight_list, 'Borm Weight': borm_weight_list, 'Borm Reps': borm_rep_list, 'Borm': borm_list}, index=date_list)
    lift_info = pd.DataFrame({'UniCheck': unilateral_check, 'BWCheck': bodyweight_check}, index=[current_lift])
    return lift_df, lift_info

lift_df_dict = {}
lift_info_df = pd.DataFrame(columns=['UniCheck','BWCheck'])
for lift, row in lift_count_df.iterrows():
    lift_df_dict[lift],lift_info = liftanalyser(lift)
    lift_info_df = pd.concat([lift_info_df, lift_info], ignore_index=False)

def liftplot(lift_name, num_dates=False):
    st.header(lift_name)

    lift_df = lift_df_dict[lift_name]
    UniCheck = lift_info_df.loc[lift_name, 'UniCheck']
    BWCheck = lift_info_df.loc[lift_name, 'BWCheck']

    if num_dates > 0:
        lift_df = lift_df[0:num_dates]

    if BWCheck:
        y = 'Borm Reps'

    elif UniCheck:
        lift_df["Left Borm"] = [pt[0] for pt in lift_df['Borm']]
        lift_df["Right Borm"] = [pt[1] for pt in lift_df['Borm']]
        y = ['Weight', 'Left Borm', 'Right Borm']

    else:
        y = ['Weight', 'Borm']

    col1, col2 = st.columns(2)

    with col1:
        lift_df
    with col2:
        st.line_chart(data=lift_df, x=None,y=y)

for lift, row in lift_count_df.iterrows():
    liftplot(lift)