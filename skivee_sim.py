import sys
import div_impl

class Link:
    def __init__(self):	       
	self.alg = "skivee"
        self.log = False
	self.id_ = id(self)
	self.stopped = False
	self.eps=1.0e-8
	self.rho = 0
        self.max_e = 0
	self.FR = {} # fair rate of LSP, known at link

	# the following need to be in sync
	self.BN = {} # bottleneck of LSP, known at link
	self.S = {} # Set of LSPs traversing link
	self.B = {} # set of LSPs bn-ed at link
	self.U = {} # set of LSPs not bn-ed at link

	self.update_num = 0	   
	self.curr_time = -1
	self.curr_time_us = -1
	return
	
    def calculate_rho(self):
	assert(len(self.S) > 0)
	sum_u = float(sum([self.FR[f] for f in self.U]))
	num_bn = float(len(self.B))
	if num_bn > 0:
	    rho = (self.capacity - sum_u) / num_bn
	else:
	    sum_all = sum([self.FR[f] for f in self.S])
	    num_all = float(len(self.S))
            max_all = None
            for k in self.FR:
                if max_all is None\
                   or self.FR[k] > max_all:
                    max_all = self.FR[k]
                pass
            if max_all is None: max_all = 0
            
	    rho = (self.capacity - sum_all) / num_all\
		 + max_all
	    pass
	return rho

	     
    def get_local_state(self):
	return \
	    {"rho": self.rho, "max_e": self.max_e}
	
    def get_state(self, p):
	if p in self.U: return "U"
        else: return "B"

    def move_to_B(self, p):
	if p in self.U: del self.U[p]
	self.B[p] = True

    def move_to_U(self, p):
	if p in self.B: del self.B[p]
	self.U[p] = True

    def update_rho(self, update_str, prefix):
	update_str_keys = ["moved", "rho1", "final"]
        info = {}
        for k in update_str_keys: info[k] = ""

        
	rho = self.calculate_rho()
	if len(self.U) > 0:
	    while True:
                bottleneck_consistent=True
                for f in self.U:
	            if (self.FR[f] > rho+self.eps): 
		        bottleneck_consistent=False
                        break
                    pass
		if bottleneck_consistent: break
	        rho_1 = rho
	        if self.log: info["rho1"] += "%.3f,"%(rho_1)
                p = None
                for u in self.U:
                    if p is None or self.FR[u] > self.FR[p]:
                        p = u
                        pass
                    pass
                        
	        assert(p not in self.B and p in self.U)
	        if p > rho_1+self.eps:
		    self.move_to_B(p) 
		    rho = self.calculate_rho()
		    if self.log: info["moved"] += "%d %.3f,"%(p, rho_1)
		    pass		  

	        if p <= rho_1+self.eps or len(self.U) == 0:
		    if self.log: info["final"] = "%.3f (%d U)"%(rho_1, len(self.U))
                    break
                    pass
                pass # while True    
            pass # if len(self.U) > 0
        if self.log: str_ = prefix + ",".join([str(info[k]) \
                    for k in update_str_keys])
        if self.log: update_str[prefix] = str_
        return rho # def update_rho	     
		  
	
    def set_time(self, curr_time):
	self.curr_time = curr_time

    def set_time_us(self, curr_time_us):
	self.curr_time_us = curr_time_us
	
    def get_rate_bps(self):	   
	if len(self.S) == 0: return 0
	return self.rho
	
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
	# compare limit rate to existing rho
	# and move to B if needed
	# and don't update rho (why?)

        update_str_keys = ["time", "event", "dir",\
			   "b_old", "e_old", "bn_old", "s_old",\
                           "b_new", "e_new", "bn_new", "s_new"]
        update_str = {}

        for k in update_str_keys: 
            update_str[k] = ""
            pass
            
        if self.log:
            update_str["time"] = self.curr_time_us
	    update_str["event"] = "%d at Link %d"%(msg.id_, self.id_)
            update_str["dir"] = ["fwd"]
	    pass
            
	self.update_num += 1

	#self.lsp_creation_and_termination(update_str)
	key = "update_rho_new(%d)"% (msg.id_)
	update_str_keys.append(key)
	update_str[key] = ""
	if msg.id_ not in self.S:
	    self.S[msg.id_] = True
	    self.move_to_B(msg.id_)
	    self.rho = self.update_rho(update_str, key)
            max_e = 0
            for u in self.U:
                if max_e is None\
                  or self.FR[u] > max_e:
                    max_e = self.FR[u]
                    pass
                pass
            self.max_e = max_e

	    pass

	# self.update_er(update_str)

        if (self.rho < -1 * self.eps):
            print >> sys.stderr, "rho negative", self.rho
	assert(msg.ER >= -1 * self.eps)
	#assert(self.rho >= -1 * self.eps)
        if self.log:
	    update_str["b_old"] = self.rho
	    update_str["e_old"] = msg.ER
            update_str["bn_old"] = msg.BN
	    update_str["s_old"] = self.get_state(msg.id_)
            pass

        if (self.rho + self.eps < msg.ER or msg.BN == self.id_):
            # lavanya: added msg.BN == self.id_ so this link will update ER when its BN goes up            
            # so that other links can update ER
	    self.move_to_B(msg.id_)
	    msg.BN = self.id_
	    msg.ER = self.rho
	    # and don't update rho?
	    pass
        if self.log:
	    update_str["b_new"] = ""
	    update_str["e_new"] = msg.ER
	    update_str["bn_new"] = msg.BN
            update_str["s_new"] = self.get_state(msg.id_)
            pass
	if self.log: print "update," + ",".join([k+":"+str(update_str[k]) for k in update_str_keys])
        assert(self.rho >= -1 * self.eps)

	pass

    def process_reverse(self, msg):
	# update limit rate and bottleneck link
	# and use bottleneck link to move to B or U
	# and update rho
	update_str_keys = ["time", "event", "dir",\
			   "b_old", "e_old", "bn_old", "s_old",\
                           "b_new", "e_new", "bn_new", "s_new"]
	update_str = {}
	for k in update_str_keys: 
	    update_str[k] = ""
        if self.log:
	    update_str["time"] = self.curr_time_us
	    update_str["event"] = "%d at Link %d"%(msg.id_, self.id_)
	    update_str["dir"] = ["rvs"]
	    pass
	self.update_num += 1
        if self.log:
	    update_str["b_old"] = self.rho # though ignored
	    update_str["e_old"] = msg.ER
            update_str["bn_old"] = msg.BN
	    update_str["s_old"] = self.get_state(msg.id_)
            pass
	self.FR[msg.id_] = float(msg.ER)
	self.BN[msg.id_] = msg.BN
	if self.BN[msg.id_] == self.id_:
	    self.move_to_B(msg.id_)
	else:
	    self.move_to_U(msg.id_)
	    pass
            
	key = "update_rho_rvs(%d)"% (msg.id_)
	update_str_keys.append(key)

	self.rho = self.update_rho(update_str, key)

        max_e = 0
        for u in self.U:
            if max_e is None\
              or self.FR[u] > max_e:
                max_e = self.FR[u]
                pass
            pass
        self.max_e = max_e

        if self.log:
	    update_str["b_new"] = self.rho # though ignored
	    update_str["e_new"] = msg.ER
            update_str["bn_new"] = msg.BN
	    update_str["s_new"] = self.get_state(msg.id_)
            pass
            
	if self.log: print "update," + ",".join([str(update_str[k]) for k in update_str_keys])
	pass

	
	

