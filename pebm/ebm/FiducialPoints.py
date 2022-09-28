import math
import numpy as np
import os
import scipy.signal as sc_signal
import tempfile
import wfdb
from wfdb import processing

from pebm._ErrorHandler import _check_shape_, WrongParameter
from pebm.ebm.c_files.EpltdAll import epltd_all
from pebm.ebm.wavedet_exe.Wavdet import wavdet


class FiducialPoints:
    def __init__(self, signal: np.array, fs: int, n_pools: int = 1):
        """
        The purpose of the FiducialPoints class is to calculate the fiducial points.

        :param signal: The ECG signal as a two-dimensional ndarray, when the first dimension is the len of the ecg, and the second is the number of leads.
        :param fs: The sampling frequency of the signal.
        :param peaks: The indexes of the R- points of the ECG signal – optional input.
        :param n_pools: The number of cores to use when calculating the fiducials.
        """
        if fs <= 0:
            raise WrongParameter("Sampling frequency should be strictly positive")
        _check_shape_(signal, fs)

        self.signal = signal
        self.fs = fs
        self.peaks = []
        if n_pools is None:
            self.n_pools = 1
        else:
            self.n_pools = n_pools

    def wavedet(self, matlab_pat: str = None, peaks: np.array = np.array([])):
        """
        The wavedat function uses the matlab algorithm wavedet, compiled for python.
        The algorithm is described in the following paper:
        Martinze at el (2004),
        A wavelet-based ECG delineator: evaluation on standard databases.
        IEEE Transactions on Biomedical Engineering, 51(4), 570-581.

        :param peaks: Optional input- Annotation of the reference peak detector (Indices of the peaks). If peaks are not given,
         the peaks are calculated with epltd detector.
        :param matlab_pat: Optional input- required when running on a linux machine.

        :returns:
            *fiducials: Dictionary that includes indexes for each fiducial point.
        """

        signal = self.signal
        fs = self.fs

        try:
            cwd = os.getcwd()
            fl = 1
        except:
            print("Not exists current path")
            fl = 0

        if len(np.shape(signal)) == 2:
            [ecg_len, ecg_num] = np.shape(signal)
        elif len(np.shape(signal)) == 1:
            ecg_num = 1
        if peaks.size == 0:
            peaks = self.epltd

        self.peaks = peaks

        fiducials_mat = wavdet(signal, fs, peaks, matlab_pat)
        keys = [
            "Pon",
            "P",
            "Poff",
            "QRSon",
            "Q",
            "qrs",
            "S",
            "QRSoff",
            "Ton",
            "T",
            "Toff",
            "Ttipo",
            "Ttipoon",
            "Ttipooff",
        ]
        position = fiducials_mat["output"]
        all_keys = fiducials_mat["output"].dtype.names
        fiducials = {}

        num_ecg = np.size(position)
        for j in np.arange(num_ecg):
            position_values = []
            position_keys = []
            for i, key in enumerate(all_keys):
                ret_val = position[0, j][i].squeeze()
                if keys.__contains__(key):
                    if len(ret_val[np.isnan(ret_val)]):
                        ret_val[np.isnan(ret_val)] = np.nan
                    ret_val = np.asarray(ret_val)
                    position_values.append(ret_val)
                    position_keys.append(key)
            # -----------------------------------

            fiducials[j] = dict(zip(position_keys, position_values))
        if fl:
            os.chdir(cwd)
        return fiducials

    @property
    def epltd(self):
        """
        This function calculates the indexes of the R-peaks with epltd peak detector algorithm.
        This algorithm were introduced by Pan, Jiapu; Tompkins, Willis J. (March 1985).
        "A Real-Time QRS Detection Algorithm". IEEE Transactions on Biomedical Engineering.
        BME-32 (3): 230–236

        :return: indexes of the R-peaks in the ECG signal.
        """
        try:
            cwd = os.getcwd()
            fl = 1
        except:
            fl = 0

        signal = self.signal
        fs = self.fs

        if len(np.shape(signal)) == 2:
            [ecg_len, ecg_num] = np.shape(signal)
            size_peaks = np.zeros([1, ecg_num]).squeeze()
            peaks_dict = {}
            for i in np.arange(0, ecg_num):
                peaks_dict[str(i)] = epltd_all(signal[:, i], fs)
                size_peaks[i] = len(peaks_dict[str(i)])
            max_sp = int(np.max(size_peaks))
            peaks = np.zeros([max_sp, ecg_num])
            for i in np.arange(0, ecg_num):
                peaks[: int(size_peaks[i]), i] = peaks_dict[str(i)]
        elif len(np.shape(signal)) == 1:
            ecg_num = 1
            peaks = epltd_all(signal, fs)

        if fl:
            os.chdir(cwd)

        return peaks

    def xqrs(self):

        signal = self.signal
        fs = self.fs

        if len(np.shape(signal)) == 2:
            [ecg_len, ecg_num] = np.shape(signal)
            size_peaks = np.zeros([1, ecg_num]).squeeze()
            peaks_dict = {}
            for i in np.arange(0, ecg_num):
                signali = signal[:, i]
                peaks_dict[str(i)] = calculate_xqrs(signali, fs)
                size_peaks[i] = len(peaks_dict[str(i)])
            max_sp = int(np.max(size_peaks))
            peaks = np.zeros([max_sp, ecg_num])
            for i in np.arange(0, ecg_num):
                peaks[: int(size_peaks[i]), i] = peaks_dict[str(i)]
        elif len(np.shape(signal)) == 1:
            ecg_num = 1
            peaks = calculate_xqrs(signal, fs)
        self.peaks = peaks
        return peaks

    def jqrs(self):

        signal = self.signal
        fs = self.fs
        thr = 0.8
        rp = 0.25
        if len(np.shape(signal)) == 2:
            [ecg_len, ecg_num] = np.shape(signal)
            size_peaks = np.zeros([1, ecg_num]).squeeze()
            peaks_dict = {}
            for i in np.arange(0, ecg_num):
                signali = signal[:, i]
                peaks_dict[str(i)] = calculate_jqrs(signali, fs, thr, rp)
                size_peaks[i] = len(peaks_dict[str(i)])
            max_sp = int(np.max(size_peaks))
            peaks = np.zeros([max_sp, ecg_num])
            for i in np.arange(0, ecg_num):
                peaks[: int(size_peaks[i]), i] = peaks_dict[str(i)]
        elif len(np.shape(signal)) == 1:
            ecg_num = 1
            peaks = calculate_jqrs(signal, fs, thr, rp)
        self.peaks = peaks
        return peaks


