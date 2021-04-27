#!/usr/bin/env python
# $Id: gendb.py 2005 2009-07-31 14:14:48Z lsc $
#
# Copyright (c) 2009 STFC Rutherford Appleton Laboratory
# Author: Lee-Shawn Chin
# Date  : July 2009
#
# NOTE: This is a proof-of-concept implementation. It was not designed for
#       production use but merely to explore what is possible
#       Use at your own risk ;)
#

import argparse, os, re, sys
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from glob import glob
import sqlite3

outfile = "iters.db"

def error(mesg):
    print(">>>>> (Error): {0}".format(mesg), file=sys.stderr)
    sys.exit(1)

def warn(mesg):
    print(">> (Warning): {0}".format(mesg), file=sys.stderr)

def file_exist(fname):
    f = glob(fname)
    if fname in f: return True
    else: return False

def get_node_text(node):
    if len(node.childNodes) != 1 or node.childNodes[0].nodeType != node.TEXT_NODE:
        error("getText() routine used on non-text XML node")
    return node.childNodes[0].data.strip()

def get_agent_sql(data):
    # "data" should be in format
    # data["name"] = "agent_name"
    # data["iter"] = 1
    # data["vars"] = {}
    #     data["vars"]["varname"] = value
    global agents

    try:
        name = data["name"]
        vars = data["vars"]
        iter = data["iter"]
    except:
        error("BUG!! contact script author")

    # check agent exists
    if name not in agents.keys():
         print("var ignored {0}".format(name))

    else:
	    # retrieve values in the right order
	    keys = []
	    values = []
	    for v in vars.keys():
    		if v == "name": continue
    		if v not in agents[name]:
    		     continue

    		else :
    			keys.append(v)
    			values.append(vars[v])

	    sql = []
	    sql.append("insert into {0}".format(name))
	    sql.append("(_ITERATION_NO,{0})".format(",".join(keys)))
	    sql.append("values ({0},'{1}');" .format(iter, "','".join(values)))
	    return " ".join(sql)

