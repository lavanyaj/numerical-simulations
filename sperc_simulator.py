import time
import sys
import skivee_sim
import sperc_robust_sim
import sperc_ignore_sim
import sperc_basic_sim
import perc_sim
import naive_sim





from event_queue import *
from max_min_helper import *
from collections import deque
import numpy as np
import div_impl
from prec_library import PrecisionLibrary

class Simulator:
    def __init__(self, alg, c, link_delay, delay_noise,  instance_num, prng_link_delay, prng_drop, prng_start_timeout,\
                 flow_filename, link_filename, prec, waterfilling_eps, convergence_threshold,\
                 alg_link_warn_eps, alg_link_link_eps, log, check_rates_interval, max_consecutive_converged,\
                 frugal_timeout, warn_if_infeasible, drop_probability, frugal_rto, seed_link_delay,\
                 lookup_params, seed_drop, seed_start_timeout, log_dir_path):
        assert(prng_link_delay is not None)
        assert(prng_drop is not None)
        assert(prng_start_timeout is not None)
        self.seed_link_delay = seed_link_delay
        self.seed_drop = seed_drop
        self.seed_start_timeout = seed_start_timeout
        self.alg_lib = {"sperc_basic": sperc_basic_sim,\
                        "perc": perc_sim, "naive": naive_sim,\
                        "sperc_ignore": sperc_ignore_sim,\
                        "sperc_robust": sperc_robust_sim,\
                        "skivee": skivee_sim}
        self.log_dir_path = log_dir_path
        self.sim_id = self.log_dir_path.split("/")[-1]
        self.alg = alg
        assert alg in self.alg_lib
        
        
        
        self.frugal_timeout = frugal_timeout
        self.finished_flows = deque()
        self.run_start_time = -1
        self.run_end_time = -1
        self.dur_rtts = -1
        self.run_start_events = -1
        self.run_end_events = -1        
        self.log_all_flows_file = None
        self.log_all_links_rate_file = None
        self.log_all_links_rate_detailed_file = None
        
        self.first_rate_log = True
        self.log_link_utilization_file = {}
        self.drop_probability = drop_probability
        self.frugal_rto = frugal_rto

        self.prng_link_delay = prng_link_delay
        self.prng_drop = prng_drop
        self.prng_start_timeout = prng_start_timeout
        self.prec_library = PrecisionLibrary(prec=prec, eps1=waterfilling_eps, eps2=convergence_threshold, eps3=alg_link_warn_eps, eps4=alg_link_link_eps)
        self.c = c
        self.link_delay = link_delay
        self.delay_noise = delay_noise
        self.log = log
        self.check_rates_interval = check_rates_interval
        self.max_consecutive_converged = max_consecutive_converged
        assert(self.max_consecutive_converged > 0)

        self.num_links = c.shape[0]
        self.num_flows = 0
        self.instance_num = instance_num

        self.levels = np.ones(self.num_links) * 100000 # assuming we'll never have this many links)
        self.init_realtime = time.time()
        self.link_objects = {}

        self.last_progress_log_rtt = 0
        self.last_errors_log_us = 0
        self.last_link_utilization_log_rtt = 0
        self.num_drops = 0

        self.convergence_threshold = self.prec_library.eps2
        self.convergence_run = False
        self.c = c
        self.lookup_params = lookup_params
        
        for i in range(self.num_links):
            self.link_objects[i] = self.alg_lib[self.alg].Link() #SPERCLink()
            self.link_objects[i].set_capacity(c[i, 0])
            self.link_objects[i].id_ = i
            # s-PERC "ignore" uses epsilon for inequality comparisons, default 1e-7
            if hasattr(self.link_objects[i], 'set_epsilon'):
                self.link_objects[i].set_epsilon(self.prec_library.eps4)
                if i == 0: print("link "+str(i)+" has eps " + str(self.link_objects[i].eps))
        assert(self.link_objects[0].alg == self.alg)
        if lookup_params['N'] > 0:
            div_impl.initialize(divN=lookup_params['N'], divl=lookup_params['l'], divm=lookup_params['m'])
            
            assert(self.alg in ['sperc_ignore', 'sperc_basic', 'sperc_robust'])
            for i in range(self.num_links):
                self.link_objects[i].use_approx_div(N=lookup_params['N'],\
                                                    l=lookup_params['l'],\
                                                    m=lookup_params['m'],\
                                                    cap_range=(1e-5, lookup_params['c']),\
                                                    max_flows=lookup_params['f'])
                pass
            pass
        
        self.event_queue = EventQueue()
        self.time_granularity = "microseconds"

        # they can start at different times
        for i in range(self.num_links):
            delay_start_timeout = (self.prng_start_timeout.random_sample()+1) * self.frugal_timeout
            self.event_queue.schedule("reset max_sat at %d"%i,\
                                      delay=delay_start_timeout)
            
        self.source_objects = {}
        self.destination_objects = {}
        self.message_objects = {}

        self.ideal_active_flows = {} # updated as soon as flows are scheduled to be start/stop with delay=0
        self.paths = {} # update as soon as flows are schedule to be started or when their messages are stopped
        self.flow_filename = flow_filename
        self.link_filename = link_filename
        self.warn_if_infeasible = warn_if_infeasible
        
        return

    def check_rates(self, curr_time):


        
        ideal_active_flows = sorted(self.ideal_active_flows.keys())
        flow_num = 0
        self.flow_num_to_flow_id = {}
        self.flow_id_to_flow_num = {}
        for flow_id in ideal_active_flows:
            if flow_id not in self.source_objects:
                print >> sys.stderr, "WARNING: ideal active flow " + str(flow_id) + " not set up yet, in check_rates"
                continue            
            self.source_objects[flow_id].set_time(curr_time)
            self.flow_num_to_flow_id[flow_num] = flow_id
            self.flow_id_to_flow_num[flow_id] = flow_num
            flow_num += 1

        for link_id in range(self.num_links):
            self.link_objects[link_id].set_time(curr_time)
            self.link_objects[link_id].set_time_us(curr_time*self.longest_rtt)

        now_rtts = ((1.0*(self.event_queue.get_last_time() - self.run_start_time))/self.longest_rtt)

        now_us = self.event_queue.get_last_time() - self.run_start_time
        if (now_us - self.last_errors_log_us) >= self.longest_rtt * 0.25 * 1.0001:
            self.last_errors_log_us = now_us
            self.log_all_flows("AllFlowRates")
            self.log_all_links("AllLinkRates")
            
        preface = "MaxMinLinkUtilization"
        now_rtts = ((1.0*(self.event_queue.get_last_time() - self.run_start_time))/self.longest_rtt)


    def get_filename(self, suffix):
        return ("%s-%s"%(self.log_dir_path, suffix))

    
    def reset_logfiles(self):
        # we compare time since run start with last errors log rtt
        # when we reset run start, should also reset this
        self.last_progress_log_rtt = 0
        self.last_errors_log_us = 0
        self.last_link_utilization_log_rtt = 0
        self.num_drops = 0

        self.log_all_flows_file = None
        self.log_all_links_rate_file = None
        self.log_all_links_rate_detailed_file = None
        self.log_link_utilization_file = {}

    def log_all_links(self, preface):
        assert(self.convergence_run)

        if  self.log_all_links_rate_file is None:      
            self.log_all_links_rate_file = self.get_filename("link-rates")
            self.log_all_links_rate_detailed_file = self.get_filename("link-rates-detailed")
            print("writing to", self.log_all_links_rate_file, self.log_all_links_rate_detailed_file)

            with open(self.log_all_links_rate_detailed_file, "w") as fd:
                with open(self.log_all_links_rate_file, "w") as f:

                    comment = "# link rate" + preface + ", " + self.sim_id
                    num_bottleneck_links = 0

                    f.write("time(us), time(RTTs),")
                    fd.write("time(us), time(RTTs),")
                    for linkId in range(self.wf_maxmin.num_links):
                        linkKey = "%d"%linkId
                        optimalRate = float(self.wf_maxmin.maxmin.r[linkId])
                        if optimalRate < float('inf'):
                            f.write("Actual-Link%s"%linkKey+",Optimal-Link%s"%linkKey+",ActualMaxE-Link%s"%linkKey)
                            fd.write("Actual-Link%s"%linkKey+",Optimal-Link%s"%linkKey+",MaxE-Link%s"%linkKey+",ActualMaxE-Link%s"%linkKey+",RateForB-Link%s"%linkKey)
                            f.write(",")
                            fd.write(",")
                            pass
                        num_bottleneck_links +=1
                        pass
                    f.write("\n")
                    fd.write("\n")
                    comment += ", " + str(num_bottleneck_links) + " bottleneck links"
                    f.write(comment)
                    f.write("\n")
                    fd.write(comment)
                    fd.write("\n")
                    pass # with open
                pass # with open
            pass # if ..file is None

        time_since_start = self.event_queue.get_last_time() - self.run_start_time        
        assert(self.instance_num >= 0)
            
        with open(self.log_all_links_rate_detailed_file, "a") as fd:
            with open(self.log_all_links_rate_file, "a") as f:
                f.write(str(time_since_start) + "," + str(time_since_start/self.longest_rtt) + ",")
                fd.write(str(time_since_start) + "," + str(time_since_start/self.longest_rtt) + ",")

                for linkId in range(self.wf_maxmin.num_links):
                    link_state = self.link_objects[linkId].get_local_state()

                    if self.alg in ["sperc_basic", "naive", "sperc_ignore", "sperc_robust"]:
                        if (float(link_state["num_b"]) == 0): actualRate = float('inf')
                        else: actualRate = (self.link_objects[linkId].capacity - float(link_state["sum_e"]))/float(link_state["num_b"])
                        actualMaxE = float(link_state["actual_max_e"])
                        maxE = float(link_state["max_e"])
                        rateForB = float(link_state["last_bottleneck_rate_for_b_flow"])
                    elif self.alg in ["perc"]:
                        actualRate = link_state["bottleneck_rate"]
                        actualMaxE = link_state["max_e"]
                        maxE = actualMaxE
                        rateForB = actualRate
                    elif self.alg in ["skivee"]:
                        actualRate = link_state["rho"]
                        actualMaxE = link_state["max_e"]
                        maxE = actualMaxE
                        rateForB = actualRate
                        pass
                    optimalRate = float(self.wf_maxmin.maxmin.r[linkId])

                    if (actualRate == float('inf')): actualRate = -1
                    if (maxE == float('inf')): maxE = -1
                    if (actualMaxE == float('inf')): actualMaxE = -1
                    if (rateForB == float('inf')): rateForB = -1

                    if optimalRate < float('inf'):
                        fd.write(",".join([str(val) for val in [actualRate, optimalRate, maxE, actualMaxE, rateForB]]))
                        f.write(",".join([str(val) for val in [actualRate, optimalRate, actualMaxE]]))
                        f.write(",")
                        fd.write(",")
                        pass
                    pass # for linkId

                f.write("\n")
                fd.write("\n")
                pass # with open
            pass # with open
        pass
        
    def log_all_flows(self, preface):
        assert(self.convergence_run)
        all_flows = sorted(self.ideal_active_flows.keys())

        if  self.log_all_flows_file is None:      
            self.log_all_flows_file = self.get_filename("flow-rates")
            print("writing to", self.log_all_flows_file)

            with open(self.log_all_flows_file, "w") as f:
                comment = "# " + preface + ", " + self.sim_id + ", Time (us), Rates (b/s)"                
                maxCpg2Level=0
                maxCpg1Level=0
                f.write("time(us), time(RTTs),")
                
                for flowId in all_flows:
                    assert(flowId in self.flow_id_to_flow_num)
                    flowNum = self.flow_id_to_flow_num[flowId]

                    cpg2Level = self.wf_maxmin.cpg_maxmin.flow_levels[flowNum]
                    maxCpg2Level=max(maxCpg2Level, cpg2Level)

                    cpg1Level = self.wf_maxmin.cpg_maxmin1.flow_levels[flowNum]
                    maxCpg1Level=max(maxCpg1Level, cpg1Level)

                    bottleneckLink = self.wf_maxmin.cpg_maxmin.flow_bottlenecks[flowNum]
                    flowKey = "%d-%d-%d"%(flowNum, cpg1Level, bottleneckLink)
                    f.write("Actual-Flow%s"%flowKey+",Optimal-Flow%s"%flowKey+",RelErr-Flow%s"%flowKey)
                    f.write(",")
                f.write("\n")
                f.write(comment)
                f.write("\n")
                f.write("# maxCpg1Level %d\n" % maxCpg1Level)
                f.write("# maxCpg2Level %d\n" % maxCpg2Level)                
                f.write("# maxWfLevel %d\n" % self.wf_maxmin.maxmin.level)
                f.write("# maxRtt %f\n" % self.longest_rtt)            
            pass # with open(..


        
        time_since_start = self.event_queue.get_last_time() - self.run_start_time
        rtts_since_start = time_since_start/self.longest_rtt

        assert(self.instance_num >= 0)
        with open(self.log_all_flows_file, "a") as f:
            distinct_optimal_rates = {}
            f.write(str(time_since_start) + "," + str(rtts_since_start) + ",")
            for flowId in all_flows:
                assert(flowId in self.flow_id_to_flow_num)
                flowNum = self.flow_id_to_flow_num[flowId]
                assert(flowId in self.source_objects)
                actualRate = self.source_objects[flowId].get_last_min_alloc()
                optimalRate = float(self.wf_maxmin.maxmin.x[flowNum])                
                if self.first_rate_log:
                    distinct_optimal_rates["%.5f"%optimalRate] = True
                
                relDiffRate = self.get_relative_diff(actualRate, optimalRate)
                if relDiffRate == self.prec_library.mpf_inf:
                    print >> sys.stderr, "WARNING: actual rate is of flow", flowId, " at ",
                    self.event_queue.get_last_time(), " is ", actualRate
                    " and optimal rate is ", optimalRate, " so difference is ",\
                        relDiffRate, "( inf is ", self.prec_library.mpf_inf, ")"
                    pass
                f.write(",".join([str(val) for val in [actualRate, optimalRate, relDiffRate]]))
                f.write(",")
                pass
            f.write("\n")
            if self.first_rate_log:
                f.write("# distinctOptimalRates %d\n" % len(distinct_optimal_rates))
                self.first_rate_log = False
                pass
            pass # with open
        return

    def get_relative_diff(self, actualRate, optimalRate):
        relDiffRate = None
        if (actualRate == self.prec_library.mpf_inf and optimalRate == self.prec_library.mpf_inf):
            absDiffRate = self.prec_library.zero
            relDiffRate = self.prec_library.zero
        elif (actualRate == self.prec_library.mpf_inf):
            relDiffRate = self.prec_library.mpf_inf
            assert(False)
        elif (optimalRate == self.prec_library.mpf_inf):
            relDiffRate = -1
            assert(False)
        else:
            diffRate = (actualRate - optimalRate)
            if optimalRate > 0:
                relDiffRate = diffRate/optimalRate
            elif optimalRate == 0 and actualRate == 0:
                relDiffRate = 0
            else:
                relDiffRate = 0

        assert(self.prec_library.mpf_inf > 0)            
        return relDiffRate

    def log_link_utilization_detailed(self, preface):
        assert(self.convergence_run)
        for flow_rate_type in self.wf_maxmin.flow_rate_types:
            self.log_link_utilization_detailed_type(preface, flow_rate_type)
            pass

    def log_link_utilization_detailed_type(self, preface, flow_rate_type):
        assert(self.convergence_run)
        time_since_start = self.event_queue.get_last_time() - self.run_start_time        
        if flow_rate_type not in self.log_link_utilization_file:
            self.log_link_utilization_file[flow_rate_type]\
                = self.get_filename("link-utilization-%s"%flow_rate_type)
            print("writing to", self.log_link_utilization_file)

            with open(self.log_link_utilization_file[flow_rate_type], "w") as f:
                comment = "# link utilization" + preface + ", " + self.sim_id                
                f.write(flow_rate_type + ",time(us), time(RTTs),")
                for linkId in range(self.wf_maxmin.num_links):
                    linkKey = "%d"%linkId
                    f.write("ActualUtil-Link%s"%linkKey+",OptimalUtil-Link%s"%linkKey\
                            +",RelErrUtil-Link%s"%linkKey\
                            +",FracErrUtil-Link%s"%linkKey)
                    f.write(",")
                    pass
                f.write("\n")
                f.write(comment)
                f.write("\n")
                pass # with open

        time_since_start = self.event_queue.get_last_time() - self.run_start_time
        with open(self.log_link_utilization_file[flow_rate_type], "a") as f:
            f.write(flow_rate_type + "," + str(time_since_start) + ",")
            f.write(str(time_since_start/self.longest_rtt) + ",")

            for linkId in range(self.num_links):
                actualUtil = self.wf_maxmin.link_utilization_abs[flow_rate_type][linkId]
                optimalUtil = float(self.wf_maxmin.maxmin.utilization[linkId])
                maxUtil = self.c[linkId,0]
                if optimalUtil < 0:
                    print >> sys.stderr, "WARNING: optimal util of link", linkId, " at ",
                    self.event_queue.get_last_time(), " is ", optimalUtil
                    assert(optimalUtil >= 0)

                relErrUtil = self.get_relative_diff(actualUtil, optimalUtil)
                if relErrUtil == self.prec_library.mpf_inf:
                    print >> sys.stderr, "WARNING: actual util of link", linkId, " at ",
                    self.event_queue.get_last_time(), " is ", actualUtil
                    " and optimal util is ", optimalUtil, " so difference is ",\
                        relErrUtil, "( inf is ", self.prec_library.mpf_inf, ")"
                relErrUtil = self.get_relative_diff(actualUtil, optimalUtil)


                fracErrUtil = self.get_relative_diff(actualUtil, maxUtil)
                if fracErrUtil == self.prec_library.mpf_inf:
                    print >> sys.stderr, "WARNING: actual util of link", linkId, " at ",
                    self.event_queue.get_last_time(), " is ", actualUtil
                    " and max util is ", maxUtil, " so difference is ",\
                        fracErrUtil, "( inf is ", self.prec_library.mpf_inf, ")"

                f.write(",".join([str(val) for val in [actualUtil, optimalUtil, relErrUtil, fracErrUtil]]))
                f.write(",")
            assert(self.instance_num >= 0)
            f.write("\n")
            pass # with open
        return

    # sets up source/ destination /message objects, adds flows to active paths
    # schedule flows to start at start_time (relative)
    # new flows is a map from flow ids to an np array of its traffic matrix
    def setup_flows(self, new_flows, relative_start_time):
        print "# setting up " + str(len(new_flows)) + " flows"
        self.num_flows += len(new_flows)        
        unique_paths = {}
        # self.num_links doesn't change
        for flow_id in new_flows:       
            self.ideal_active_flows[flow_id] = True
            self.paths[flow_id] = np.nonzero(new_flows[flow_id])[0]
            path_str = str(self.paths[flow_id])
            if path_str not in unique_paths:
                unique_paths[path_str] = []
            unique_paths[path_str].append(flow_id)
            self.source_objects[flow_id] = self.alg_lib[self.alg].Source() #SPERCSource()
            self.destination_objects[flow_id] = self.alg_lib[self.alg].Destination() #SPERCDestination()
            self.message_objects[flow_id] = self.alg_lib[self.alg].Message() #SPERCMessage()
            self.message_objects[flow_id].id_ = flow_id
            self.message_objects[flow_id].name_ = "%s(%d)"%(path_str,flow_id)
            self.event_queue.schedule_start_flow(flow_id, delay=relative_start_time)
        current_longest_path = 0
        path_lengths = [len(self.paths[flow_id]) for flow_id in self.paths]
        if len(path_lengths) > 0:
            current_longest_path = max(path_lengths)
        self.longest_rtt = self.link_delay * current_longest_path * 2
        
        for path_str in unique_paths:
            print "#", len(unique_paths[path_str]), "flows use path", path_str, ":", str(sorted(unique_paths[path_str][:5])), "..."

        return

    # schedule flows (sources) to stop at stop_time (relative)
    # then after some time check if they have stopped and remove
    # them from active paths
    def stop_flows(self, flows_to_stop, relative_stop_time):
        for flow_id in flows_to_stop:
            del self.ideal_active_flows[flow_id]
            self.event_queue.schedule_stop_flow(flow_id, delay=relative_stop_time)
            # also check that we don't stop flows in the middle
            # of a convergence run     
            self.num_flows -= 1
        self.event_queue.schedule("update paths", delay=2*self.longest_rtt)
        
        return

    # set up max min helper for current set of active flows/ paths
    # and schedule check rates messages
    # make sure no pending start/ stop messages
    def setup_maxminhelper(self, A, curr_time, max_microseconds):
        # wf_maxmin stores flows in sorted order
        print "# setting up maxmin helper using TM of size " + str(A.shape)
        assert(self.instance_num >= 0)
        self.wf_maxmin\
            = MaxMinHelper(A, self.c,\
                           max_consecutive_converged=self.max_consecutive_converged,\
                           prec_library=self.prec_library,
                           instance_num=self.instance_num,\
                           log=self.log)
        assert(max_microseconds > 0)
        end_time = curr_time + max_microseconds
        print ("scheduling check rate to start in %d us, and go on until end_time %d (curr_time %d)" %\
               (self.check_rates_interval, end_time, curr_time))
        self.event_queue.schedule_check_rates\
            (delay=self.check_rates_interval,end_time=end_time)
        self.convergence_run = True
        self.flow_num_to_flow_id = {}
        return

    def teardown_maxminhelper(self):
        self.wf_maxmin = None
        self.convergence_run = False
        self.last_progress_log_rtt = 0
        self.flow_num_to_flow_id = {}
        
    # run events from event queue for dur
    def run_for_duration(self, dur):
        self.run_start_time = self.event_queue.get_last_time()
        self.run_start_events = self.event_queue.get_total_simulated()
        self.run_start_wallclock = time.time()
        prev_ev_time = self.run_start_time
        abs_end_time = self.run_start_time + dur
        self.dur_rtts = dur/self.longest_rtt
        while (self.event_queue.has_events()\
               and prev_ev_time < abs_end_time):
            ev_time, ev_id, ev = self.event_queue.get_next_event()
            curr_time = ev_time/self.longest_rtt
            assert(ev_time >= prev_ev_time)
            prev_ev_time = ev_time
            if ev.startswith("check rates"):
                assert(self.convergence_run)
                self.handle_check_rates_event(curr_time, ev)
            elif ev.startswith("start"):
                self.handle_start_flow_event(curr_time, ev)
            elif (ev.startswith("stop")):
                self.handle_stop_flow_event(curr_time, ev)
            elif (ev.startswith("reset max_sat")):
                self.handle_reset_maxsat_event(curr_time, ev)
            elif (ev.startswith("update paths")):
                self.handle_update_paths_event(curr_time, ev)
            elif (ev.startswith("process")):
                self.handle_process_event(curr_time, ev)
            elif (ev.startswith("retransmit timeout")):
                self.handle_retransmit_timeout_event(curr_time, ev)
            else:
                print >> sys.stderr, "ERROR: don't know how to handle event " + str(ev)
                assert(False)

        self.run_end_events = self.event_queue.get_total_simulated()            
        self.run_end_time = self.event_queue.get_last_time()                
        return

    def handle_process_event(self, curr_time, ev):
        tokens = ev.split()
        assert(tokens[0] == "process")
        flow_id = int(tokens[2])
        hop = int(tokens[5])
        direction = int(tokens[-1])
        source_processed = False
        destination_processed = False
        time_since_start_rtts = (self.event_queue.get_last_time() - self.run_start_time)/self.longest_rtt

        # when hop is path length, we're at destination
        # turn around for next hop
        if (hop == len(self.paths[flow_id])):
            assert(direction == 1)
            self.destination_objects[flow_id].set_time(curr_time)
            self.destination_objects[flow_id].process_forward\
                (self.message_objects[flow_id])
            destination_processed = True
            hop = hop - 1
            direction = -1
            # when hop is -1, we're at source
            # turn around for next hop
        elif (hop == -1):
            assert(direction == -1)
            self.source_objects[flow_id].set_time(curr_time)
            self.source_objects[flow_id].process_reverse\
                (self.message_objects[flow_id])
            source_processed = True
            hop = hop + 1
            direction = 1
            # otherwise we are at a link in flow's path
            # continue in same direction for next hop
        elif (direction == 1):
            assert (hop >= 0)
            if (hop >= len(self.paths[flow_id])):
                print >> sys.stderr, "WARNING: hop is more than length of path " +\
                    str(len(self.paths[flow_id])) +\
                    " " + str(self.paths[flow_id]) +\
                    " for flow " + str(flow_id)
            assert (hop >= 0)
            assert (hop < len(self.paths[flow_id]))

            # hop is the index of the link in the path
            # need to retrieve link_id separately
            link_id = self.paths[flow_id][hop]
            self.link_objects[link_id].set_time(curr_time)
            random_value = self.prng_drop.rand()
            if (random_value < self.drop_probability and time_since_start_rtts < 0.2 * self.dur_rtts):
                self.num_drops += 1
                self.message_objects[flow_id].dropped = True
                self.message_objects[flow_id].dropstr = "drop hop %d link %d fwd time %g %g RTTs from start"%\
                                                        (hop, link_id, curr_time, time_since_start_rtts)
                last_packet_time = -1
                if hasattr(self.source_objects[flow_id], "last_packet_time"):
                    last_packet_time = self.source_objects[flow_id].last_packet_time
                print ("Dropping flow %d, %s msg %s src last_packet_time %s dur %g RTTs" %\
                    (flow_id, self.message_objects[flow_id].dropstr,\
                     self.message_objects[flow_id].name_,\
                     str(last_packet_time), self.dur_rtts))
            else:
                self.link_objects[link_id].process_forward\
                    (self.message_objects[flow_id])
                hop = hop + 1
            # direction unchanged
        else:
            assert(direction == -1)
            assert (hop >= 0)
            assert (hop < len(self.paths[flow_id]))
            # hop is the index of the link in the path
            # need to retrieve link_id separately
            link_id = self.paths[flow_id][hop]
            self.link_objects[link_id].set_time(curr_time)

            random_value = self.prng_drop.rand()
            if (random_value < self.drop_probability and time_since_start_rtts < 0.2 * self.dur_rtts):
                self.num_drops += 1
                self.message_objects[flow_id].dropped = True
                self.message_objects[flow_id].dropstr = "drop hop %d link %d fwd time %g %g RTTs from start"%\
                                                        (hop, link_id, curr_time, time_since_start_rtts)
                last_packet_time = -1
                if hasattr(self.source_objects[flow_id], "last_packet_time"):
                    last_packet_time = self.source_objects[flow_id].last_packet_time
                print("Dropping flow %d, %s msg %s src last_packet_time %s dur %g RTTs" %\
                    (flow_id, self.message_objects[flow_id].dropstr,\
                     self.message_objects[flow_id].name_,\
                     str(last_packet_time),  self.dur_rtts))
            else:
                self.link_objects[link_id].process_reverse\
                    (self.message_objects[flow_id])
                hop = hop - 1
            # direction unchanged

        # schedule message at next hop only if it's not stopped
        # msg.stopped is set by source object
        delay_noise = 0
        if self.delay_noise[1] > 0:
            delay_noise = self.prng_link_delay.randint(1,self.delay_noise[0]+1) * self.delay_noise[1]
        if (not self.message_objects[flow_id].stopped\
            and not self.message_objects[flow_id].dropped):
            mean_delay=self.link_delay
            # we're assuming first link captures delay for source s/w + NIC
            # similarly for destination
            if source_processed or destination_processed: mean_delay=0
            self.event_queue.schedule_process_flow_at_hop\
                (flow_id=flow_id, delay=mean_delay+delay_noise,\
                 hop=hop, direction=direction)
            if source_processed and self.frugal_rto > 0:
                self.event_queue.schedule\
                    ("retransmit timeout flow %d"\
                    %(flow_id), delay=self.frugal_rto)
        return

    def handle_retransmit_timeout_event(self, curr_time, ev):
        tokens = ev.split()
        flow_id = int(tokens[3])
        if flow_id not in self.source_objects:
            return
        last_packet_time = self.source_objects[flow_id].last_packet_time
        source_stopped = self.source_objects[flow_id].prepared_to_stop()
        assert(last_packet_time is not None)
        # if no packet was received at flow source for the last
        # frugal_rto duration, assume packet is dropped
        if ((curr_time - last_packet_time)*self.longest_rtt >= 0.9 * self.frugal_rto):
            print("Deduce drop flow %d curr time %g last_packet_time %g timeout %g dropper %s src stop? %s\n" %\
                (flow_id, curr_time, last_packet_time, self.frugal_rto,\
                 self.message_objects[flow_id].dropstr, source_stopped))
            # assume packet is dropped
            assert(self.message_objects[flow_id].dropped)
            if (not source_stopped):
                self.source_objects[flow_id].restart()
                num_restarts = self.source_objects[flow_id].num_restarts
                self.message_objects[flow_id] = self.alg_lib[self.alg].Message()
                self.message_objects[flow_id].id_ = flow_id
                path_str = str(self.paths[flow_id])
                self.message_objects[flow_id].name_ = "%s(%d) retx %d"%(path_str,flow_id, num_restarts)
                self.event_queue.schedule_start_flow(flow_id, delay=0)
                pass
            pass

    def handle_reset_maxsat_event(self, curr_time, ev):
        tokens = ev.split()
        link = int(tokens[3])
        self.link_objects[link].set_time(curr_time)
        self.link_objects[link].reset_max_sat()

        if hasattr(self.link_objects[link], 'sync_shadow_state'):
            self.link_objects[link].sync_shadow_state()
            assert(hasattr(self.link_objects[link], 'reset_shadow_state'))
            self.link_objects[link].reset_shadow_state()

        if not self.link_objects[link].stopped:
            self.event_queue.schedule("reset max_sat at %d"%link,\
                                      delay=self.frugal_timeout)
        return

    def handle_stop_flow_event(self, curr_time, ev):
        tokens = ev.split()
        flow_id = int(tokens[2])
        self.source_objects[flow_id].set_time(curr_time)
        if not self.source_objects[flow_id].prepared_to_stop():
            self.source_objects[flow_id].prepare_to_stop()
        return

    def handle_update_paths_event(self, curr_time, ev):
        all_flows = copy.deepcopy(self.paths.keys())
        path_lengths = []
        for flow_id in all_flows:
            assert (flow_id in self.source_objects)
            assert (flow_id in self.message_objects)
            assert (flow_id in self.destination_objects)
            if self.source_objects[flow_id].pending_leave\
                    and self.message_objects[flow_id].stopped:
                del self.paths[flow_id]
                del self.source_objects[flow_id]
                del self.message_objects[flow_id]
                del self.destination_objects[flow_id]
                self.finished_flows.append(flow_id)
            else:
                path_lengths.append(len(self.paths[flow_id]))
        current_longest_path = 0
        if len(path_lengths) > 0:
            current_longest_path = max(path_lengths)
        self.longest_rtt = self.link_delay * current_longest_path * 2            
    def handle_start_flow_event(self, curr_time, ev):
        tokens = ev.split()
        flow_id = int(tokens[2])
        self.source_objects[flow_id].set_time(curr_time)
        self.source_objects[flow_id].start_flow(self.message_objects[flow_id])
        delay_noise = 0
        if self.delay_noise[1] > 0:
            delay_noise = self.prng_link_delay.randint(1,self.delay_noise[0]+1) * self.delay_noise[1]
        self.event_queue.schedule_process_flow_at_hop\
            (flow_id=flow_id, hop=0, delay=(self.link_delay+delay_noise),\
             direction=1)
        if self.frugal_rto > 0:
            self.event_queue.schedule("retransmit timeout flow %d"\
                                      %(flow_id), delay=self.frugal_rto)
            pass
        return

    def handle_check_rates_event(self, curr_time, ev):
        tokens = ev.split()
        end_time = int(tokens[3])
        assert(self.convergence_run)
        self.check_rates(curr_time)
        if (self.event_queue.get_last_time() < end_time):\
            self.event_queue.schedule_check_rates\
                (delay=self.check_rates_interval, end_time=end_time) # actually absolute end time

        return
    pass