def calculate_xqrs(signal, fs, n_pools=10):
    try:
        cwd = os.getcwd()
        fl = 1
    except:
        print("Not exists current path")
        fl = 0
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.chdir(tmpdirname)
        wfdb.wrsamp(
            record_name="temp",
            fs=np.asscalar(np.uint(fs)),
            units=["mV"],
            sig_name=["V5"],
            p_signal=signal.reshape(-1, 1),
            fmt=["16"],
        )
        record = wfdb.rdrecord(tmpdirname + "/temp")
        ecg = record.p_signal[:, 0]
        pool_to_close = False
        if n_pools > 1:
            if pool is None:
                pool = multiprocessing.Pool(n_pools)
                pool_to_close = True
            borders = np.round(np.linspace(0, len(ecg), n_windows + 1)).astype(int)
            ecg_wins = [
                ecg[borders[i] : borders[i + 1]] for i in range(len(borders) - 1)
            ]
            lengths = np.array([len(e) for e in ecg_wins])
            ecg_wins = [np.tile(e, 2) for e in ecg_wins]
            fss = fs * np.ones(n_windows)
            sampfrom = np.zeros(n_windows, dtype=int)
            sampto = "end" * np.ones(n_windows, dtype=object)
            conf = np.array([None] * n_windows)
            learn = True * np.ones(n_windows, dtype=bool)
            verbose = False * np.ones(n_windows, dtype=bool)
            res = pool.starmap(
                processing.xqrs_detect,
                zip(ecg_wins, fss, sampfrom, sampto, conf, learn, verbose),
            )
            res = [res[i][res[i] > lengths[i]] - lengths[i] for i in range(len(res))]
            xqrs = np.concatenate(
                tuple([res[i] + borders[i] for i in range(n_windows)])
            ).astype(int)
            if pool_to_close:
                pool.close()
        else:
            xqrs = processing.xqrs_detect(ecg, fs, verbose=True)

    if fl:
        os.chdir(cwd)
    return xqrs