class Source:
    def __init__(self):
	self.alg = "skivee"	       
	self.pending_leave = False
	self.curr_time = -1
	self.last_request = 0
	return

    def set_time(self, curr_time):
	self.curr_time = curr_time

    def get_actual_rate_bps(self):
	return self.last_request

    def get_last_request(self):
	return self.last_request
	
    def get_last_min_alloc(self):
	return self.last_request
	
    def start_flow(self, msg):
	msg.dir_ = "fwd"
	msg.ER = float('inf')
	msg.BN = -1
	return

    def process_reverse(self, msg):
	self.last_request = msg.ER
	return

    def prepared_to_stop(self):
	return self.pending_leave	 

    def prepare_to_stop(self):
	assert(self.pending_leave == False)
	self.pending_leave = True
	return

class Destination:
    def __init__(self):
	self.alg = "skivee"
	self.curr_time = -1
	return

    def set_time(self, curr_time):
	self.curr_time = curr_time
	return

    def process_forward(self, msg):
	msg.dir_ = "rvs"
	return

class Message:
    def __init__(self):
	self.alg = "skivee"	       
	# self.RR = 0 # Reserved Rate is 0
	# self.W = 1 # weight is 1
	self.ER = 0 # Expected Fair Rate
	self.BN = -1 # BottleNeck
	self.dir_ = "fwd"
	
	self.dropped = False
	self.stopped = False
	self.id_ = id(self)
	self.name_ = str(self.id_)

	pass

    def get_requested_rate(self):
	return self.ER
