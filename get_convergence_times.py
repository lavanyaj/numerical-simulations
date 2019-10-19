#from utils import *
import numpy as np
import pandas as pd
import argparse
import sys


"""
how to use to get CT results
python files_to_run/get_convergence_times.py --filename results/*flow-rate*txt
"""
# for robustness expriments, we used
# [0.001, 0.01, 0.1, 0.2, 0.3, 0.5]
thresholds = [0.01] #[x * 0.1 for x in range(10)] 
parser = argparse.ArgumentParser()
parser.add_argument("--input_files", type=str, nargs='+', help="CSV file of link rates")
parser.add_argument("--stdin", action="store_true")
parser.add_argument("--thresholds", type=float, nargs='+', help="thresholds for convergence", default=[0.01])
args = parser.parse_args()

def get_filename(prefix):
    return args.result_filename
    pass

def get_headers():
    return "filename," + "cpg1, cpg2, wf, max_rtt, distinct," + ",".join(["convergence_time-%d, converged_for-%s, last_time_over_index-%s, convergence_row-%s"\
                     % (t*100, t*100, t*100, t*100) for t in thresholds])

def get_convergence_times(filename,stdin):
    run_id = filename.split("/")[-1]
    maxCpg1Level = -1
    maxCpg2Level = -1
    maxWfLevel = -1
    maxRtt = -1
    distinctOptimalRates = -1
    with open(filename) as f:
        for line in f:
            if line.startswith("# maxCpg1Level"):
                maxCpg1Level = int(line.rstrip().split()[-1])
                pass
            if line.startswith("# maxCpg2Level"):
                maxCpg2Level = int(line.rstrip().split()[-1])
                pass
            if line.startswith("# maxWfLevel"):
                maxWfLevel = int(line.rstrip().split()[-1])
                pass

            if line.startswith("# maxRtt"):
                maxRtt = float(line.rstrip().split()[-1])
                pass                
            if line.startswith("# distinctOptimalRates"):
                distinctOptimalRates = int(line.rstrip().split()[-1])
                pass                

            pass
        pass

    if stdin:
        df = pd.read_csv(sys.stdin, header='infer', comment='#')
    else:
        df = pd.read_csv(filename, header='infer', comment='#')
        pass

    num_columns = df.shape[1]
    #print df.columns.values.tolist()

    df['Time'] = pd.to_datetime(df["time(us)"], unit='us')
    #df['Time'] = pd.to_datetime(df['Time'], unit='us')
    df.index = df['Time']
    del df['Time']
    
    last_time = -1    
    relative_errs= df.select(lambda col: col.startswith('RelErr'), axis=1)
    relative_errs.index = df.index

    abs_relative_errs = relative_errs.apply(abs, axis=1)
    abs_relative_errs.index = relative_errs.index
    #print "shape of abs_relative_errs: %s" % (str(abs_relative_errs.shape))
    
    max_relative_errs = abs_relative_errs.apply(max, axis=1)
    max_relative_errs.index = abs_relative_errs.index
    #print "shape of max_relative_errs: %s" % (str(max_relative_errs.shape))

    # print "index of max abs"
    max_relative_errs_index = abs_relative_errs.idxmax(axis=1)
    #print "shape of max_relative_errs_index: %s" % (str(max_relative_errs_index.shape))
    num_rows = max_relative_errs.shape[0]

    convergence_durations = []
    convergence_times = []
    convergence_row = []

    convergence_time_index = []
    last_time_over = []
    last_time_over_index = []

    for t in thresholds:
        last_time_over.append(-1)
        convergence_time_index.append(-1)
        last_time_over_index.append(-1)

    start_time = pd.to_datetime(0)
    last_time = max_relative_errs.index[num_rows-1]

    # for each threshold: we store last row when the max relative
    # error (out of all flows' relative errors) exceeded the threshold
    # and we also store the argmax (or "index"). convergence_time
    # stores tentative row when rel errors converged to within threshold
    # (tentative because we might encounter a row later, when rel err
    # is more than threshold)
    # if last_time_over is -1, that means max relative error was 
    # always <= threshold
    for i in range(num_rows):
        val = max_relative_errs[i]
        for t in range(len(thresholds)):
            if val > thresholds[t]:
                last_time_over[t] = i
                convergence_time_index[t] = i+1
                last_time_over_index[t] = max_relative_errs_index[i]
            #print "row %d, threshold %f, max_relative_err %f"%(i, thresholds[t], val)

    for t in range(len(thresholds)):
        ct_index = convergence_time_index[t]
        ct = -1
        cd = -1
        # convergence time: last time before the experiment end when
        # a flow's relative error exceeded the threshold (-1 implies
        # all flows had relative errors within threshold for duration of
        # experiment). convergence: duration: how long since a
        # flow's relative error exceeded the threshold
        if ct_index < num_rows:
            ct = (max_relative_errs.index[ct_index]-start_time).microseconds
            cd = (last_time-max_relative_errs.index[ct_index]).microseconds
            if maxRtt > 0:
                ct = ct
                cd = cd
        convergence_times.append(ct)
        convergence_durations.append(cd)
        convergence_row.append(ct_index)

    return run_id + ", " + str(maxCpg1Level) +", " + str(maxCpg2Level) + ", " + str(maxWfLevel)\
        + ", " + "%.1f"%maxRtt\
        + ", " + "%d"%distinctOptimalRates\
        + ", " + ",".join(["%s, %s, %s, %s"\
                           % (str((convergence_times[t])),\
                              str((convergence_durations[t])),\
                              str(last_time_over_index[t]),\
                              str(convergence_row[t]))\
                           for t in range(len(thresholds))])
   

if (args.stdin):
    assert(len(args.filename) == 1)

print get_headers()
for filename in args.input_files:
    print "%s"%(get_convergence_times(filename, stdin=args.stdin))
    pass
    
