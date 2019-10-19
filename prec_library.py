import numpy as np
#import mpmath
import sys

class PrecisionLibrary:
    # wf/cpg/alg uses eps1, conv uses eps2, warnings use eps3
    def __init__(self, prec, eps1, eps2, eps3, eps4):
        self.mpf_zero = 0
        self.mpf_inf = float('inf')
        self.mpf_one = 1.0
        self.prec = prec
        self.eps1 = eps1
        self.eps2 = eps2
        self.eps3 = eps3
        self.eps4 = eps4
        self.mpf_mode = False
 
       # if self.prec >= 15:
       #      self.mpf_mode = True
       #      mpmath.mp.dps = self.prec
       #      self.mpf_zero = mpmath.mpf(0)
       #      self.mpf_inf = mpmath.mpf('inf')
       #      self.mpf_one = mpmath.mpf(1)
       #      self.eps1 = mpmath.mpf(eps1)
       #      self.eps2 = mpmath.mpf(eps2)
       #      self.eps3 = mpmath.mpf(eps3)
       #      self.eps4 = mpmath.mpf(eps4)
       #  else:
       #      assert(eps1 >= 1e-14)
       #      assert(eps2 >= 1e-14)
       #      assert(eps3 >= 1e-14)
       #      assert(eps4 >= 1e-14)
    def get_diff(self, opt, act, name="", log=False):
        assert(opt.shape == act.shape)
        diff = np.ones(act.shape) * self.mpf_inf
        finite_indices = np.where((opt < self.mpf_inf) & (act < self.mpf_inf))[0]
        both_inf = np.where((opt == self.mpf_inf) & (act == self.mpf_inf))[0]
        one_inf = np.where((opt == self.mpf_inf) ^ (act == self.mpf_inf))[0]
                
        diff[finite_indices] = abs(opt[finite_indices] - act[finite_indices])
        diff[one_inf] = self.mpf_inf
        diff[both_inf] = self.mpf_zero

        return diff

    def get_rel_diff(self, opt, act, name="", log=False):
        if not(opt.shape == act.shape):
            print >> sys.stderr, "ERROR: getting relative diff for ", name, " but opt has different shape from act", opt.shape, "v/s", act.shape
        assert(opt.shape == act.shape)
        diff = np.ones(act.shape) * self.mpf_inf
        finite_indices = np.where((opt < self.mpf_inf) & (act < self.mpf_inf))[0]
        both_inf = np.where((opt == self.mpf_inf) & (act == self.mpf_inf))[0]
        one_inf = np.where((opt == self.mpf_inf) ^ (act == self.mpf_inf))[0]
        opt_finite = opt[finite_indices]
        act_finite = act[finite_indices]
        # relative error is relative to optimal (not necessarily the larger number)
        # larger_finite = np.where(opt_finite > act_finite, opt_finite, act_finite)
        # error of a finite number is inf relative to 0, say
        # diff[finite_indices] = np.where(larger_finite > self.mpf_zero, abs(opt_finite - act_finite)/larger_finite, self.mpf_inf)
        diff[finite_indices] = np.where(opt_finite > self.mpf_zero, abs(opt_finite - act_finite)/opt_finite, self.mpf_inf)
        diff[one_inf] = self.mpf_inf
        diff[both_inf] = self.mpf_zero
        return diff
        
    def mpf(self, num):
        if self.mpf_mode:
            return mpmath.mpf(num)
        else:
            return num

    def nstr(self, num):
        if self.mpf_mode:
            return mpmath.nstr(num, 4)
        else:
            return "%.4f"%num
