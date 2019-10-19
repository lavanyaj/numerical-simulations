import sys
import random
#import matplotlib.pyplot as plt
import numpy as np
import time
#from gen_workload import *
#from waterfilling_hp import Waterfilling
from prec_library import PrecisionLibrary

#import networkx as nx
#import matplotlib.pyplot as plt
#import pygraphviz as pgv

class GlobalCpg:
    def __init__(self, routes, c, log, prec_library, neighbor_degree=1, get_precedents=False, hint_levels={}):
        #print "GlobalCpg"
        #print mpmath.mp
        ########################## Inputs ##############################        
        (self.num_flows, self.num_links) = routes.shape
        self.routes = routes  # incidence matrix for flows / links
        self.c = np.ones((self.num_links,1)) * prec_library.mpf_one  # link capacities
        for i in range(self.num_links):
            self.c[i] = prec_library.mpf(c[i,0])
        ################################################################
        self.prec_library = prec_library
        self.neighbor_degree=neighbor_degree
        self.get_precedents = get_precedents
        self.t = 0        
        self.r = np.ones((self.num_links,1)) * prec_library.mpf_inf
        self.x = np.ones((self.num_flows,1)) * prec_library.mpf_inf 
        self.levels = np.ones((self.num_links, 1)) * float('inf')
        self.flow_levels = np.ones((self.num_flows, 1)) * -1
        self.flow_bottlenecks = np.ones((self.num_flows, 1)) * -1
        self.max_level = -1
        self.hint_levels=hint_levels
        self.run(log=log)



    def run(self, log=False):
        num_flows = self.num_flows
        num_links = self.num_links
        routes = self.routes
        c = self.c
        rates = np.array(self.r, copy=True)
        
        rem_flows = np.array(range(num_flows))
        rem_links = np.array(range(num_links))


        rem_cap = np.array(c, copy=True)
        active_flows = np.ones((num_flows, 1), dtype=float)
        active_links = np.ones((num_links, 1), dtype=float)
        prev_rates = None
        freeze_level = {}

        potential_direct_precedents = {}
        potential_indirect_precedents = {}
        potential_second_direct_precedents = {}
        potential_second_indirect_precedents = {}

        direct_precedents = {}
        indirect_precedents = {}
        second_direct_precedents = {}
        second_indirect_precedents = {}

        self.max_level = 0

        while rem_flows.size != 0 and self.max_level < num_links:
            assert(len(rem_links) > 0)
            self.max_level += 1
            
            flows_per_link = routes.T.dot(active_flows)

            rates = np.ones((self.num_links, 1)) * -1 * self.prec_library.mpf_one

            for l in range(self.num_links):
                if flows_per_link[l,0] > 0:
                    rates[l,0] = rem_cap[l,0]/flows_per_link[l,0]
            
            for j in rem_links:
                # If link didn't have any active flows at the beginning of this round, ignore
                if flows_per_link[j,0] == 0:                    
                    continue

                if j not in potential_direct_precedents:
                    potential_direct_precedents[j] = []
                if j not in potential_indirect_precedents:
                    potential_indirect_precedents[j] = []
                if j not in potential_second_direct_precedents:
                    potential_second_direct_precedents[j] = []
                if j not in potential_second_indirect_precedents:
                    potential_second_indirect_precedents[j] = []
                    
                # Check each link if it has minimum rate of all links that share a flow with it
                # This should include all links that were active at the end of the last level
                
                flows_of_link = rem_flows[np.where(routes[rem_flows,j] > 0)[0]]                
                tmp = routes[flows_of_link, :]
                indices = np.unique(np.where(tmp[:, rem_links]>0)[1])
                assert(len(indices) > 0)                
                neighbors_of_link = rem_links[indices]                            
                link_rates = np.squeeze(rates[neighbors_of_link,:])
                assert((link_rates > self.prec_library.mpf_zero).all())
                assert((self.levels[neighbors_of_link] >= self.max_level).all())
                min_rate = np.min(link_rates)
                sorted_links =  np.argsort(link_rates, axis=0)
                assert(min_rate > self.prec_library.mpf_zero)
                
                # TODO: calculate potential precedents only if j is not going to be removed in this round
                # currently must do this in two passes, and get precedents in second pass given hint_levels
                if self.get_precedents: 
                    indices = np.where(link_rates < rates[j,0]) #[0] # np.where returns tuple of arrays, one for each dimension, we want row?
                    neighbors_with_smaller_rates = neighbors_of_link[indices]

                    # hint that j will be removed in next level
                    if (len(self.hint_levels) == 0 or (self.hint_levels[j] == self.max_level+1)):
                        potential_direct_precedents[j] = list(neighbors_with_smaller_rates)
                        #print "level", self.max_level, "potential_direct_precedents of",j,":", potential_direct_precedents[j]

                        potential_indirect_precedents[j] = []
                        for neighbor1 in potential_direct_precedents[j]:
                            flows_of_neighbor =  rem_flows[np.where(routes[rem_flows,neighbor1] > 0)[0]]
                            tmp = routes[flows_of_neighbor, :]
                            indices = np.unique(np.where(tmp[:, rem_links]>0)[1])
                            assert(len(indices) > 0)
                            neighbors_of_neighbor1 = rem_links[indices]
                            link_rates2 = np.squeeze(rates[neighbors_of_neighbor1])
                            assert((link_rates2 > self.prec_library.mpf_zero).all())
                            assert((self.levels[neighbors_of_neighbor1] >= self.max_level).all())

                            indices = np.where(link_rates2 < rates[neighbor1, 0])
                            neighbors_of_neighbor1_with_smaller_rates = list(neighbors_of_neighbor1[indices])
                            potential_indirect_precedents[j].extend([(neighbor2, neighbor1)\
                                                                     for neighbor2 in neighbors_of_neighbor1_with_smaller_rates\
                                                                 ])
                            pass
                        #print "level", self.max_level, "potential_indirect_precedents of",j,":", potential_indirect_precedents[j]

                        if (self.neighbor_degree == 2):
                            indices = np.where(link_rates >= rates[j,0]) #[0] # np.where returns tuple of arrays, one for each dimension, we want row?
                            neighbors_with_larger_rates = neighbors_of_link[indices]

                            potential_second_direct_precedents[j] = []
                            for neighbor1 in list(neighbors_with_larger_rates):
                                if neighbor1 == j: continue
                                flows_of_neighbor =  rem_flows[np.where(routes[rem_flows,neighbor1] > 0)[0]]
                                tmp = routes[flows_of_neighbor, :]
                                indices = np.unique(np.where(tmp[:, rem_links]>0)[1]) # index into rem_links
                                assert(len(indices) > 0)
                                neighbors_of_neighbor1 = rem_links[indices] # names of links
                                link_rates2 = np.squeeze(rates[neighbors_of_neighbor1]) # index is into neighbors_of..1
                                assert((link_rates2 > self.prec_library.mpf_zero).all())
                                assert((self.levels[neighbors_of_neighbor1] >= self.max_level).all())

                                indices = np.where(link_rates2 < rates[j, 0]) # index intro neighbors_of..1
                                neighbors_of_neighbor1_with_smaller_rates = list(neighbors_of_neighbor1[indices]) # names of links
                                potential_second_direct_precedents[j].extend([(neighbor2, neighbor1)\
                                                                          for neighbor2 in list(neighbors_of_neighbor1_with_smaller_rates)])
                                pass
                            #print "level", self.max_level, "potential_second_direct_precedents of",j,":", potential_second_direct_precedents[j]
                        
                            potential_second_indirect_precedents[j] = []
                            for neighbor2, neighbor1 in potential_second_direct_precedents[j]:
                                flows_of_neighbor =  rem_flows[np.where(routes[rem_flows,neighbor2] > 0)[0]]
                                tmp = routes[flows_of_neighbor, :]
                                indices = np.unique(np.where(tmp[:, rem_links]>0)[1])
                                assert(len(indices) > 0)
                                neighbors_of_neighbor2 = rem_links[indices]
                                link_rates3 = np.squeeze(rates[neighbors_of_neighbor2])
                                assert((link_rates3 > self.prec_library.mpf_zero).all())
                                assert((self.levels[neighbors_of_neighbor2] >= self.max_level).all())
                                
                                indices = np.where(link_rates3 < rates[neighbor2, 0])
                                neighbors_of_neighbor2_with_smaller_rates = list(neighbors_of_neighbor2[indices])
                                potential_second_indirect_precedents[j].extend([(neighbor3, neighbor2, neighbor1)\
                                                                                for neighbor3 in neighbors_of_neighbor2_with_smaller_rates])
                                pass
                            #print "level", self.max_level, "potential_second_indirect_precedents of",j,":", potential_second_indirect_precedents[j]
                            pass # if neighbor_degree == 2
                    pass


                if min_rate < rates[j,0]: 
                    k = None
                    flows_of_link = None
                    neighbors_of_link = None
                    link_rates = None
                    sorted_common_links = None
                    min_rate = None
                    continue
                
                if j not in freeze_level:
                    freeze_level[j] = []
                freeze_level[j].append(self.max_level)

                if min_rate >= rates[j,0]: 
                    cmp_ = ">="
                else: 
                    cmp_ = "<"

                if len(sorted_links) > 0:
                    # if log: print "type of sorted links", type(sorted_links), "shape", sorted_links.shape, "type of neighbors_of_link", type(neighbors_of_link)
                    sorted_link_names = neighbors_of_link[sorted_links]
                    # if log: print len(sorted_links), "first-degree neighbors with min_rate %.3f"%min_rate, cmp_, " rate of ", j, "%.3f"%rates[j,0],\
                    #    ", ".join(["%d (%.3f) "%(link, rates[link]) for link in sorted_link_names[:5]]),\
                    #    "..",\
                    #    ", ".join(["%d (%.3f)  "%(link, rates[link]) for link in sorted_link_names[-5:]])
                else:
                    #if log: print "no first-degree neighbors of ", j
                    pass

                # for links with rates -1, assume zero and ignore
                if self.neighbor_degree == 2:
                    #if log: print "checking second-degree neighbors of",j
                    first_degree_neighbor_links = {}

                    for neighbor1 in neighbors_of_link:
                        first_degree_neighbor_links[neighbor1] = j
                        pass

                    medium_links = {}
                    for neighbor1 in neighbors_of_link:
                        flows_of_neighbor =  rem_flows[np.where(routes[rem_flows,neighbor1] > 0)[0]]
                        tmp = routes[flows_of_neighbor, :]
                        indices = np.unique(np.where(tmp[:, rem_links]>0)[1])
                        assert(len(indices) > 0)                
                        neighbor_of_neighbor1 = rem_links[indices]
                        for neighbor2 in neighbor_of_neighbor1:
                            if neighbor2 not in medium_links\
                               and neighbor2 not in first_degree_neighbor_links\
                               and not (neighbor2 == j):
                                medium_links[neighbor2] = neighbor1
                            pass
                        pass

                    if len(medium_links) > 0:
                        second_degree_neighbors = np.asarray(medium_links.keys())
                        assert((self.levels[second_degree_neighbors] >= self.max_level).all())
                        link_rates = np.squeeze(rates[second_degree_neighbors,:])
                        assert((link_rates > self.prec_library.mpf_zero).all())
                        min_rate = np.min(link_rates)
                        sorted_links = np.squeeze(np.argsort(link_rates, axis=0))
                        assert(min_rate > self.prec_library.mpf_zero)
                        if min_rate >= rates[j,0]: cmp_ = ">="
                        else: cmp_ = "<"
                        #if log: print "type of sorted links", type(sorted_links), "shape", sorted_links.shape, "type of second_degree_neighbors", type(second_degree_neighbors)
                        sorted_link_names = second_degree_neighbors[sorted_links]
                        # if log: print len(sorted_links), "second-degree neighbors with min_rate %.3f"%min_rate, cmp_, " rate of ", j, "%.3f"%rates[j,0],\
                        #    ", ".join(["%d (%f) via %d (%f) "%(link, rates[link], medium_links[link], rates[medium_links[link]]) for link in sorted_link_names[:5]]),\
                        #    "..",\
                        #    ", ".join(["%d (%f) via %d (%f) "%(link, rates[link], medium_links[link], rates[medium_links[link]]) for link in sorted_link_names[-5:]]),\
                        if min_rate <  rates[j,0]: 
                            if log: print "second degree neighbors exists with rate exceeding rate of ", j, "%.3f"%rates[j,0],"continue"
                            k = None
                            flows_of_link = None
                            neighbors_of_link = None
                            link_rates = None
                            sorted_common_links = None
                            min_rate = None
                            continue
                    else:
                        if log: print "no second degree neighbors exist for link ", j
                        pass
                    pass


                if self.get_precedents:
                    seen = {}

                    direct_precedents[j] = []
                    for link in potential_direct_precedents[j]:
                        if (self.levels[link] == self.max_level - 1):
                            direct_precedents[j].append("%d (%.3f)"%(link, prev_rates[link]))
                            seen[link] = "d %d"%link
                            pass
                        pass

                    indirect_precedents[j] = []
                    for link,medium in potential_indirect_precedents[j]:
                        if (self.levels[medium] >= self.max_level and self.levels[link] == self.max_level - 1):
                            if link not in seen:
                                indirect_precedents[j].append(("%d (%.3f) -> %d (%.3f)"%(link, prev_rates[link], medium, prev_rates[medium])))
                                seen[link] = "i %d->%d"%(link,medium)
                            else:
                                if not (seen[link].startswith("i")):
                                    #print link, " seen before as ", seen[link], " considering now as i %d->%d"%(link, medium)
                                    pass
                                pass
                            pass
                        pass

                    second_direct_precedents[j] = []
                    for link,x in potential_second_direct_precedents[j]:
                        if (self.levels[link] == self.max_level - 1):
                            if link not in seen:
                                second_direct_precedents[j].append(("%d (%.3f) -> %d (%.3f)"%(link, prev_rates[link], x, prev_rates[x])))
                                seen[link] = "2d %d->%d"%(link,x)
                            else:
                                if not (seen[link].startswith("2d")):
                                    #print link, " seen before as ", seen[link], " considering now as 2d %d->%d"%(link, x)
                                    pass
                                pass
                            pass
                        pass

                    second_indirect_precedents[j] = []
                    for link,medium,x in potential_second_indirect_precedents[j]:
                        if (self.levels[medium] >= self.max_level\
                            and self.levels[link] == self.max_level - 1):
                            if link not in seen:
                                second_indirect_precedents[j].append(("%d (%.3f) -> %d (%.3f) -> %d (%.3f)"%(link, prev_rates[link], medium, prev_rates[medium], x, prev_rates[x])))
                                seen[link] = "2i %d->%d->%d"%(link, medium, x)
                            else:
                                if not (seen[link].startswith("2i")):
                                    #print link, " seen before as ", seen[link], " considering now as 2i %d->%d->%d"%(link, medium, x)
                                    pass
                                pass
                            pass
                        pass

                    if self.neighbor_degree == 1 and self.max_level > 1: 
                        assert(len(direct_precedents[j]) > 0 or len(indirect_precedents[j]) > 0)
                        pass

                    if self.neighbor_degree == 2 and self.max_level > 1: 
                        assert(len(direct_precedents[j]) > 0 or len(indirect_precedents[j]) > 0 or len(second_direct_precedents[j]) > 0 or len(second_indirect_precedents[j]) > 0)
                        pass
                    pass

                if log: 
                    print "Removing link ", j, " in CPG level ", self.max_level, " along with",\
                        len(flows_of_link), "flows at rate", float(rates[j,0]), " freeze-level", str(freeze_level[j])
                    
                    if self.get_precedents:
                        print len(direct_precedents[j]), "direct precedents", direct_precedents[j][:5], "..."
                        print len(indirect_precedents[j]), "indirect precedents", indirect_precedents[j][:5], "..."

                        if self.neighbor_degree == 2:
                            print len(second_direct_precedents[j]), "second direct precedents", second_direct_precedents[j][:5], "..."
                            print  len(second_indirect_precedents[j]), "second indirect precedents", second_indirect_precedents[j][:5], "..."
                            pass
                        pass
                    pass# if log
                
                assert(min_rate >= rates[j,0])
                self.r[j] = min(rates[j,0], min_rate)
                self.levels[j] = self.max_level
                self.flow_levels[flows_of_link] = self.max_level
                self.flow_bottlenecks[flows_of_link] = j
                self.x[flows_of_link] = min(rates[j,0], min_rate)
                                    
                # Update capacities of neighboring links, subtract rates of all active flows
                num_active_flows = routes[:,j].T.dot(active_flows)
                if log: print "updating capacity of neighbors of this link", j, ":", neighbors_of_link, "(", num_active_flows,  "active flows)" 

                if num_active_flows > 0:
                    # okay to have all links
                    for neighbor1 in neighbors_of_link:
                        if neighbor1 == j: continue
                        if self.levels[neighbor1] < float('inf'):
                            # if log:\
                            #    print "neighbor1 %d has level %d rate %s, we %d have level %d rate %s"\
                            #     % (neighbor1, self.levels[neighbor1], str(self.r[neighbor1]),\
                            #        j, self.max_level, min_rate)
                            assert(self.levels[neighbor1] == self.max_level)
                            continue               
                        num_active_common_flows = \
                                                  (np.minimum(routes[:,j],\
                                                              routes[:,neighbor1])).T\
                                                      .dot(active_flows)[0]
                        nacf = self.prec_library.mpf(num_active_common_flows)
                        rem_cap[neighbor1] = rem_cap[neighbor1] - nacf * rates[j,0]
                        if not (rem_cap[neighbor1] >= self.prec_library.mpf_zero):
                            print "rem_cap[", neighbor1,"] is", rem_cap[neighbor1], "exceeds 0(", self.prec_library.mpf_zero,")" 
                        assert(rem_cap[neighbor1] >= -1 * self.prec_library.eps1)
                        pass
                    pass
                
                active_flows[flows_of_link] = 0
                active_links[j] = 0                    

                if log: print "Link",j,"is no longer active, flows_per_link[j,0]", flows_per_link[j,0], "rem_cap[j]", rem_cap[j], "rates[j,0]", rates[j,0]
                pass
                # closes for j in rem_links

            rem_links = np.array([l for l in rem_links if active_links[l] > 0])
            rem_flows = np.array([f for f in rem_flows if active_flows[f] > 0])
            prev_rates = np.array(rates, copy=True)            
            pass
            # closes while rem_flows.si
        pass

