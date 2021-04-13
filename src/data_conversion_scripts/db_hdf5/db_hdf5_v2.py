#!/usr/bin/env python3

#################################################################################################################
## This script creates HDF5 files from corresponding SQLite db files in one-to-one fashion. So, for each db file
## present in the input folder, a corresponding HDF5 file is created in the output folder. To combine db files into
## a single HDF5 file, use version 1 of script named db_hdf5_v1.py instead.
#################################################################################################################

from __future__ import print_function
import sqlite3, sys, glob, os, argparse
import pandas as pd


pd.set_option('io.hdf.default_format','table')  # Commenting this line out will write HDF5 as a fixed format, and not as a table format
                                                # Writing as a fixed format is faster than writing as a table, but the file cannot be 'modified/appended to' later on
DB_SUFFIX = '.db'

# Function to check for existing directories, and create a new one if not present
def dir_check(d):
    if os.path.exists(d):
        outpath = os.path.abspath(d)
        print("- Directory used for output: [" + outpath + "]")

    else:
        os.makedirs(d)
        outpath = os.path.abspath(d)
        print("- Output directory created: [" + outpath + "]")

# Function to print out the error messages,if any, and exit
def error(mesg):
    print('>>>>> (Error): {0}' .format(mesg), file = sys.stderr)
    sys.exit(1)


def agent_dataframe(agent_name):
    agent_name = agent_name.decode('utf-8')
    df = pd.read_sql(("SELECT * from "+ agent_name), con)

    # Ignoring the empty tables
    if df.empty == False:
    #Converting the datatypes to make all of them uniform, to avoid pickling later on when writing to HDF
        types = df.apply(lambda x: pd.api.types.infer_dtype(x.values))

        for col in types[types=='floating'].index:
            df[col] = df[col].astype(str)

        for col in types[types=='mixed'].index:
            df[col] = df[col].astype(str)

        for col in types[types=='unicode'].index:
            df[col] = df[col].astype(str)

        # Keeping count of the individual agent instance
        # IterationList =[]
        # agtin = str('agent_inst').encode('utf-8')
        # IterationList = df['_ITERATION_NO'].tolist()
        # j=0
        # agentinstance_index =[j]
        # for i in range(1,len(IterationList)):
        #   if IterationList[i] == IterationList[i-1]:
        #       j=j+1
        #       agentinstance_index.append(j)
        #   else:
        #       j=0
        #       agentinstance_index.append(j)
        # # Adding the agent instance count as a separate column to the dataframe
        # df[agtin] = agentinstance_index
        # # Creating hierarchial index for df with the iteration number, and agent instance count
        # df.set_index(['_ITERATION_NO',agtin], inplace=True)

        # Set [iters,id] as the new index
        #df.reset_index() # start anew
        df.set_index(['_ITERATION_NO','id'], inplace=True)

        return df

def gen_hdf(fname, output_folder, chunksize, h5_compression):
    outFileName = output_folder + '/' +  os.path.basename(fname)[:-len(DB_SUFFIX)]
    fname_tostore = outFileName +'.h5'
    #verboseprint ('- Preparing HDF5 file: '+os.path.basename(fname_tostore)+'for writing')
    #store = pd.HDFStore(fname_tostore, 'w', chunksize = 500, complevel = 1, complib ='bzip2', fletcher32 = True)

    if (h5_compression):
        verboseprint ('\n- \t HDFStore using: compression, with chunksize: ' + str(chunksize))
        store = pd.HDFStore(fname_tostore, 'w', chunksize = chunksize, complevel = 1, complib ='bzip2', fletcher32 = True) # store with compression
    else:
        verboseprint ('\n- \t HDFStore using: no compression')        
        store = pd.HDFStore(fname_tostore, 'w')  # to store without compression

    global con, cur, agent_name
    con = None
    try:
        con = sqlite3.connect(fname)
        cur = con.cursor()

        # Get the name of all the tables in the SQLite DB i.e. the agent types
        cur.execute("SELECT name from sqlite_master WHERE type='table';")
        agent_list = [x[0].encode('ascii', 'ignore') for x in cur.fetchall()]
        w = str('_iters_').encode('utf-8')
        if w in agent_list:
            agent_list.remove(w)
        # Iterate through all the agent tables in the DB and add each to a unique Dataframe
        for agent_name in agent_list:
            verboseprint ('- Processing table values for: '+str(agent_name).replace("b'","'"))
            dfa = agent_dataframe(agent_name)
            verboseprint ('- Obtained Dataframe for: '+str(agent_name).replace("b'","'"))
            # Checking and ignoring empty agent tables that might be in the DB
            if dfa is not None:
                verboseprint ('- Preparing HDF5 file for writing')
                a = agent_name.decode('utf-8')
                # Storing the object (dataframe) in the HDF Store
                store[a] = dfa
                verboseprint ('- Successfully wrote: '+str(agent_name).replace("b'","'")+ ' into HDF5 file. \n')
    except sqlite3.Error as e:
        print("Error ", e.args[0])
        sys.exit(1)
    finally:
        if con:
            con.close()
    verboseprint ('- Successfully closed HDF5 file: '+os.path.basename(fname_tostore)+'\n')
    store.close()
    del dfa