def load_iteration_file(itno, basedir, db):

    filename = os.path.join(basedir, "{0}.xml".format(itno))
    print("   + Reading file {0}".format(filename))

    if not file_exist(filename):
        error("Strange! Input file disappeared : {0}".format(filename))
    try:
        file = open(filename, "r")
    except:
        error("Could not open file {0}".format(filename))


    db.execute("INSERT INTO _iters_(itno) VALUES ({0});".format(i))

    data = {}
    in_xagent_tag = False
    line = file.readline()
    re_tag = re.compile(r"<(\w+)>([^<]*)</\1>")

    while line:
        line = line.strip()

        if not line: # ignore empty lines
             # get next line and restart loop
            line = file.readline()
            continue

        if in_xagent_tag:
            if line == "</xagent>": # end if this agent def
                in_xagent_tag = False

                try:
                    db.execute(get_agent_sql(data)) # store data in db
                except ValueError:
                    print("Skip agent")
                    del(data)

            else: # next agent mem
                match = re_tag.match(line)
                if not match: error("Unknown line: {0}".format(line))

                tag = match.group(1)
                val = match.group(2)

                if tag == "name":
                    data["name"] = val
                else:
                    data["vars"][tag] = val

        else: # outside xagent tag
            if line == "<xagent>":
                in_xagent_tag = True
                data = {}
                data["iter"] = i
                data["vars"] = {}


        line = file.readline() # get next line

    file.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='gendb_special.py', description='Script creates SQLite db file from corresponding XML files in many-to-one fashion, and skips missing Agents.')
    parser.add_argument('--model', '-m', help='Set (absolute or relative) path to the directory that contains the model, including the name of the model file (model.xml).', nargs=1, type=str, required=True)
    parser.add_argument('--xml', '-x', help='Set (absolute or relative) path to the directory that contains the data to be converted (xml files).', nargs=1, type=str, required=True)
    parser.add_argument('--output', '-o', help='Set (absolute or relative) path to the directory where the output file should be written (iters.db). If the folder does not exist, it will be created.', nargs=1, type=str, required=False)
    args = parser.parse_args()

    # check if output argument is used
    if args.output:
        # check if a custom .db file is used
        if args.output[0].rsplit('/', 1)[1].endswith('.db'):
            # check if output directory exists
            if not os.path.isdir(args.output[0].rsplit('/', 1)[0]):
                error("Output directory ({0}) does not exist".format(args.output[0].rsplit('/', 1)[0]))
            else:
                outfile = str(args.output[0])
        else:
            # check if output directory exists
            if not os.path.isdir(args.output[0]):
                error("Output directory ({0}) does not exist".format(args.output[0]))
            else:
                # check for output path and add an ending slash if necessary
                if args.output[0][-1:] is '/':
                    outfile = str(args.output[0] + outfile)
                else:
                    outfile = str(args.output[0] + '/' + outfile)

    # get input arguments
    model = args.model[0]
    itsdir = args.xml[0]

    # check that model file exists
    if not file_exist(model):
        error("Model file ({0}) does not exist".format(model))

    # ensure directory exists
    if not os.path.isdir(itsdir):
        error("Input directory ({0}) does not exist".format(itsdir))

    # Retrieve list of data files
    datafiles = glob(os.path.join(itsdir, "[0-9]*.xml"))
    if len(datafiles) == 0:
        error("No data files found in {0}".format(itsdir))

    # get list of iters from datafile names
    print("")
    print(" - Scanning \"{0}\"".format(itsdir))
    iters = []
    iter_pattern = "{0}{1}*([0-9]+)\.xml".format(itsdir, os.sep)
    iter_re = re.compile(iter_pattern)
    for df in datafiles:
        match = iter_re.match(df)
        if not match:
            error("BUG: Unknown line \nglob line = {0} \npattern = {1}".format(df, iter_pattern))
        iters.append(int(match.group(1)))
    iters.sort()
    print(" - Found iters : {0}".format(str(iters)[1:-1]))

    # Initialise database
    print(" - Initialising database file : \"{0}\"".format(outfile))
    if file_exist(outfile):
        print("   ... File already exist. Deleting.")
        try:
            os.remove(outfile)
        except:
            error("Could not delete file {0}".format(outfile))
    db = sqlite3.connect(outfile, isolation_level=None) # manage our own transactions

    # some performance tuning
    db.execute("PRAGMA temp_store = MEMORY;")
    db.execute("PRAGMA synchronous = OFF;")
    db.execute("PRAGMA journal_mode = OFF;")

    # parse xmml file to determine required database structure
    print(" - Analysing model")
    agents = {}
    models = [model]
    model_count = 0

    while len(models) > 0:
        fname = models.pop()
        model_count = model_count + 1
        if model_count == 1:
            dirname = os.path.dirname(fname) #update root model.xml folder only once, re-use for nested model.xml files with hard paths

        # load xml file
        print("   + parsing {0}".format(fname))
        try:
            dom = minidom.parse(fname)
        except IOError:
            error("Unable to read model file ({0})".format(fname))
        except ExpatError:
            error("Invalid XML file ({0})".format(fname))

        # detect nested models
        nodes = dom.getElementsByTagName("model")
        for node in nodes:
            status = get_node_text(node.getElementsByTagName("enabled")[0])
            if status != "true": continue # disabled. ignore

            # add nested model file to list of files
            modelfile = get_node_text(node.getElementsByTagName("file")[0])
            models.append(os.path.join(dirname,modelfile))
        del(nodes)

        # detect agents
        nodes = dom.getElementsByTagName("xagent")
        for node in nodes:
            # get agent name
            aname = get_node_text(node.getElementsByTagName("name")[0])
            varlist = []
            vars = node.getElementsByTagName("variable")
            # get list of agent memory vars
            for var in vars:
                varlist.append(get_node_text(var.getElementsByTagName("name")[0]))
            del(vars)

            # remove array brackets
            for i in range(len(varlist)):
                v = varlist[i]
                if "[" in v: varlist[i] = v[:v.index("[")]

            # add agent data to out list
            if aname in agents.keys(): # agent already exist. Merge
                for v in varlist:
                    if v not in agents[aname]: agents[aname].append(v)
            else: # new agent
                agents[aname] = varlist
        del(nodes)

        # finished parsing this file
        del(dom)

    # Create db tables
    print(" - Initialising database structure")
    print("   + creating table : _iters_")
    db.execute("BEGIN;")
    db.execute("CREATE TABLE _iters_ (itno)") # metadata table
    for a in agents: # agent data tables
        sql = "CREATE TABLE {0} (_ITERATION_NO,{1})".format(a, ",".join(agents.get(a)))
        print("   + creating table : {0}".format(a))
        db.execute(sql)
    db.execute("END;")

    # Finally, load data from *.xml files
    print(" - Importing snapshot data into database")
    for i in iters:
        db.execute("BEGIN;")
        load_iteration_file(i, itsdir, db)
        db.execute("END;")

    # Done!
    print(" - DONE. Output file : {0}".format(outfile))
    print("")

    # close db
    db.commit()
    db.close()
