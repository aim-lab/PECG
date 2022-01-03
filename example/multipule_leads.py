from pebm import Preprocessing as Pre
from pebm.ebm import FiducialPoints as Fp
from pebm.ebm import Biomarkers as Obm
import matplotlib.pyplot as plt
import scipy.io as spio
from scipy.fft import fft, ifft, fftshift
import numpy as np

ecg_mat = spio.loadmat('/home/sheina/pebm/example/TNMG_example0.mat')

freq = 400;
signal = ecg_mat['signal']

pre = Pre.Preprocessing(signal, freq)
bsqi = pre.bsqi()
f_notch = 60
fsig =pre.notch(f_notch)
fsig= pre.bpfilt()


matlab_pat= '/usr/local/MATLAB/R2021a'

fp = Fp.FiducialPoints(signal, freq)
peaks = fp.epltd()
peaks = fp.xqrs()
fiducials = fp.wavedet(matlab_pat)

obm = Obm.Biomarkers(signal, freq, fiducials=fiducials,matlab_path=matlab_pat)
ints, stat_i = obm.intervals()
waves, stat_w = obm.waves()




