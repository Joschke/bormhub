import streamlit as st
import pandas as pd
import numpy as np
import re

st.set_page_config(layout="wide")

# wrap everything in main() so we can return until inputs are given
# https://discuss.streamlit.io/t/is-there-a-pretty-way-to-stop-quit-script-until-parameters-have-been-set/1603/5
def main():
    
    path_num = st.text_input("Number of logbook path inputs to stitch", 1)

    path_list = []

    for i in range(int(path_num)):

        path = st.text_input(f"Logbook path {i+1}").encode('unicode-escape').decode()
        # remove quotes if the user enters a path with quotes
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        path_list = path_list + [path]
    
    # the rest of the code will not run until this checkbox is checked
    checkbox = st.checkbox("It's Bormin Time")
    if not checkbox:
        return

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

    # caching is not working, no idea why
    @st.cache_data()
    def load_data(path_list):
        
        # added this here to see when im runnin this func
        running = st.empty()
        running.write("Runnin this func")
        
        # need to include skip_blank_lines=False for using blank lines to identify when lifts end
        full_file_df = pd.concat( [ pd.read_csv(csv, sep="      ", header=None, skip_blank_lines=False) for csv in path_list ] )

        latest_iteration = st.empty()
        bar = st.progress(0)

        results = {}
        borm_results = {}
        rep_results = {}
        date_c = "nah"
        lift_c = "nah"
        weight_c = "nah"
        rep_c = "nah"

        lift_results_dict = {}
        lift_info_df = pd.DataFrame(columns=['Count','Unilateral','Bodyweight'])

        date_flag = "### "
        lift_flag = "> "
        weight_flag = ">> "
        bodyweight_flag = "bw"

        # initialise max_weight for an early check
        max_weight = 0

        for idx, row in full_file_df.iterrows():
            
            # this progress bar does not work at all
            latest_iteration.text(f'Reading markdown line {idx+1}')
            bar.progress((idx)/len(full_file_df))

            info = str(row[0])

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

                # upon seeing a lift, add it to lift_info_df
                previous_lift_count = lift_info_df.Count.get(lift_c, 0)
                lift_info_df.loc[lift_c,'Count'] = previous_lift_count + 1

                if not previous_lift_count:
                    # if this is a new lift, set checks to a default of False
                    unilateral_check = False
                    bodyweight_check = False
                    # also, add an empty df to lift_results_dict
                    lift_results_dict[lift_c] = pd.DataFrame(columns=['Max Weight', 'Borm Weight', 'Borm Reps', 'Borm'])

                # if it's an established lift, get checks from the df
                else:
                    unilateral_check = lift_info_df.loc[lift_c,'Unilateral']
                    bodyweight_check = lift_info_df.loc[lift_c,'Bodyweight']

                # establish empty maxes for this lift on this day
                max_weight = 0
                if unilateral_check:
                    max_borm = [0,0]
                    reps_during_borm_set = [0,0]
                    weight_during_borm_set = [0,0]
                else:
                    max_borm = 0
                    reps_during_borm_set = 0
                    weight_during_borm_set = 0

            elif info.startswith(weight_flag):
                weight_c = info[len(weight_flag):]

                # if this is the first time we see this lift, check if it is a bodyweight lift
                if previous_lift_count == 0 and bodyweight_check == False and weight_c.endswith("bw"):
                    bodyweight_check = True
                    lift_info_df.loc[lift_c,'Bodyweight'] = bodyweight_check
                # if it's not a bodyweight lift, add that info to lift_info_df
                elif previous_lift_count == 0:
                    lift_info_df.loc[lift_c,'Bodyweight'] = bodyweight_check

                clean_weight = float(re.sub('[^\d\.]', '', weight_c))

            elif np.isnan(rep_count):
                # if info is nan, we have reached a blank line which indicates the end of the lift, and we can commit maxes for this session
                # also need to check if max_weight has been set to any value so that this does not trigger for blank lines between days
                if info == "nan" and max_weight:
                    current_results_df = pd.DataFrame({'Max Weight': [max_weight], 'Borm Weight': [weight_during_borm_set], 'Borm Reps': [reps_during_borm_set], 'Borm': [max_borm]}, index=[date_c])
                    lift_results_dict[lift_c] = pd.concat([lift_results_dict[lift_c], current_results_df])
                    # reset max_weight to 0 so future blank lines dont trigger this until a new lift begins
                    max_weight = 0

                if info.startswith("L ") | info.startswith("R "):
                    # this is a unilateral lift, so if this is the first time we see this lift, add that info to lift_info_df
                    if previous_lift_count == 0 and unilateral_check == False:
                        unilateral_check = True
                        lift_info_df.loc[lift_c,'Unilateral'] = unilateral_check
                        # recreate empty maxes in this case
                        max_borm = [0,0]
                        reps_during_borm_set = [0,0]
                        weight_during_borm_set = [0,0]
                    
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

                    if clean_weight > max_weight and rep_count:
                        max_weight = clean_weight

                    for i in range(len(borm)):
                        if borm[i] > max_borm[i]:
                            max_borm[i] = borm[i]
                            reps_during_borm_set[i] = rep_count[i]
                            weight_during_borm_set[i] = clean_weight
                    
            elif not np.isnan(rep_count):
                # this is a bilateral lift, so if this is the first time we see this lift, add that info to lift_info_df
                # additionally check if that info is already in lift_info_df so we don't run this for every set on the first day
                # use get to return 1 if the cell is not found
                if previous_lift_count == 0 and lift_info_df.Unilateral.get(lift_c, 1):
                    # unilateral_check will already be false so no need to set it again
                    lift_info_df.loc[lift_c,'Unilateral'] = unilateral_check

                rep_count = float(rep_count)
                borm = borm_calc(rep_count,weight_c)
                
                results[date_c][lift_c].append({'Weight': weight_c, 'Reps': rep_count, 'Borm': borm})

                if clean_weight > max_weight and rep_count:
                    max_weight = clean_weight

                # "and rep_count" to check if reps is more than 0
                if borm > max_borm and rep_count:
                    max_borm = borm
                    reps_during_borm_set = rep_count
                    weight_during_borm_set = clean_weight

        bar.empty()
        latest_iteration.empty()
        running.empty()

        return results, lift_info_df, lift_results_dict

    results, lift_info_df, lift_results_dict = load_data(path_list)

    lift_info_df

    def liftplot(lift_name, num_dates=False):
        st.header(lift_name)

        lift_df = lift_results_dict[lift_name]
        UniCheck = lift_info_df.loc[lift_name, 'Unilateral']
        BWCheck = lift_info_df.loc[lift_name, 'Bodyweight']

        if num_dates > 0:
            lift_df = lift_df[0:num_dates]

        if BWCheck and UniCheck:
            # adding these extra columns feels like it should be unnecessary 
            # but cant figure out how to get rid of them while using st.line_chart
            lift_df["Left Reps"] = [pt[0] for pt in lift_df['Borm Reps']]
            lift_df["Right Reps"] = [pt[1] for pt in lift_df['Borm Reps']]
            y = ['Left Reps', 'Right Reps']

        elif BWCheck:
            y = 'Borm Reps'

        elif UniCheck:
            lift_df["Left Borm"] = [pt[0] for pt in lift_df['Borm']]
            lift_df["Right Borm"] = [pt[1] for pt in lift_df['Borm']]
            y = ['Max Weight', 'Left Borm', 'Right Borm']

        else:
            y = ['Max Weight', 'Borm']

        col1, col2 = st.columns(2)

        with col1:
            lift_df
        with col2:
            st.line_chart(data=lift_df, x=None, y=y)

    option = st.selectbox('Select an exercise', lift_info_df.index)

    liftplot(option)

    # for lift, row in lift_count_df.iterrows():
    #     liftplot(lift)

main()