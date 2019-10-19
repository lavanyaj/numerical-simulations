import argparse
import numpy as np

parser = None
args = None
"""
example usage

python files_to_run/generate_flows_file.py --num_switches 10 --num_flows 400 --num_sims 10 --change_flows 4 --flow_filename test-fully_connected-10-400flows-change4.txt

How to pick num_flows?
Say we want given flows_per_link on average
 average number of links in a flow's path's path_length= 0.5* (num_switches-1)
 path_length * num_flows = flows_per_link * num_links
"""
def parse_args_to_gen_flows():
    global parser
    global args
    parser = argparse.ArgumentParser(description="arguments to generate flows file")
    parser.add_argument("--seed_stop_flows", type=int)
    parser.add_argument("--seed_path_len", type=int)
    parser.add_argument("--seed_path_links", type=int)

    parser.add_argument("--num_links", type=int)
    parser.add_argument("--num_flows", type=int)
    parser.add_argument("--longest_path", type=int)
    parser.add_argument("--shortest_path", type=int)
    
    parser.add_argument("--num_sims", type=int)
    parser.add_argument("--change_flows", type=int)
    parser.add_argument("--flow_filename", type=str, help="filename containing flow config", default="flow_files.txt")
    args = parser.parse_args()
    pass

class GenerateFlowsFile:
    def __init__(self):
        self.prng_stop_flows = np.random.RandomState(args.seed_stop_flows)
        # used for picking flows to remove
        self.prng_path_len = np.random.RandomState(args.seed_path_len)
        # used for picking flows to remove and start
        self.prng_path_links = np.random.RandomState(args.seed_path_links)
        # used to pick random lengths for flows (when fixed length is false)

        pass

    
    def simple(self, numFlows, numLinks, longestPath, shortestPath, changeFlows, numSims):
        self.numFlows = numFlows
        trafficMatrix = np.zeros((numLinks))
        flowNum = 0
        simNum = 0
        activeFlows = {}
        with open(args.flow_filename, "w") as f:
            while simNum < numSims:                            
                if (simNum) == 0: 
                    flowsToAdd = numFlows
                    flowsToStop = 0
                    print ("sim %d add %d stop %d curr %d" % (simNum, flowsToAdd, flowsToStop, len(activeFlows)))
                else:
                    flowsToAdd = changeFlows
                    flowsToStop = changeFlows
                    activeFlowIds = sorted(activeFlows.keys())
                    print ("sim %d add %d stop %d curr %d" % (simNum, flowsToAdd, flowsToStop, len(activeFlows)))
                    pass


                if flowsToStop > 0:
                    sample= self.prng_stop_flows.choice\
                            (len(activeFlowIds),\
                             flowsToStop,\
                            replace=False)
                    for s in sample:
                        delFlowNum = activeFlowIds[s]
                        f.write("%d 0 %d\n" %\
                                (simNum, 
                                 delFlowNum))
                        del activeFlows[delFlowNum]
                        pass
                    activeFlowIds = None
                    pass

                for i in range(flowsToAdd):
                    # randint from lo (inclusive) to hi (exclusive)
                    assert(longestPath >= 1)
                    numLinksInPath=self.prng_path_len.randint(shortestPath,\
                                                              longestPath+1)
                    # numLinksInPath samples are drawn
                    path = self.prng_path_links.choice(range(numLinks),\
                                                       numLinksInPath, replace=False)
                    assert(len(path) == numLinksInPath)
                    pathStr = " ".join([str(p) for p in path])

                    # add flows
                    activeFlows[flowNum] = True
                    f.write("%d 1 %d %d %s\n"% (simNum, flowNum, numLinks, pathStr))
                    flowNum += 1
                    pass
                    # replace 10\% of flows
                pass
                simNum += 1
            pass
        pass

def main():
    parse_args_to_gen_flows()
    gff = GenerateFlowsFile()
    assert(args.num_links is not None)        
    assert(args.num_flows is not None)
    assert(args.longest_path is not None)
    assert(args.change_flows is not None)
    assert(args.num_sims is not None)
    gff.simple\
        (numFlows=args.num_flows,\
         numLinks=args.num_links,\
         longestPath=args.longest_path,\
         shortestPath=args.shortest_path,\
         changeFlows=args.change_flows,\
         numSims=args.num_sims)

print __name__
if __name__ == "__main__":
    main()
