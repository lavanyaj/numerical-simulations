from sperc_simulator import *
import numpy as np
import argparse

"""
how to run custom simulation
 python files_to_run/dynamic_simulator.py --link_filename test-fully_connected-10-links.txt --flow_filename test-fully_connected-10-400flows-change4.txt --max_microseconds 10000
 then python files_to_run/get_convergence_times.py --filename results/*flow-rates*txt
"""
def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

parser = argparse.ArgumentParser(description="arguments to dynamic simulator")
parser.add_argument("--seed_link_delay", type=int, help="seed for link delay")
parser.add_argument("--seed_drop", type=int, help="seed for drops")
parser.add_argument("--seed_start_timeout", type=int, help="seed for when to start maxe timeouts")
parser.add_argument("--link_filename", type=str, help="filename containing link config") #, default="links_file.txt")
parser.add_argument("--flow_filename", type=str, help="filename containing flow events") #, default="dep_chain.txt")
parser.add_argument("--log",type=str2bool, help="detailed logs",default=False)
parser.add_argument("--warn_if_infeasible",type=str, nargs='+', help="one or more of msg_min_alloc, source_actual_rate",default=["msg_min_alloc","source_latest_min_alloc"])
parser.add_argument("--alg",type=str,help="sperc|sperc_basic|naive|perc|cpg|skivee|sperc_ignore|sperc_robust")
parser.add_argument("--lookup_hint_maxflows",type=int,help="hint for lookup table") #, default=0)
parser.add_argument("--lookup_hint_err",type=str,help="hint for lookup table") #, default=0)
parser.add_argument("--log_dir_path",type=str,help="e.g., prefix for log files containing per-flow rates, link utilization etc.")

args = parser.parse_args()


###################### Global constants ########################
sim_next_flow = None

sim_log = args.log
prng_link_delay=np.random.RandomState(args.seed_link_delay)
prng_drop=np.random.RandomState(args.seed_drop)
prng_start_timeout=np.random.RandomState(args.seed_start_timeout)
# used by simulator of generating small noise in delay at each link per packet



sim_nlinks = None
sim_longest_rtt = None
sim_shortest_rtt = None
sim_max_microseconds = None
sim_prec=None
sim_waterfilling_eps= None
sim_alg_link_warn_eps=None
# used to check rates and demands from alg
sim_convergence_threshold= None
sim_check_rates_interval = None
sim_link_delay = None
sim_link_delay_noise = None 
sim_max_consecutive_converged = None
sim_frugal_timeout = None
sim_lookup_table = None
sim_N = None
sim_m = None
sim_l = None
sim_drop_probability = None
sim_frugal_rto = None
c = None

################################################################


