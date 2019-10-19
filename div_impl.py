#!/usr/bin/env python

"""
When using as lookup table based division module

This module implements integer division using the fact that:
A/B = exp(log(A) - log(B))

Involves:
  - 2 ternary match table lookups to approximate log(A) and log(B)
  - integer subtraction to compute: diff = log(A) - log(B)
  - 1 exact match table lookup to approximate: exp(diff)

API - 2 functions:
  1. make_tables() - sets up the log_table and exp_table
  2. divide(a,b) - performs the approximate integer division

When using as synthetic approximate division module
This module implements floating point division and adds Gaussian noise

API - 1 function:
  2. divide(a,b) - performs the approximate floating point division

"""

import sys, os
from math import exp, log
import numpy as np

"""
N=16, m=6, l=9 gives these results:
len(log_table) =  383
total_mem = 1885.75 bytes
Mean Error: 1%

N=32, m=6, l=10 gives these results:
len(log_table) =  895
total_mem = 
Mean Error: 1%

N=32, m=4, l=8 gives these results:
len(log_table) =  239
total_mem = 
Mean Error: 5%

N=32, m=3, l=7 gives these results:
len(log_table) =  123
total_mem = 
Mean Error: 10%
"""

N = 32
m = 10 #3
l = 16 #4

meanError = 0.20 # 1% error
prng = np.random.RandomState(123)
absCutoff = None

wLookupTable = True

initialized = False
err_max = [0,0,0]
err_total = 0
err_num = 0

log_table = []
exp_table = []


    

def gen_log_keys():
    keys = []
    fmat_key = '{:0%db}' % N
    for key in range(1,2**m):
        key_str = fmat_key.format(key)
        keys.append(key_str)

    fmat_sub_key = '{:0%db}' % m
    for i in range(1, N-m+1):
        for k in range(2**(m-1), 2**m):
            key_str = '0'*(N-m-i) + fmat_sub_key.format(k) + 'X'*i
            keys.append(key_str)
    return keys

"""
Input
-----
keys: list of strings of the form '010XX'

Generates entries of form: (addr, data, mask, val)

NOTE: Assumes the X's are all at the end
"""
def gen_log_entries(keys):
    global log_table, exp_table
    addr = 0
    for key in keys:
        wc_len = key.count('X')
        mask_len = len(key) - wc_len
        mask = (2**mask_len -1) << wc_len
        data = int(key.replace('X','0'),2)
        avg = find_avg(key)
        val = f_log(avg)
        log_table.append((addr, data, mask, val))
        addr += 1

"""
Find the average value covered by the data & mask

i.e. 011X => (6+7)/2 = 6.5
"""
def find_avg(key):
    min_val = int(key.replace('X','0'),2)
    max_val = int(key.replace('X','1'),2)
    return (min_val + max_val)/2.0

def f_log(x):
    return int(round(log(x)/log(2**N-1)*(2**l-1)))

"""
Finds the appropriate match in the log_table for input integer x
"""
def apply_log_table(x):
    for (addr, data, mask, val) in log_table:
        if data == (x & mask):
            return val
    sys.stderr.write("ERROR: could not find match in log_table for input " + str(x) + "\n")
    sys.exit(1)

def print_log_table():
    print ("log_table:")
    print ("----------")
    for (data, mask), val in log_table.items():   
        fmat = "({:0%db}, {:0%db}) ==> {}" % (N, N)
        print (fmat.format(data, mask, val))
    print ("len(log_table) = " + str(len(log_table)))

"""
Generates the entries for the exp_table.

Exact match table mapping [0, 2^l-1] => [0, 2^N-1]
"""
def gen_exp_entries():
    global log_table, exp_table
    for key in range(2**l):
        exp_table.append((key, f_log_inv(key)))

def f_log_inv(x):
    return int(round(exp((x/(2**l-1.0))*log(2**N-1))))

def apply_exp_table(x):
    assert(x < len(exp_table))
    entry = exp_table[x]
    assert(entry[0] == x)
    return entry[1]
    #for (key, val) in exp_table:
    #    if key == x:
    #        return val
    sys.stderr.write("ERROR: could not find match in exp_table for input " + str(x) + "\n")
    sys.exit(1)