if __name__ == "__main__":
    # Setup for command line arguments
    parser = argparse.ArgumentParser(prog='db_hdf5_v2.py', description='Converts SQLite database files to HDF5 files (1-to-1). The script creates a corresponding .h5 file for each .db file.')
    parser.add_argument('dbpath', help='Path to folder containing the .db files', nargs=1, type=str)
    parser.add_argument('-o', '--outpath', help='Path to output folder where h5 files should be written', nargs=1, type=str)
    parser.add_argument('-v', '--verbose', help='Get the status of the intermediate processing steps', action='store_true')
    parser.add_argument('-s', '--status', help='Get the total progress of the processing', action='store_true')
    parser.add_argument('-r', '--recursive', help = 'Use recursion to process all subfolders',action='store_true')
    parser.add_argument('-c', '--chunksize', help='Set the chunksize for HDF5 files', nargs='?', type=int, const=500, default=500, action='store', required=False)
    parser.add_argument('-z', '--compress', help='Use internal compression in HDFStore', nargs='?', type=int, const=1, default=1, action='store', required=False)

    args = parser.parse_args()

    #Setup for verbose arguments
    if args.verbose:
        def verboseprint(*args):
            for arg in args:
                print(arg, end=' ')
            print()
    else:
        verboseprint = lambda *a: None

    #Setup for process status arguments
    if args.status:
        def statusprint(*args):
            for arg in args:
                print(arg, end=' ')
            print()
    else:
        statusprint = lambda *a: None

    # Settings for HDF5 files
    chunksize = args.chunksize
    verboseprint ('- Chunksize used in HDFStore: ' + str(chunksize))
    h5_compression = args.compress
    if (h5_compression):        
        verboseprint ('- Compression used in HDFStore: ' + str(h5_compression))
    else:
        verboseprint ('- Compression used in HDFStore: ' + 'None')


    # Set input parameters
    input_dbfolder = args.dbpath[0]

    if os.getcwd() == os.path.abspath(input_dbfolder):
        error("- Python script and data files not allowed in a single folder. The script expects at least one level of folder hierarchy. Please fix the issue and retry.")

    dir_list =[]
    if args.recursive:
        # Checking for nested subdirectories within a directory
        for (dirpath,dirnames,filenames) in os.walk(input_dbfolder):
            dir_list.append(os.path.abspath(dirpath))
    else:
        dir_list.append(os.path.abspath(input_dbfolder))

    # Set output parameters
    output_folder =  ''
    if args.outpath:
        output_folder = args.outpath[0]
    else:
        # Choose one of the options below and comment out the other as desired.
        #output_folder =  './output_'+os.path.basename(os.path.dirname(input_dbfolder)) # Create output folder in the same folder where Python script is located.
        #output_folder =  os.path.dirname(input_dbfolder)+'/output_'+os.path.basename(os.path.dirname(input_dbfolder))  # Create output folder in the same folder where input folder is located.
        output_folder =  os.path.dirname(input_dbfolder)  # Create no output folder and places h5 file in same folder as input file.

    # Function call to check if the output folder already exists, and create if not present
    dir_check(output_folder)

    F = len(dir_list)
    # Process each folder in the input directory
    processed_folders = 0
    statusprint('\n- Total number of folders: '+ str(F)+'\n')

    for d in dir_list:
        statusprint('- Started processing folder: '+os.path.basename(d))
        statusprint('- \t complete path: ' + os.path.abspath(d))

        # Populate the list with all sql file names in the folder
        db_file_list = []
        for fname in glob.glob(os.path.join(d, '*'+DB_SUFFIX)):
            db_file_list.append(fname)
            statusprint('- \t adding to list: '+str(fname))
        statusprint('- Total number of files within folder: '+ str(len(db_file_list)))
        
        # Generate HDFStore objects and store in h5 file
        processed_files =[]
        for fname in sorted(db_file_list):
            verboseprint('\n- Started processing: '+os.path.basename(fname))
            gen_hdf(fname, output_folder, chunksize, h5_compression)
            processed_files.append(fname)
            percent = round((float(len(processed_files))/len(db_file_list))*100,2)
            statusprint('- Number processed files: '+str(len(processed_files))+', of total: '+str(len(db_file_list))+'    Progress: '+ str(percent) +'%'),
        statusprint('- Finished processing folder: '+os.path.basename(d)+'\n')
        processed_folders = processed_folders+1
        f_percent = round((float(processed_folders)/F)*100,2)
        statusprint('- Total progress: '+ str(f_percent) +'%', '\n')
