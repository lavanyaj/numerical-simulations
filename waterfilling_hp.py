import sys
import random
#import matplotlib.pyplot as plt
import numpy as np
import time

class Waterfilling:
    """
    initializes x and r with optimal flow allocations
    and link fair share rates for traffic matrix routes and link
    capacities c, and level with number of levels
    after running the waterfilling algorithm. note
    that if sum of flow allocations at a link is less than capacity
    then fair share of link is float('inf').
    not that routes and c must be initialized before calling this.
    """                

    def __init__(self, routes, c, log, prec_library):
        #log = True
        #print "Waterfilling"
        #print mpmath.mp
        
        (self.num_flows, self.num_links) = routes.shape
        self.levels = np.ones((self.num_links, 1)) * float('inf')
        self.prec_library = prec_library
        
        eps = prec_library.eps1
        weights = np.ones((self.num_flows,1))
        #print("weights", weights.shape, weights)
        #print("routes", routes.shape, routes)
        #self.r = np.ones((self.num_links,1)) * mpf_inf
        #self.x = np.ones((self.num_flows,1)) * mpf_inf 

        x = np.zeros((self.num_flows,1))
        active_flows = np.ones((self.num_flows, 1), dtype=bool)

        
        rem_cap = c #np.ones((self.num_links, 1)) * prec_library.mpf_one
        # for i in range(self.num_links):
        #     rem_cap[i] = prec_library.mpf(c[i,0])


        self.max_level = 0
        num_active_flows = np.count_nonzero(active_flows, axis=0)
        #print(num_active_flows,"flows left")

        while num_active_flows > 0:
            
            # number of rem flows on all links
            link_weights = np.dot(routes.T, weights)
            assert(rem_cap.shape == link_weights.shape)
            try:
                fair_shares = np.where(link_weights>0, rem_cap/link_weights, float('inf'))
            except:
                pass
            #print("link_weights", link_weights)
            #print("rem_cap", rem_cap)
            #print("fair_shares", fair_shares)
            fair_shares.reshape(self.num_links, 1)
            bl = np.argmin(fair_shares)
            #print ("bl",type(bl),bl)
            inc = float(fair_shares[bl, 0])
            assert(inc < float('inf'))

            # increase level, only when link with smallest fair share rate
            # has a rate larger than last one, handles the following example
            # two links, each cap 10.0, each has one flow, and none in common
            # each link identified in different iterations of this loop
            if self.max_level == 0 or inc > eps: self.max_level += 1
            x = np.where(active_flows, x + inc * weights, x)

            if log:
                    print "In round",self.max_level,\
                        " link", bl, "has smallest fair share", inc, "b/s",\
                        "Next rate increase is", inc, " (type ", type(inc), ") cuz of bl ",\
                        bl, " with rem_cap ", rem_cap[bl,0], " b/s",\
                        "and ", link_weights[bl,0] , " of the total ",\
                        num_active_flows, " remaining flows"
            rem_cap = rem_cap - inc * link_weights
            neg_cap = list(np.where(rem_cap < -1e7)[0]) # for each (aka only) column                    
            if (len(neg_cap) > 0):
                print >> sys.stderr, "warning! in watefilling hp links with neg. rem_cap ", neg_cap
            bf = np.where(routes[:,bl] > 0)[0]
            active_flows[bf] = 0
            num_active_flows = np.count_nonzero(active_flows, axis=0)
            #print(num_active_flows,"flows left")
            weights[bf] = 0
            self.levels[bl] = self.max_level
            
        # get max. rate at each link
        r = np.ones((self.num_links,1)) * float('inf')
        for e in range(self.num_links):
            flows = np.nonzero(routes[:, e])[0]
            if len(flows) > 0:
                sum_demands = sum(x[flows])[0]
                cap = c[e,0]
                diff = abs(sum_demands - cap)
                if (sum_demands > cap or diff < eps):
                    r[e] = max(x[flows])
                    print "link",e,"has rate", r[e]

        self.level = self.max_level
        self.x = x
        self.r = r

        self.bottleneck_links_arr = np.where(self.r < float('inf'))[0]
        self.bottleneck_links = {}
        self.non_bottleneck_links = {}

        self.sat_flows = {}
        self.unsat_flows = {}

# class Eps:
#     def __init__(self):
#         self.eps1 = 1e-7
#         pass

# def main():
#     for num_flows in [10, 100, 1000, 10000]:
#         start = time.time()
#         routes = np.ones((num_flows, 2))
#         routes[:, 1] = 0
#         routes[0:2, 1] = 1
#         routes[0, 0] = 0
#         c = np.ones((2,1))
    
#         wf = Waterfilling(routes, c, True, Eps())
#         stop = time.time()
#         elapsed = stop - start
#         print("num_flows", num_flows, "elapsed", elapsed,"s")
#         #print wf.x
#         #print wf.r
#         #print wf.level
#         pass

# main()
