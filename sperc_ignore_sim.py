import sys
import div_impl

# warn when warn_eps precision in calculations cause change in state
# uses 2 way updates and fixed timeouts for resetting max sat
# also want to log per-packet updates at link
class Link:
    def __init__(self):        
        self.alg = "sperc_ignore"
        self.update_str_keys = ["time", "event", "e", "b", "condition", "s", "a", "NumB", "SumE", "R", "B", "E"]
        self.id_ = id(self)
        self.stopped = False
        self.sum_e = 0
        self.num_b = 0

        self.num_flows = 0
        self.max_e = 0 
        self.next_max_e = 0 

        self.last_bottleneck_rate_for_b_flow = 0 # for logging only
        self.actual_max_e = 0 # for logging only

        self.update_num = 0
        
        self.e_limit_rates = {}

        self.curr_time = -1
        self.curr_time_us = -1
        self.eps = 1e-7
        self.approx_div = False

        return

    def set_epsilon(self, eps):
        self.eps = eps
        pass

    def use_approx_div(self, N, l, m, cap_range, max_flows, eps):
        assert(div_impl.N == N)
        assert(div_impl.l == l)
        assert(div_impl.m == m)
        assert(div_impl.initialized)
        self.approx_div = True
        self.cap_range = cap_range
        self.max_flows = max_flows
        self.rel_err = eps / cap_range[1]
        pass

    def set_time(self, curr_time):
        self.curr_time = curr_time

    def set_time_us(self, curr_time_us):
        self.curr_time_us = curr_time_us
        
    # def get_rate_bps(self):        
    #     if self.num_flows == 0: return 0

    #     #        elif (self.capacity - self.sum_e) < 1e-6:
    #     #            rate = self.max_e

    #     if self.num_b > 0:
    #         rate = (self.capacity - self.sum_e)/self.num_b
    #     else:
    #         rate = float('inf')
    #     return rate

    def prepare_to_stop(self):
        assert(not self.stopped)
        self.stopped = True

    def set_capacity(self, cap_bps):
        self.capacity = cap_bps
        return


    def update_max_e(self, new_alloc):
        self.max_e = max(self.max_e, new_alloc)
        self.next_max_e = max(self.next_max_e, new_alloc)
        pass

    def reset_max_sat(self):
        self.max_e = self.next_max_e
        self.next_max_e = 0
        pass

    def get_local_state(self):
        info =  {"sum_e": self.sum_e, "num_b": self.num_b,\
                 "num_flows": self.num_flows, "max_e": self.max_e,
                 "actual_max_e": self.actual_max_e,\
                 "last_bottleneck_rate_for_b_flow": self.last_bottleneck_rate_for_b_flow}
        # print "get_local_state: link %d %s" % (self.id_, state_str)
        return info

    def process_forward(self, msg):
        self.process_common(msg)

    def process_reverse(self, msg):
        self.process_common(msg)

    def process_common(self, msg):
        #update_str_keys = ["time", "event", "e", "b", "condition", "s", "a", "NumB", "SumE", "R", "B", "E"]
        update_str = {}
        for k in self.update_str_keys: update_str[k] = ""
        update_str["time"] = self.curr_time_us
        update_str["event"] = "%d at Link %d"%(msg.id_, self.id_)        
        info = self.get_local_state()
        #print "%d) msg %d at link %d at %.2f. "%(self.update_num, msg.id_, self.id_, self.curr_time),
        self.update_num += 1
        #print "old sum_e %.3f, num_sat %.3f, num_flows %.3f. " %(self.sum_e, self.num_sat, self.num_flows),
        
        # we asume the flow is unsat for rate calculation
        #old_label = "new flow"
        #old_alloc = -1
        #        else:
        #           old_label = msg.bottleneck_states[self.id_]
        #          old_alloc = msg.allocations[self.id_]
        #         pass

        sum_e = info["sum_e"]
        num_b = info["num_b"]
        max_e = info["max_e"]        
        num_flows = info["num_flows"]

        # assume flow not limited here for bottleneck rate
        if (self.id_ not in msg.bottleneck_states): # old flow
            msg.bottleneck_states[self.id_] = "E"
            msg.allocations[self.id_] = 0
            num_flows += 1
            self.num_flows += 1
            pass

        if(msg.bottleneck_states[self.id_] == "E"):
            # we don't update max_e here
            sum_e -= msg.allocations[self.id_]
            num_b += 1
            assert(num_b <= num_flows)
            pass

        old_label = msg.bottleneck_states[self.id_]
        old_alloc = msg.allocations[self.id_]
                
        # we calculate a rate using latest sum_e, num_flows, num_sat
        assert(num_b > 0)
        bottleneck_rate = (self.capacity - sum_e)/num_b
        true_bottleneck_rate = bottleneck_rate
        if self.approx_div: 
            bottleneck_rate = div_impl.sperc_divide(cap=(self.capacity-sum_e),\
                                                    flows=num_b,cap_range=self.cap_range,\
                                                    max_flows = self.max_flows)
            pass

        update_str["b"] = bottleneck_rate
        #print "true_rate %.3f, allocation %.3f, label %s,  adjusted_rate %.3f. "%\
        #    (true_rate, old_alloc, old_label, rate),

        # assume flow not limited here for limit rate
        msg.bottleneck_rates[self.id_] = float('inf')
        msg.ignore_bits[self.id_] = 1
        # propagated rate is infty if ignore, else b
        links = sorted(msg.bottleneck_rates.keys())
        ignore_bits = [msg.ignore_bits[l] for l in links]
        bottleneck_rates = [msg.bottleneck_rates[l] for l in links]
        propagated_rates = []
        for i in range(len(ignore_bits)): 
            assert(type(ignore_bits[i]) == int and ignore_bits[i] in [1,0])
            if ignore_bits[i] == 0: 
                propagated_rates.append(bottleneck_rates[i])
            else:
                propagated_rates.append(float('inf'))
                pass
            pass
        limit_rate = min(propagated_rates)
        update_str["e"] = limit_rate

        assert(bottleneck_rate < float('inf'))

        e_limit_rates_modified = False            
        
        if limit_rate < float('inf')\
             and true_bottleneck_rate > limit_rate\
             and abs(true_bottleneck_rate - limit_rate) > self.eps: # true value since this is just c - sume > limit_rate * numb
            msg.bottleneck_states[self.id_] = "E"
            msg.allocations[self.id_] = limit_rate

            if msg.id_ not in self.e_limit_rates\
               or abs(limit_rate - self.e_limit_rates[msg.id_]) > self.eps:
                e_limit_rates_modified = True
            self.e_limit_rates[msg.id_] = limit_rate

        else:
            msg.bottleneck_states[self.id_] = "B"
            msg.allocations[self.id_] = bottleneck_rate # lookup table
            self.last_bottleneck_rate_for_b_flow = bottleneck_rate

            if msg.id_ in self.e_limit_rates:
                e_limit_rates_modified = True
                del self.e_limit_rates[msg.id_]        
            pass

        if e_limit_rates_modified:
            if len(self.e_limit_rates) > 0:
                self.actual_max_e = max([self.e_limit_rates[k] for k in self.e_limit_rates])
                self.actual_arg_max_e = [k for k in self.e_limit_rates if abs(self.e_limit_rates[k]-max_e) < 10*self.eps]

                pass
            else:
                self.actual_max_e = 0
                self.actual_arg_max_e = -1

        update_str["a"] = msg.allocations[self.id_]
        update_str["s"] = msg.bottleneck_states[self.id_]
            
        self.update_local_state(old_label, old_alloc,\
                                msg.bottleneck_states[self.id_],\
                                msg.allocations[self.id_], msg)

        if (msg.bottleneck_states[self.id_] == "E"):
            self.update_max_e(msg.allocations[self.id_])
            pass

        update_str["NumB"] = self.num_b
        update_str["SumE"] = self.sum_e
            
        # by default we propagate, but if bottleneck rate is definitely less than maxe, ignore
        msg.bottleneck_rates[self.id_] = bottleneck_rate # lookup table
        if (max_e > true_bottleneck_rate\
            and abs(max_e - true_bottleneck_rate) > self.eps): # true value since this is just maxe * numb > c - sume
            msg.ignore_bits[self.id_] = 1
        else:
            msg.ignore_bits[self.id_] = 0
        pass
        

    def update_local_state(self, old_label, old_alloc,\
                           new_label, new_alloc, msg):
        if (old_label == "B" and new_label == "E"):
            self.sum_e += new_alloc
            self.num_b -= 1
        elif (old_label == "E" and new_label == "E"):            
            self.sum_e = self.sum_e - old_alloc + new_alloc
        elif (old_label == "E" and new_label == "B"):
            self.sum_e -= old_alloc
            self.num_b +=1
        elif (old_label == "E" and new_label == "inactive flow"):
             self.sum_e -= old_alloc
             self.num_flows -= 1        
        elif (old_label == "B" and new_label == "inactive flow"):
             self.num_b -= 1
             self.num_flows -= 1        


        # no changes to sum_e, num_b for new flow to inactive flow

