import sys
import div_impl

# warn when warn_eps precision in calculations cause change in state
# uses 2 way updates and fixed timeouts for resetting max sat
# also want to log per-packet updates at link
class Link:
    def __init__(self):        
        self.eps = 1.0e-7
        self.alg = "perc"
        self.update_str_keys = ["time", "event", "e", "b", "condition", "a", "R", "B", "E"]
        self.id_ = id(self)
        self.stopped = False
  
        self.limit_rates = {}

        self.last_time_max_min_rate_for_flow_updated = {}
        self.last_max_min_rate_for_flow = {}
        self.last_time_limit_rates_changed = None
        # if last_time_max_min_rate_for_flow_updated < last_time_limit_rates_changed: update max min rate again
        
        # we don't want to do a max-min rate calculation, every time get_rate_bps() is called
        # so we'll save the bottleneck rate each time we find a flow is bottlenecked
        # if it's different from old bottleneck rate .. or if flow is not bottlenecked
        # we'll say self.bottleneck_rate_for_bottleneck_flow_updated = True
        self.latest_bottleneck_rate = float('inf')
        self.latest_max_e = 0
        
        self.num_flows = 0
        self.update_num = 0        
        self.curr_time = -1
        self.curr_time_us = -1
        return

    def get_local_state(self):
        return {"max_e": self.latest_max_e, "bottleneck_rate": self.latest_bottleneck_rate}
        
    def max_min_rate(self):
        values = sorted(self.limit_rates.values())
        sum_values = sum(values)
        sum_e = 0
        n = len(values)
        r = self.capacity/float(n)
        assert(values[-1] == float('inf') or sum_values > self.capacity or abs(self.capacity - sum_values) <= self.eps)
        for i in range(n):
            if values[i] >= r or abs(values[i]-r) < self.eps: return r
            sum_e += values[i]
            num_b = n - i - 1
            r = float(self.capacity - sum_e)/num_b
            pass
        assert(False)
        pass
        
    def set_time(self, curr_time):
        self.curr_time = curr_time

    def set_time_us(self, curr_time_us):
        self.curr_time_us = curr_time_us
        
    def get_rate_bps(self):        
        if self.num_flows == 0: return 0
        return self.latest_bottleneck_rate
        
    def prepare_to_stop(self):
        assert(not self.stopped)
        self.stopped = True

    def set_capacity(self, cap_bps):
        self.capacity = cap_bps
        return


    def update_max_e(self, new_alloc):
        # do nothing
        pass

    def reset_max_sat(self):
        # do nothing
        pass

    def process_forward(self, msg):
        self.process_common(msg)

    def process_reverse(self, msg):
        self.process_common(msg)

        
    def process_common(self, msg):
        #self.update_str_keys = ["time", "event", "e", "b", "condition", "a", "R", "B", "E"]
        update_str = {}
        for k in self.update_str_keys: update_str[k] = ""
        update_str["time"] = self.curr_time_us
        update_str["event"] = "%d at Link %d"%(msg.id_, self.id_)
        
        self.update_num += 1

        # we asume the flow is unsat for rate calculation
        # first save the old limit rate so we can check if it's changed later
        new_flow = False
        num_flows = self.num_flows
        if (msg.id_ not in self.limit_rates):
            new_flow = True
            assert(self.id_ not in msg.allocations)
            num_flows += 1
            old_limit_rate = None
        else:
            old_limit_rate = self.limit_rates[msg.id_]            
            pass

        # Find bottlneck rate for flow based on other flows' limit rates
        if msg.id_ not in self.last_time_max_min_rate_for_flow_updated\
           or self.last_time_limit_rates_changed is None\
           or (self.last_time_max_min_rate_for_flow_updated[msg.id_] < self.last_time_limit_rates_changed):
            self.limit_rates[msg.id_] = float('inf')
            bottleneck_rate = self.max_min_rate()
            self.last_time_max_min_rate_for_flow_updated[msg.id_] = self.curr_time
            self.last_max_min_rate_for_flow[msg.id_] = bottleneck_rate
        else:
            bottleneck_rate = self.last_max_min_rate_for_flow[msg.id_]
            pass
        update_str["b"] = bottleneck_rate


        # Find new limit rate for flow
        limit_rate = float('inf')
        if len(msg.bottleneck_rates) > 1 and self.id_ in msg.bottleneck_rates:
            limit_rate = min([msg.bottleneck_rates[l] for l in msg.bottleneck_rates if l != self.id_])
        update_str["e"] = limit_rate


        # Compare and decide flow's new allocation
        bottlenecked = False    
        if limit_rate < float('inf') and bottleneck_rate > limit_rate\
           and abs(bottleneck_rate - limit_rate) > self.eps:
            msg.allocations[self.id_] = limit_rate
            update_str["condition"] = "e < b"
        else:
            bottlenecked = True
            msg.allocations[self.id_] = bottleneck_rate
            update_str["condition"] = "e >= b"
            pass
        update_str["a"] = msg.allocations[self.id_]
        msg.bottleneck_rates[self.id_] = bottleneck_rate


        # Save flow's new limit rate if it changed since last time
        if old_limit_rate is None or abs(old_limit_rate-limit_rate)>self.eps:
            self.limit_rates[msg.id_] = limit_rate
            self.last_time_limit_rates_changed = self.curr_time
        else:
            self.limit_rates[msg.id_] = old_limit_rate
            

        # Do we update bottleneck rate for bottleneck flows?
        if bottlenecked and bottleneck_rate != self.latest_bottleneck_rate:
            self.latest_bottleneck_rate = bottleneck_rate
        elif not bottlenecked and (old_limit_rate is None or old_limit_rate != limit_rate):
            sum_limit_rates = sum(self.limit_rates.values())
            if sum_limit_rates < self.capacity and abs(sum_limit_rates-self.capacity) > self.eps:
                self.latest_bottleneck_rate = float('inf')
                self.latest_max_e = max(self.limit_rates.values())
            else:
                self.latest_bottleneck_rate = self.max_min_rate()
                e_rates = [v for v in self.limit_rates.values() if v < self.latest_bottleneck_rate]
                if len(e_rates) > 0: self.latest_max_e = max(e_rates)
                else: self.latest_max_e = 0

        update_str["R"] = self.latest_bottleneck_rate
        bottlenecked_flows = sorted([f for f in self.limit_rates if self.limit_rates[f] >= self.latest_bottleneck_rate])
        update_str["B"] = str(bottlenecked_flows[:5])
        update_str["E"] = str(sorted([f for f in self.limit_rates if self.limit_rates[f] < self.latest_bottleneck_rate])[:5])
        #print "update," + ",".join([str(update_str[k]) for k in self.update_str_keys])
        pass
        

class Source:
    def __init__(self):
        self.alg = "perc"            
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
        self.alg = "perc"
        self.curr_time = -1
        return

    def set_time(self, curr_time):
        self.curr_time = curr_time
        return

    def process_forward(self, msg):
        return

class Message:
    def __init__(self):
        self.alg = "perc"            

        self.allocations = {} # allocation
        self.bottleneck_rates = {} # bottleneck rate (for naive/ PERC)
        
        self.dropped = False
        self.stopped = False
        self.id_ = id(self)
        self.name_ = str(self.id_)

        pass

    def get_requested_rate(self):
        if len(self.bottleneck_rates) > 0: return  min([self.bottleneck_rates[l] for l in self.bottleneck_rates])
        return float('inf')
