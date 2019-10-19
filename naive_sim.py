import sys
import div_impl

# warn when warn_eps precision in calculations cause change in state
# uses 2 way updates and fixed timeouts for resetting max sat
# also want to log per-packet updates at link
class Link:
    def __init__(self):        
        self.alg = "naive"
        self.update_str_keys = ["time", "event", "e", "b", "condition", "s", "a", "NumB", "SumE", "R", "B", "E"]
        self.id_ = id(self)
        self.stopped = False
        self.sum_e = 0
        self.num_b = 0

        self.num_flows = 0
        self.max_e = 0 # not used in naive algorithm
        self.next_max_e = 0 # not used in naive algorithm

        self.last_bottleneck_rate_for_b_flow = 0
        self.actual_max_e = 0
        self.update_num = 0
        
        self.e_limit_rates = {}

        self.curr_time = -1
        self.curr_time_us = -1
        return

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
                 "num_flows": self.num_flows, 
                 "max_e": self.max_e, "actual_max_e":self.actual_max_e,\
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
        if (self.num_b == 0):
            true_rate = float('inf')
        else:
            true_rate = (self.capacity - self.sum_e)/self.num_b
        
        
        # we asume the flow is unsat for rate calculation
        new_flow = False
        num_flows = info["num_flows"]
        if (self.id_ not in msg.bottleneck_states):
            new_flow = True
            assert(self.id_ not in msg.allocations)
            num_flows += 1
            old_label = "new flow"
            old_alloc = -1
        else:
            old_label = msg.bottleneck_states[self.id_]
            old_alloc = msg.allocations[self.id_]
            pass

        sum_e = info["sum_e"]
        num_b = info["num_b"]
        max_e = info["max_e"]        
        if (self.id_ in msg.bottleneck_states and\
            msg.bottleneck_states[self.id_] == "E"):
            assert(self.id_ in msg.allocations)
            # we don't update max_e here
            sum_e -= msg.allocations[self.id_]
            assert(num_b < num_flows)
            num_b += 1
        pass

        if self.id_ not in msg.bottleneck_states: 
            num_b += 1
        
        # we calculate a rate using latest sum_e, num_flows, num_sat
        assert(num_b > 0)
        bottleneck_rate = (self.capacity - sum_e)/num_b
        update_str["b"] = bottleneck_rate
        #print "true_rate %.3f, allocation %.3f, label %s,  adjusted_rate %.3f. "%\
        #    (true_rate, old_alloc, old_label, rate),

        limit_rate = float('inf')
        if len(msg.bottleneck_rates) > 1 and self.id_ in msg.bottleneck_rates:
            limit_rate = min([msg.bottleneck_rates[l] for l in msg.bottleneck_rates if l != self.id_])
        update_str["e"] = limit_rate

        e_limit_rates_modified = False
        if limit_rate < float('inf') and bottleneck_rate > limit_rate\
           and abs(bottleneck_rate - limit_rate) > 1e-7:
            msg.bottleneck_states[self.id_] = "E"
            msg.allocations[self.id_] = limit_rate
            if msg.id_ not in self.e_limit_rates or abs(limit_rate - self.e_limit_rates[msg.id_]) > 1e-7:
                e_limit_rates_modified = True
            self.e_limit_rates[msg.id_] = limit_rate            
            #print "SAT at %.3f. "%msg.CPrequest,
        else:
            msg.bottleneck_states[self.id_] = "B"
            msg.allocations[self.id_] = bottleneck_rate
            self.last_bottleneck_rate_for_b_flow = bottleneck_rate
            if msg.id_ in self.e_limit_rates:
                e_limit_rates_modified = True
                del self.e_limit_rates[msg.id_]
            #print "UNSAT at %.3f. "%rate,            
            pass

        if e_limit_rates_modified:
            if len(self.e_limit_rates) > 0:
                self.actual_max_e = max([self.e_limit_rates[k] for k in self.e_limit_rates])
                self.actual_arg_max_e = [k for k in self.e_limit_rates if abs(self.e_limit_rates[k]-max_e) < 1e-6]
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
            
        # what happens if we don't use MaxSat?
        # max(max_e, bottleneck_rate)
        msg.bottleneck_rates[self.id_] = bottleneck_rate

        # implicit state ??
        # print "new sum_e %.3f, num_sat %.3f, num_flows %.3f\n" %\
        #     (self.sum_e, self.num_sat, self.num_flows)
        # print "update," + ",".join([str(update_str[k]) for k in self.update_str_keys])
        pass
        

    def update_local_state(self, old_label, old_alloc,\
                           new_label, new_alloc, msg):
        if (old_label == "new flow" and new_label in ["E", "B"]):
            self.num_flows += 1
        elif (old_label in ["E", "B"] and new_label == "inactive flow"):
             self.num_flows -= 1        
        if (old_label == "new flow" and new_label == "E"):
            self.sum_e += new_alloc
        elif (old_label == "new flow" and new_label == "B"):
            self.num_b += 1
        elif (old_label == "B" and new_label == "E"):
            self.sum_e += new_alloc
            self.num_b -= 1
        elif (old_label == "E" and new_label == "E"):            
            self.sum_e = self.sum_e - old_alloc + new_alloc
        elif (old_label == "E" and new_label == "B"):
            self.sum_e -= old_alloc
            self.num_b +=1
        elif (old_label == "E" and new_label == "inactive flow"):
             self.sum_e -= old_alloc
        elif (old_label == "B" and new_label == "inactive flow"):
             self.num_b -= 1

        # no changes to sum_e, num_b for new flow to inactive flow

class Source:
    def __init__(self):
        self.alg = "naive"            
        self.pending_leave = False
        self.curr_time = -1
        self.last_request = 0
        self.last_min_alloc = 0
        return

    def set_time(self, curr_time):
        self.curr_time = curr_time

    def get_actual_rate_bps(self):
        return self.last_request

    def get_last_request(self):
        return self.last_request
        
    def get_last_min_alloc(self):
        return self.last_min_alloc
        
    def start_flow(self, msg):
        msg.bottleneck_rates = {}
        msg.allocations = {}
        msg.bottleneck_states = {}
        return

    def process_reverse(self, msg):
        #self.last_request = float('inf')
        if len(msg.bottleneck_rates) > 0: self.last_request = min([msg.bottleneck_rates[l] for l in msg.bottleneck_rates]) # bottlneck rates
        if len(msg.allocations) > 0: self.last_min_alloc = min([msg.allocations[l] for l in msg.allocations]) # allocations
        return

    def prepared_to_stop(self):
        return self.pending_leave        

    def prepare_to_stop(self):
        assert(self.pending_leave == False)
        self.pending_leave = True
        return

class Destination:
    def __init__(self):
        self.alg = "naive"
        self.curr_time = -1
        return

    def set_time(self, curr_time):
        self.curr_time = curr_time
        return

    def process_forward(self, msg):
        return

class Message:
    def __init__(self):
        self.alg = "naive"            

        self.allocations = {} # allocation
        self.bottleneck_states = {} # bottleneck state
        self.bottleneck_rates = {} # bottleneck rate (for naive/ PERC)
        
        self.dropped = False
        self.stopped = False
        self.id_ = id(self)
        self.name_ = str(self.id_)

        pass

    def get_requested_rate(self):
        if len(self.bottleneck_rates) > 0: return  min([self.bottleneck_rates[l] for l in self.bottleneck_rates])
        return float('inf')