class Source:
    def __init__(self):
        self.alg = "sperc_ignore"            
        self.pending_leave = False
        self.curr_time = -1
        self.last_request = 0
        self.last_min_alloc = 0
        return

    def set_time(self, curr_time):
        self.curr_time = curr_time

    def get_actual_rate_bps(self):
        return self.last_min_alloc

    # def get_last_request(self):
    #     return self.last_request
        
    def get_last_min_alloc(self):
        return self.last_min_alloc
        
    def start_flow(self, msg):
        msg.bottleneck_rates = {}
        msg.allocations = {}
        msg.bottleneck_states = {}
        return

    def process_reverse(self, msg):
        #self.last_request = float('inf')
        if len(msg.bottleneck_rates) > 0: 
            self.last_request = min(msg.bottleneck_rates.values())
        if len(msg.allocations) > 0: 
            self.last_min_alloc = min(msg.allocations.values())
        return

    def prepared_to_stop(self):
        return self.pending_leave        

    def prepare_to_stop(self):
        assert(self.pending_leave == False)
        self.pending_leave = True
        return

class Destination:
    def __init__(self):
        self.alg = "sperc_ignore"
        self.curr_time = -1
        return

    def set_time(self, curr_time):
        self.curr_time = curr_time
        return

    def process_forward(self, msg):
        return

class Message:
    def __init__(self):
        self.alg = "sperc_ignore"            

        self.allocations = {} # allocation
        self.bottleneck_states = {} # bottleneck state
        self.bottleneck_rates = {} # bottleneck rate (for sperc_ignore/ PERC)
        self.ignore_bits = {}

        self.dropped = False
        self.stopped = False
        self.id_ = id(self)
        self.name_ = str(self.id_)

        pass

    # def get_requested_rate(self):
    #     if len(self.bottleneck_rates) > 0: return  min([self.bottleneck_rates[l] for l in self.bottleneck_rates])
    #     return float('inf')