def calculate_jqrs(signal, fs, thr, rp):
    """The function is an Implementation of an energy based qrs detector [1]_. The algorithm is an
    adaptation of the popular Pan & Tompkins algorithm [2]_. The function assumes
    the input ecg is already pre-filtered i.e. bandpass filtered and that the
    power-line interference was removed. Of note, NaN should be represented by the
    value -32768 in the ecg (WFDB standard).
    .. [1] Behar, Joachim, Alistair Johnson, Gari D. Clifford, and Julien Oster.
        "A comparison of single channel fetal ECG extraction methods." Annals of
        biomedical engineering 42, no. 6 (2014): 1340-1353.
    .. [2] Pan, Jiapu, and Willis J. Tompkins. "A real-time QRS detection algorithm."
        IEEE Trans. Biomed. Eng 32.3 (1985): 230-236.
    :param signal: vector of ecg signal amplitude (mV)
    :param fs: sampling frequency (Hz)
    :param thr: threshold (nu)
    :param rp: refractory period (sec)
    :param debug: plot results (boolean)
    :return: qrs_pos: position of the qrs (sample)
    """
    try:
        cwd = os.getcwd()
        fl = 1
    except:
        print("Not exists current path")
        fl = 0
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.chdir(tmpdirname)
        wfdb.wrsamp(
            record_name="temp",
            fs=np.asscalar(np.uint(fs)),
            units=["mV"],
            sig_name=["V5"],
            p_signal=signal.reshape(-1, 1),
            fmt=["16"],
        )
        record = wfdb.rdrecord(tmpdirname + "/temp")
        ecg = record.p_signal[:, 0]
        INT_NB_COEFF = int(np.round(7 * fs / 256))  # length is 30 for fs=256Hz
        dffecg = np.diff(ecg)  # differenciate (one datapoint shorter)
        sqrecg = np.square(dffecg)  # square ecg
        intecg = sc_signal.lfilter(
            np.ones(INT_NB_COEFF, dtype=int), 1, sqrecg
        )  # integrate
        mdfint = intecg
        delay = math.ceil(INT_NB_COEFF / 2)
        mdfint = np.roll(
            mdfint, -delay
        )  # remove filter delay for scanning back through ecg
        # thresholding
        mdfint_temp = mdfint
        mdfint_temp_ = np.delete(
            mdfint_temp, np.where(ecg == -32768)
        )  # exclude the NaN (encoded in WFDB format)
        xs = np.sort(mdfint_temp)
        ind_xs = int(np.round(98 / 100 * len(xs)))
        en_thres = xs[ind_xs]
        poss_reg = mdfint > thr * en_thres
        tm = np.arange(start=1 / fs, stop=(len(ecg) + 1) / fs, step=1 / fs).reshape(
            1, -1
        )
        # search back
        SEARCH_BACK = 1
        if SEARCH_BACK:
            indAboveThreshold = np.where(poss_reg)[
                0
            ]  # indices of samples above threshold
            RRv = np.diff(tm[0, indAboveThreshold])  # compute RRv
            medRRv = np.median(RRv[RRv > 0.01])
            indMissedBeat = np.where(RRv > 1.5 * medRRv)[0]  # missed a peak?
            # find interval onto which a beat might have been missed
            indStart = indAboveThreshold[indMissedBeat]
            indEnd = indAboveThreshold[indMissedBeat + 1]
            for i in range(0, len(indStart)):
                # look for a peak on this interval by lowering the energy threshold
                poss_reg[indStart[i] : indEnd[i]] = mdfint[indStart[i] : indEnd[i]] > (
                    0.25 * thr * en_thres
                )
        # find indices into boudaries of each segment
        left = np.where(np.diff(np.pad(1 * poss_reg, (1, 0), "constant")) == 1)[
            0
        ]  # remember to zero pad at start
        right = np.where(np.diff(np.pad(1 * poss_reg, (0, 1), "constant")) == -1)[
            0
        ]  # remember to zero pad at end
        nb_s = len(left < 30 * fs)
        loc = np.zeros([1, nb_s], dtype=int)
        for j in range(0, nb_s):
            loc[0, j] = np.argmax(np.abs(ecg[left[j] : right[j] + 1]))
            loc[0, j] = int(loc[0, j] + left[j])
        sign = np.median(ecg[loc])
        # loop through all possibilities
        compt = 0
        NB_PEAKS = len(left)
        maxval = np.zeros([NB_PEAKS])
        maxloc = np.zeros([NB_PEAKS], dtype=int)
        for j in range(0, NB_PEAKS):
            if sign > 0:
                # if sign is positive then look for positive peaks
                maxval[compt] = np.max(ecg[left[j] : right[j] + 1])
                maxloc[compt] = np.argmax(ecg[left[j] : right[j] + 1])
            else:
                # if sign is negative then look for negative peaks
                maxval[compt] = np.min(ecg[left[j] : right[j] + 1])
                maxloc[compt] = np.argmin(ecg[left[j] : right[j] + 1])
            maxloc[compt] = maxloc[compt] + left[j]
            # refractory period - has proved to improve results
            if compt > 0:
                if (maxloc[compt] - maxloc[compt - 1] < fs * rp) & (
                    np.abs(maxval[compt]) < np.abs(maxval[compt - 1])
                ):
                    maxval = np.delete(maxval, compt)
                    maxloc = np.delete(maxloc, compt)
                elif (maxloc[compt] - maxloc[compt - 1] < fs * rp) & (
                    np.abs(maxval[compt]) >= np.abs(maxval[compt - 1])
                ):
                    maxval = np.delete(maxval, compt - 1)
                    maxloc = np.delete(maxloc, compt - 1)
                else:
                    compt = compt + 1
            else:
                # if first peak then increment
                compt = compt + 1
        qrs_pos = maxloc  # datapoints QRS positions
    if fl:
        os.chdir(cwd)
    return qrs_pos