def setup_sim_from_file():
    global sim_nlinks
    global c
    global sim_link_delay
    global sim_shortest_rtt
    global sim_longest_rtt
    global sim_check_rates_interval
    global sim_frugal_timeout
    global sim_max_microseconds  
    global sim_prec
    global sim_waterfilling_eps 
    global sim_alg_warn_eps
    global sim_convergence_threshold
    global sim_alg_link_eps
    global sim_link_delay_noise   
    global sim_max_consecutive_converged  
    global sim_lookup_table  
    global sim_N  
    global sim_m  
    global sim_l  
    global sim_drop_probability
    global sim_frugal_rto

    link_index = 0
    with open(args.link_filename) as f:
        for line in f:
            if line.startswith("nlinks"):
                sim_nlinks = int(line.split()[1])
                print "sim_nlinks %d"%(sim_nlinks)
                c = np.ones((sim_nlinks, 1), dtype=float)
            elif line.startswith("link_delay "):
                sim_link_delay = float(line.split()[1])
                print "sim_link_delay %f"%(sim_link_delay)
            elif line.startswith("shortest_rtt"):                
                sim_shortest_rtt = float(line.split()[1])
                print "sim_shortest_rtt %f"%(sim_shortest_rtt)
            elif line.startswith("longest_rtt"):
                sim_longest_rtt = float(line.split()[1])
                print "sim_longest_rtt %f"%(sim_longest_rtt)
            elif line.startswith("check_rates_interval"):
                sim_check_rates_interval = float(line.split()[1])
                print "sim_check_rates_interval %f"%(sim_check_rates_interval)
            elif line.startswith("frugal_timeout"):
                sim_frugal_timeout = float(line.split()[1])
                print "sim_frugal_timeout %f"%(sim_frugal_timeout)
            elif line.startswith("max_microseconds"):
                sim_max_microseconds = float(line.split()[1])
                # default 10,000
                print "sim_max_microseconds %f"%(sim_max_microseconds)
            elif line.startswith("lookup_table"):
                sim_lookup_table = True
                tokens = [t for t in line.split()[1:]]
                str_N = tokens[0]
                assert (str_N == "N")
                sim_N = int(tokens[1])
                str_l = tokens[2]
                sim_l = int(tokens[3])
                assert (str_l == "l")
                str_m = tokens[4]
                sim_m = int(tokens[5])
                assert (str_m == "m")
                print "lookup_table %s N %d l %d m %d" % (str(sim_lookup_table), sim_N, sim_l, sim_m)
                # default 32, 6, 9
            elif line.startswith("exact"):
                sim_lookup_table = False
                sim_N = 0
                sim_l = 0
                sim_m = 0
                print "exact lookup_table %s N %d m %d l %d" % (str(sim_lookup_table), sim_N, sim_l, sim_m)
            elif line.startswith("prec"):
                tokens = [float(f) for f in line.split()[1:]]
                sim_prec = int(tokens[0])
                sim_waterfilling_eps = tokens[1]
                sim_alg_warn_eps = tokens[2]
                sim_convergence_threshold = tokens[3]
                sim_alg_link_eps = tokens[4]

                print "prec %d wf eps %.12f warn eps %.12f convergence eps %.12f link eps %.12f"%\
                    (sim_prec, sim_waterfilling_eps,\
                     sim_alg_warn_eps, sim_convergence_threshold, sim_alg_link_eps)
            elif line.startswith("link_delay_noise "):
                tokens = line.split()[1:]
                sim_link_delay_noise = (float(tokens[0]), float(tokens[1]))
            elif line.startswith("max_consecutive_converged"):
                sim_max_consecutive_converged = int(line.split()[1])
                print "max consecutive converged (is used) %d" % sim_max_consecutive_converged
            elif line.startswith("drop_probability"):
                tokens = line.split()[1:]
                sim_drop_probability = float(tokens[0])
                print "drop probability is %g" % sim_drop_probability
            elif line.startswith("frugal_rto"):
                tokens = line.split()[1:]
                sim_frugal_rto = float(tokens[0])
            elif line.rstrip():
                link_rate = float(line.split()[0])
                print "link %d has capacity %f"%(link_index, link_rate)
                c[link_index] = link_rate
                link_index += 1
                pass
            else:
                print "couldn't parse empty line"
                pass
        pass

    pass


def parseWords(words, flows_to_start,\
               flows_to_stop):

    global sim_next_flow
    addFlow = int(words[1])
    if addFlow == 1:
        flowId = int(words[2])
        assert(flowId == sim_next_flow)
        numLinks = int(words[3])
        assert(sim_nlinks == numLinks)
        path = np.zeros((numLinks),\
                        dtype=float)        
        for index in words[4:]:
            path[int(index)] = 1
            pass
        flows_to_start[sim_next_flow] = path
        sim_next_flow += 1
        pass
    else:
        flowId = int(words[2])
        flows_to_stop[flowId] = True
        pass
    return

