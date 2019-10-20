# numerical-simulations
Python simulations comparing proactive algorithms, for SIGMETRICS'19 paper 

## Installation
I used Ubuntu 14.04 LTS on to run these simulations on multi-CPU servers.

Run ./dependencies.sh to install all python dependencies. Let me know if you discover any dependencies missing in this script. 

Install jupyter notebook separately to plot the results (you do not need anaconda).

## Running experiments
Use run_experiment.sh to run one of the four numerical experiments from the paper:
- sparse-ct : convergence times in sparse routing matrics
- dense-ct : convergence times in dense routing matrics
- robustness-approx : robustness of s-PERC to approximate division, using look-up tables with different parameters (N,m,l),
corresponding to different table sizes and errors.
- robustness-drop: robustness of s-PERC to packets drops for different drop-probabilities

The script will run experiments in parallel.
At the bottom of the scripts, you can set MAX_CPUS to control  how many experiments to run in parallel. 
I ran each experiment on its own server with MAX_CPUS set to 20. It can take one or two days to finish all the runs.
You can adjust START and END at the bottom of the script to run a subset of the runs.

## Plotting results
Use plot_experiment.ipynb to plot results from one of the four experiments.
Configure which experiment you want to plot in the second cell, and run all cells.
Boxplots of convergence times are saved as PDFs in the root directory.