def print_exp_table():
    print ("exp_table:")
    print ("----------")
    for (key, val) in exp_table:
        print ("{} ==> {}".format(key, val))
    print ("len(exp_table) = " + str(len(exp_table)))

def check_size(x):
    try:
        assert(len(bin(x))-2 <= N)
    except:
        sys.stderr.write("ERROR: %s cannot be represented in %s bits\n" % (str(x), str(N)))
        sys.exit(1)

def make_tables():
    global log_table, exp_table
    log_table = []
    exp_table = []
    keys = gen_log_keys()
    gen_log_entries(keys)
    gen_exp_entries()
    print ("N" + str(N) + ", l" + str(l) + ", m" + str(m))
    print ("# len(log_table) = " + str(len(log_table)))
    print ("# len(exp_table) = " + str(len(exp_table)))


def get_gaussian():
    gaussian = prng.normal() * meanError
    if absCutoff is not None:
        minVal = -absCutoff
        maxVal = absCutoff
        if (gaussian > maxVal):
            gaussian = maxVal
        elif (gaussian < minVal):
            gaussian = minVal
    return gaussian

def lookup_table_divide(a,b):
    check_size(a)
    check_size(b)

    if (a == 0 or b == 0 or b > a):
        return 0

    log_a = apply_log_table(a)
    log_b = apply_log_table(b)
    return apply_exp_table(log_a-log_b)

def divide(a,b):
    return lookup_table_divide(a,b)

def sperc_divide(cap, flows, cap_range, max_flows):
    global N
    global initialized
    assert(initialized)
    max_a = 2**(N-2)
    # check capacity expressed as N-bit int greater than max_flows, which we use as is
    # since lookup table arguments should be a, b where a> b
    # assert(cap_range[0] * max_a > max_flows) 
    #assert(cap >= cap_range[0]) # cap_range[0] = 1e-5, cap should never get this low    
    #if (abs(cap - cap_range[1]) < 1e-7): cap = cap_range[1]
    
    if not(cap <= cap_range[1]):
        if False: print ("sperc_divide got cap="+str(cap)+", flows="+str(flows)\
               +",cap_range="+str(cap_range)+", max_flows="+str(max_flows)\
               +" but cap > cap_range[1]")
    #assert(cap <= cap_range[1])
    
    a = int(round((cap / cap_range[1]) * (max_a-1)))
    b = flows
    true = float(cap) / flows

    def print_error():
        if False: sys.stderr.write("sperc_divide got cap="+str(cap)+", flows="+str(flows)\
               +",cap_range="+str(cap_range)+", max_flows="+str(max_flows)\
               +" so ((cap / cap_range[]))="  + str(round(cap / cap_range[1]))\
               +"  .. times (max_a-1)=" + str((cap / cap_range[1]) * (max_a-1))\
               + " .. rounded=" + str(round((cap / cap_range[1]) * (max_a-1)))\
                         + " .. int=" + str(a)\
                         + " lookup_result=a/b="+str(a)+"/"+str(b)\
                         + " final_result="+str(final_result)\
                         + " true="+str(true))
        pass

        

    lookup_result =  divide(a,b)
    final_result = (float(lookup_result) / (max_a-1)) * cap_range[1]
    #if (final_result <= cap_range[0]): final_result = cap_range[0]
    
    if cap == 0 or lookup_result == 0 or final_result == 0 or final_result < cap_range[0]:
        print_error()
        #sys.exit()    
        pass
    
    #assert(final_result > cap_range[0])    
    est = final_result
    if (true < 1e-7  and abs(true-est) < 1e-7): err = 0
    elif (true < 1e-7): err = float('inf')
    else: err = abs(true-est)/true
         
    global err_max
    global err_total
    global err_num
    if err > err_max[0]: err_max = [err, cap, flows]

    err_total += err
    err_num += 1
    
    return final_result
    

def initialize(divN, divm, divl):
    global N
    global m
    global l
    global initialized
    
    N = divN
    m = divm
    l = divl
    
    make_tables()
    initialized = True
#make_tables()
