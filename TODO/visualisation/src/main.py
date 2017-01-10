#!/usr/bin/env python
import sys, os, argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import operator

# Custom calsses written locally, import as needed
from parameters import A, M, NP
from summarystats import SummaryStats
from plot_main import Plot
from boxplot import Boxplot

if __name__ == "__main__":
    # Opening the store to get the HDF file for Agent-type
    store = pd.io.pytables.HDFStore('/home/susupta/Desktop/GitHub/Bank/Bank.h5')
    # Main dataframe to hold all the dataframes of each instance    
    d = pd.DataFrame()
    df_mean = []
    # Going through sets and runs in the HDF file
    for key in store.keys():
        # getting set and run values from the names: set_1_run_1_iters etc. hardcoded atm
        if len(key) == 18:
            s = int(key[5:-12])
            r =int(key[11:-6])
        else:
            s = int(key[5:-13])
            r =int(key[11:-6])
        # Opening Panel the particular set and run        
        pnl = store.select(key)

        # Converting panel to Dataframe        
        df = pnl.to_frame()

        # Adding two columns for set and run into the dataframe for two added level of indexing  
        df['set'] = s
        df['run'] = r
        df.set_index('run', append = True, inplace = True)
        df.set_index('set', append = True, inplace = True)
        d_i = df.reorder_levels(['set', 'run', 'major', 'minor'])

        # Adding each of the dataframe from panel into a main dataframe which has all the sets and runs        
        if d.empty:
            d = d_i
        else:   
            d = pd.concat([d,d_i], axis =0)
        # Some tweak to get the multiindex working again for the main df        
        d.index = pd.MultiIndex.from_tuples(d.index,names=['set','run','major','minor'])      
        del df,d_i   # Deleting sub df's for garbage collection  

    # Using appropriate index to get the required row and column from the main dataframe         
    filtered_df = d.iloc[(d.index.get_level_values('set') == 1) & (d.index.get_level_values('run') <= 2) & (d.index.get_level_values('major') <= 6200) & (d.index.get_level_values('minor') <= 2 )]['total_credit'].astype(float)


    # Example plots

    #############################################################################################################
    # For timeseries

    # instantiate a class with desired analysis type
    P = SummaryStats(filtered_df, A.agent) 
    
    # then call the desired method, if no plot wanted
    # print P.mean() # options: mean, median, upper_quartile, lower_quartile, custom_quantile, minimum, maximum

    # instantiate a plot class with desired output (Single, Multiple)
    Fig = Plot(P.mean(), NP.multiple) 

    # Calling the plot class instance with the desired kind of plot
    Fig.timeseries()
    ############################################################################################################ 
    #
    #
    ############################################################################################################
    # For boxplot

    # For boxplot it is a little different than the above methods as multiple instance of summary stats is needed

    # Instantiate a boxplot class
    # Fig = Boxplot(filtered_df, NP.single, A.agent)  
    
    # call the appropriate method within the class
    # Fig.single_output()
    #############################################################################################################



    store.close()