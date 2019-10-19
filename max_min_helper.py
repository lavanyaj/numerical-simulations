import copy
import sys
import random
#import matplotlib.pyplot as plt
import numpy as np
import time
from general_cpg import GlobalCpg
from waterfilling_hp import Waterfilling
#from gen_workload import gen_random_instance

#from check_invariants import InvariantsChecker
from collections import deque # to store last xx values of err as rates converge


# Helper class to study convergence of async max min algorithms, based on Waterfilling and CPG theory
# Given a traffic matric routes and link capacities c, initialize a MaxMinHelper object
# 1) to get optimal flow allocations and link fair share rates from water-filling (.maxmin.x and .maxmin.r),
# 2) to run synchronous CPG (run_reference) for sync_cpg_max_iterations and get number of steps taken by sync CPG (.sync_cpg.steps_to_converge)
# 3) and to build constraint precedence graph of links (.dependency_graph)
# 4) to log demands and rate from async algorithm and check convergence
# 5) to understand its convergence time in terms of CPG

# Note about convergence thresholds eps.
# Reference synchronous CPG is run until both rates and demands match optimal to within eps (sync_cpg_convergence_threshold)
# Also CPG levels are computed from this run by comparing link rates to optimal rates using eps (sync_cpg_convergence_threshold)
# We check convergence of arbitrary alg using log_from_algo by checking if demands match optimal to within eps (convergence_threshold)
# We record convergence times of links of arbitrary alg  by checking if  rate matches optimal to within eps (convergence_threshold)
# We analyze convergence times by checking links' convergence times (alg_levels) wrt levels from sync CPG run (levels).
# We also record the first time the link rates got close to optimal (first_convergence_threshold)
class MaxMinHelper:
    def __init__(self, routes, c,\
                 max_consecutive_converged,\
                 prec_library,
                 instance_num=0,\
                 log=False):        
        ########################## Inputs ##############################        
        (self.num_flows, self.num_links) = routes.shape
        self.routes = routes  # incidence matrix for flows / links
        self.c = c            # link capacities        
        self.instance_num = instance_num
        #self.check_stable = check_stable
        self.prec_library = prec_library
        self.waterfilling_eps = prec_library.eps1
        self.global_cpg_eps = prec_library.eps1
        self.convergence_threshold = prec_library.eps3
        self.log = log
        
        self.print_unique_paths(log)
        
        # Waterfilling max-min rates and levels
        self.maxmin = Waterfilling(routes, c, prec_library=self.prec_library, log=log)
        self.cpg_maxmin = GlobalCpg(routes, c, prec_library=self.prec_library, log=log, neighbor_degree=2)
        self.cpg_maxmin1 = GlobalCpg(routes, c, prec_library=self.prec_library, log=log, neighbor_degree=1)

        rates_diff = self.prec_library.get_diff(self.maxmin.r, self.cpg_maxmin.r)
        linf_err = max(rates_diff)
        if (linf_err > self.prec_library.eps3):
            print "warning! cpg v/s wf linf err rates=", linf_err

        flows_diff = self.prec_library.get_diff(self.maxmin.x, self.cpg_maxmin.x)
        linf_err = max(flows_diff)
        if (linf_err > self.prec_library.eps3):
            print "warning! cpg v/s wf linf err flows=", linf_err

        print "\nFinished calculating rates using Waterfilling and Cpg, they match to ", linf_err, " (flow rates)"
        # convergence info for async alg            
        self.alg_name = None
        self.invariants_checker = None
        
        self.MaxDiffRTTs = {}
        self.ArgMaxDiff = {}

    """
    prints flow ids, grouped by unique paths
    """
    def print_unique_paths(self, log=False):
        self.flow_to_path = {}
        unique_paths = {}
        self.paths = {}
        for i in range(self.num_flows):
            self.paths[i] = np.nonzero(self.routes[i, :])[0]
            path_str = str(self.paths[i])
            if path_str not in unique_paths:
                unique_paths[path_str] = []
            unique_paths[path_str].append(i)
            self.flow_to_path[i] = path_str
        keys = sorted(unique_paths.keys(), key=lambda k: len(unique_paths[k]), reverse=True)
        self.longest_rtt = max([len(self.paths[i]) for i in self.paths]) * 10 * 2.0

        if log:
            print "Flows by path"
            for k in keys:
                print k, " ", len(unique_paths[k]), " : ", str(sorted(unique_paths[k]))

        #unique paths, by link
        paths_by_link = {}
        for i in range(self.num_links):
            paths_by_link[i] = {}
            for path in unique_paths:
                if "[%d]"%i in path or "[%d "%i in path or " %d "%i in path or " %d]"%i in path:
                    paths_by_link[i][path] = True

        if log:
            for i in range(self.num_links):
                print "Link %d: "%i,
                total_flows = 0
                info = ""
                for path in paths_by_link[i]:
                    num_flows = len(unique_paths[path])
                    info += "%d %s, " % (num_flows, path)
                    total_flows += num_flows
                print total_flows, " flows- ", info
        self.paths_by_link = paths_by_link
        self.unique_paths = unique_paths
            
    
    def print_details(self, actual, optimal, name="demands"):
        ##print 'iteration=', self.t
        ##print 'demands=', self.demands.T
        #print 'maxmin=', self.maxmin.x.T
        linf_err = max(self.prec_library.get_diff(opt=optimal,act=actual))
        print 'linf error ', name, ' =', linf_err
        #print 'x.shape', self.x.shape
        print 'max(actual)', name, ' = ', max(actual)
        print 'max(maxmin)', name, ' = ',  max(optimal)
        print 'min(actual)', name, ' = ',  min(actual)
        print 'min(maxmin)', name, ' = ',  min(optimal)