def main_from_file():
    assert(len(args.link_filename) > 0)
    setup_sim_from_file()

    assert not(args.lookup_hint_maxflows == 10000)
    alg = args.alg
    assert alg == "sperc_basic" or alg == "perc" or alg == "naive" or alg == "sperc_ignore" or alg == "cpg" or alg == "skivee" or alg == "sperc_robust"
    """ 
    settings_str = ""
    if (alg == "sperc_basic" or alg == "sperc_ignore" or alg == "sperc_robust"):
        settings_str= "timeout%dus-"%(sim_frugal_timeout)
        if (sim_N > 0):
            settings_str += "lookup-N%d-l%d-m%d-c%d-f%d-e%d"% % (sim_N, sim_l, sim_m, int(max(c.values()), args.hint_lookup_maxflows, args.hint_lookup_err)
        else:
            settings_str += "exact"
            pass
        pass
    """    
    assert(sim_convergence_threshold > 1e-14)
    assert(sim_waterfilling_eps > 1e-14)

    sim = Simulator(c=c, link_delay=sim_link_delay, delay_noise=sim_link_delay_noise,\
                    alg=alg, instance_num=-1,\
                    prng_link_delay=prng_link_delay,\
                    prng_drop=prng_drop,\
                    prng_start_timeout=prng_start_timeout,\
                    flow_filename=args.flow_filename,\
                    link_filename=args.link_filename,\
                    prec=sim_prec,waterfilling_eps=sim_waterfilling_eps,\
                    convergence_threshold=sim_convergence_threshold,\
                    alg_link_warn_eps=sim_alg_warn_eps,\
                    alg_link_link_eps=sim_alg_link_eps,\
                    log=sim_log,\
                    check_rates_interval=sim_check_rates_interval,\
                    max_consecutive_converged=sim_max_consecutive_converged,\
                    frugal_timeout=sim_frugal_timeout, warn_if_infeasible=args.warn_if_infeasible,\
                    drop_probability=sim_drop_probability, frugal_rto=sim_frugal_rto,\
                    lookup_params={"N":sim_N, "l":sim_l, "m": sim_m,\
                                   "c": int(float(np.max(c))), "f": args.lookup_hint_maxflows,\
                                   "err": args.lookup_hint_err},\
                   # for logging
                    seed_link_delay=args.seed_link_delay,\
                    seed_drop=args.seed_drop,\
                    seed_start_timeout=args.seed_start_timeout,\
                    log_dir_path=args.log_dir_path)
    # prec is number of digits of precision to use in ideal waterfilling 
    #filename = args.filename
    # we initialize simulator with just the links
    # event queue is also set up at this point

    global sim_next_flow
    sim_next_flow = 0

    lastLine = None
    lastFlowTime = None
    flows_to_start = {}
    flows_to_stop = {}
    flows_started = {}

    newEvents = False
    with open(args.flow_filename) as f:
        while True:
            if len(flows_to_start) == 0 or len(flows_to_stop) == 0:
                print "flows to start / stop is 0, looking for new flows to start / stop"
                if lastLine is not None:
                    print "parse lastLine %s"%lastLine
                    parseWords(lastLine.split(), flows_to_start, flows_to_stop)
                    newEvents = True
                    lastLine = None
                    pass
                for line in f:
                    if line.startswith("#"): continue                    
                    words = line.split()
                    flowTime = int(words[0])
                    if lastFlowTime == None:
                        lastFlowTime = flowTime
                    elif flowTime != lastFlowTime:
                        lastLine = line
                        lastFlowTime = flowTime
                        break            
                    print "parse line %s"%(line)
                    parseWords(words, flows_to_start,\
                               flows_to_stop)
                    print "lastFlowTime %s"%(str(lastFlowTime))
                    newEvents = True
                    pass
                pass


            if len(flows_to_start) > 0:
                print ("starting %s"%\
                       sorted(flows_to_start.keys()[:5]))

                for flow in flows_to_start:
                    flows_started[flow]\
                        = flows_to_start[flow]
                    pass
                sim.setup_flows\
                    (new_flows=flows_to_start,\
                     relative_start_time=0)
                flows_to_start = {}
                pass

            # if len(flows_to_stop) == 0:
            #     print "flows_to_stop is 0, looking for new flows to stop"
            #     if lastLine is not None:
            #         print "parse lastLine %s"%lastLine
            #         parseWords(lastLine.split(), flows_to_start, flows_to_stop)
            #         newEvents = True
            #         lastLine = None
            #         pass
            #     for line in f:
            #         if line.startswith("#"): continue
            #         words = line.split()
            #         flowTime = int(words[0])
            #         if lastFlowTime == None:
            #             lastFlowTime = flowTime
            #         elif flowTime != lastFlowTime:
            #             lastLine = line
            #             lastFlowTime = flowTime
            #             break            
            #         print "parse line %s"%line
            #         print "lastFlowTime %s"%(str(lastFlowTime))
            #         parseWords(words,\
            #                    flows_to_start,\
            #                    flows_to_stop)
            #         newEvents = True
            #         pass
            #     pass
        
            if len(flows_to_stop) > 0:
                print ("stopping %s"%\
                       sorted(flows_to_stop.keys()[:5]))
                sim.stop_flows(flows_to_stop, 0)
                for flow in flows_to_stop:
                    del flows_started[flow]        
                    pass
                flows_to_stop = {}
                pass

            if not newEvents:
                print "no more new events.\n"
                print lastLine
                print lastFlowTime
                break
                        
            sim.instance_num += 1
            sorted_active_flows = sorted(flows_started.keys())
            print ("%d sorted active flows"%len(sorted_active_flows))
            A = flows_started[sorted_active_flows[0]]
            for flow_id in sorted_active_flows[1:]:
                A = np.vstack((A, flows_started[flow_id]))
            curr_time = sim.event_queue.get_last_time()
            print "setting up max min helper"
            sim.setup_maxminhelper(A=A, curr_time=curr_time, max_microseconds=sim_max_microseconds)
            print "max min nhelper done"
            sim.unique_id = sim.sim_id + "-" + str(sim.instance_num)
            sim.run_for_duration(sim_max_microseconds)
            newEvents = False
            sim.teardown_maxminhelper()
            sim.reset_logfiles()

            print "# Simulated events from " + str(sim.run_start_time)\
                + " us to " + str(sim.run_end_time) + " ( " + str(sim_max_microseconds) + " us)"\
                + " convergence_run: " + str(sim.convergence_run)


            pass
        pass
        
    return

if __name__ == "__main__":
    main_from_file()
