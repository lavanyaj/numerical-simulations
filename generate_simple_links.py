import numpy as np
import argparse

parser = None
args = None
"""
example usage
 python files_to_run/gene*link*file.py --num_switches 10 --link_filename test-fully_connected-10-links.txt
"""
def parse_args_to_gen_links():
    global parser
    global args
    parser = argparse.ArgumentParser(description="arguments to generate links file")
    parser.add_argument("--link_filename", type=str, help="filename containing link config", default="links_files1.txt")
    parser.add_argument("--num_links", type=int)
    parser.add_argument("--longest_path", type=int)
    parser.add_argument("--min_capacity", type=int)
    parser.add_argument("--max_capacity", type=int)
    parser.add_argument("--seed_link_cap", type=int)
    parser.add_argument("--timeout_in_rtts", type=float)
    parser.add_argument("--division_N", type=int)#, default=0) 
    parser.add_argument("--division_l", type=int) #, default=0)
    parser.add_argument("--division_m", type=int) #, default=0)
    parser.add_argument("--sperc_precision", type=str) #, default="1e-7")
    parser.add_argument("--drop_probability", type=str) #, default="0")
    parser.add_argument("--rto", type=int) #, default=0)
    parser.add_argument("--max_num_rtts", type=int) #, default=200)
   
    args = parser.parse_args()

class GenerateLinksFile:
    def __init__(self, numLinks, longestPath, seed_link_cap, max_num_rtts):
        self.link_delay = 10
        self.check_rates_interval = 20        

        # counting up link and down link separately
        self.nlinks = numLinks
        self.shortest_rtt = 2 * self.link_delay
        self.longest_rtt = 2 * longestPath * self.link_delay
        self.frugal_timeout = int(round(self.longest_rtt*args.timeout_in_rtts))
        # max_num_rtts is 100 for robustness experiments and 200 otherwise
        self.max_microseconds = max_num_rtts * self.longest_rtt
        self.link_delay_noise = (100, 1e-12)
        self.max_consecutive_converged = 200 # not used, get_conv later
        self.drop_probability = args.drop_probability
        self.frugal_rto = args.rto * self.frugal_timeout
        self.prec =  [14, 1e-08, 1e-06, 1e-07, args.sperc_precision]
        self.division = "exact"
        if (args.division_N > 0):
            self.division = "lookup_table N %d l %d m %d" %\
            (args.division_N, args.division_l, args.division_m)
        self.prng_link_cap=np.random.RandomState(seed_link_cap)

        pass

    
    def writeToFile(self):
        self.link_file = args.link_filename    
    
        print ("writing to %s"%self.link_file)
        with open(self.link_file, "w") as f:
            f.write("nlinks %d\n" % self.nlinks)
            f.write("link_delay %d\n" %\
                    self.link_delay)
            f.write("shortest_rtt %d\n" %\
                    self.shortest_rtt)
            f.write("longest_rtt %d\n" %\
                    self.longest_rtt)
            f.write("check_rates_interval %d\n" %\
                    self.check_rates_interval)
            f.write("frugal_timeout %d\n" %\
                    self.frugal_timeout)
            f.write("max_microseconds %d\n" %\
                    self.max_microseconds)
            f.write("link_delay_noise %d %g\n" %\
                    (self.link_delay_noise[0],\
                     self.link_delay_noise[1]))
            f.write("max_consecutive_converged %d\n" %\
                    self.max_consecutive_converged)
            f.write("drop_probability %s\n" %\
                    self.drop_probability)
            f.write("frugal_rto %d\n" %\
                    self.frugal_rto)
            f.write("prec %s\n" %\
                    (" ".join([str(p) for p in self.prec])))
            f.write("%s\n" % self.division)
            # define a link index function
            # that takes in switch indices
            # and returns link index?
            c = {}
            # randint from lo (inclusive) to
            #  hi (exclusive)

            for i in range(self.nlinks):
                c[i] = self.prng_link_cap.randint(args.min_capacity,\
                                         args.max_capacity+1)
                pass

            indices = sorted(c.keys())
            i = 0
            for index in indices:
                assert(i == index)
                i += 1
                f.write("%f\n"%c[index])
                pass
            pass
        
def main1():
    parse_args_to_gen_links()
    assert(args.num_links is not None)
    assert(args.longest_path is not None)
    glf = GenerateLinksFile(args.num_links,\
                            args.longest_path, args.seed_link_cap, args.max_num_rtts)
    glf.writeToFile()

if __name__ == "__main__":
    main1()
