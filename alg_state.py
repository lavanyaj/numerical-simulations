import numpy as np

class AlgState:
    def __init__(self, num_flows, num_links, mpf_zero, mpf_inf):        
        self.SAT = 1
        self.UNSAT = 2        
        self.mpf_zero = mpf_zero
        self.mpf_inf = mpf_inf
        self.num_flows = num_flows
        self.num_links = num_links
        self.local_labels = np.ones((self.num_flows, self.num_links)) * -1
        self.local_rates = np.ones((self.num_flows, self.num_links)) * mpf_zero        
        self.message_requested_rate = np.ones((self.num_flows,1)) * mpf_zero
        self.message_alloc_at_bottleneck_link = np.ones((self.num_flows,1)) * mpf_zero
        self.message_min_alloc_at_any_link = np.ones((self.num_flows,1)) * mpf_zero
        self.message_bottleneck_link = np.ones((self.num_flows,1)) * -1
        self.source_latest_min_alloc = np.ones((self.num_flows,1)) * mpf_zero
        self.source_latest_requested_bandwidth = np.ones((self.num_flows,1)) * mpf_zero

        self.bottleneck_levels = np.ones((self.num_links,1)) * mpf_zero
        self.maxsat = np.ones((self.num_links,1)) * mpf_zero
        self.demands = np.ones((self.num_flows,1)) * mpf_zero
        self.rates = np.ones((self.num_links,1)) * mpf_zero # residual rates        
        return
    
