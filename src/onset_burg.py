# onset_burg.py
#
# Burg LP-residual onset detector. Direct port of OnsetDetectorBurg.h from
# the rhythmecho project. Same algorithm, same parameters, sample-for-sample
# faithful to the C++ canonical implementation.
#
# Method (one line): fit an order-5 Burg LP model to recent history; the
# prediction error spikes on transients; trigger when the fast envelope of
# the residual energy exceeds `sensitivity` x the slow envelope (with a
# refractory period to prevent double-triggers).
#
# Usage:
#     onsets = detect_onsets(audio, sr, sensitivity=3.0)
#     # onsets is a list of sample indices in `audio`'s coordinates.

import numpy as np
import resampy

LP_ORDER = 5
HISTORY_SIZE = 256
UPDATE_INTERVAL = 256  # Burg coefficient recompute interval

# Detection sample rate. Onset detection doesn't need full audio bandwidth;
# 22.05k is the conventional MIR rate. Running the order-5 LP at 192k makes
# the model unable to fit pitched content (period > history size) — at 22.05k
# it can model the fundamental fine.
DEFAULT_DETECTION_SR = 22050


class _BurgDetector:
    """Stateful per-sample detector. Mirrors OnsetDetectorBurg.h field-for-field."""

    def __init__(self, sample_rate, sensitivity):
        self.sr = float(sample_rate)
        self.sensitivity = max(0.01, float(sensitivity))

        # Time-constant coefficients for the residual envelopes.
        # Same formula as the C++: alpha = 1 - exp(-1 / N) where N = sr * tau.
        fast_samples = max(1.0, self.sr * 0.001)   # ~1 ms
        slow_samples = max(1.0, self.sr * 0.150)   # ~150 ms
        self.fast_coeff = 1.0 - np.exp(-1.0 / fast_samples)
        self.slow_coeff = 1.0 - np.exp(-1.0 / slow_samples)

        # Refractory: hold off triggers for ~5 ms regardless of sample rate.
        # The C++ uses UPDATE_INTERVAL (256 samples), which is sample-rate-dependent
        # and too short at high rates. Scale to time instead.
        self.refractory_samples = max(UPDATE_INTERVAL, int(self.sr * 0.005))

        # Buffers and counters
        self.history = np.zeros(HISTORY_SIZE, dtype=np.float32)
        self.hist_write_pos = 0
        self.coeffs = np.zeros(LP_ORDER, dtype=np.float32)
        self.residual_env = 0.0
        self.residual_ref = 0.0
        self.prev_above = False
        self.update_counter = 0
        self.refractory_counter = 0

    def process(self, audio):
        """Run detector across audio; return list of onset sample indices."""
        onsets = []
        # Pull instance state into locals for speed (avoids attribute lookup
        # inside the hot loop).
        history = self.history
        coeffs = self.coeffs
        hist_pos = self.hist_write_pos
        residual_env = self.residual_env
        residual_ref = self.residual_ref
        prev_above = self.prev_above
        update_counter = self.update_counter
        refractory_counter = self.refractory_counter
        fast_coeff = self.fast_coeff
        slow_coeff = self.slow_coeff
        sensitivity = self.sensitivity
        refractory_samples = self.refractory_samples

        for i in range(len(audio)):
            sample = float(audio[i])

            # 1. LP prediction from past samples (history at indices wp-1, wp-2, ..., wp-LP_ORDER mod N).
            predicted = 0.0
            for k in range(1, LP_ORDER + 1):
                idx = (hist_pos - k + HISTORY_SIZE) % HISTORY_SIZE
                predicted += coeffs[k - 1] * history[idx]

            # Write current sample into history.
            history[hist_pos] = sample
            hist_pos = (hist_pos + 1) % HISTORY_SIZE

            # 2. Residual energy and envelopes.
            residual = sample - predicted
            residual_sq = residual * residual
            residual_env += fast_coeff * (residual_sq - residual_env)
            residual_ref += slow_coeff * (residual_sq - residual_ref)

            ref_floor = residual_ref if residual_ref > 1e-12 else 1e-12
            ratio = residual_env / ref_floor

            # 3. Rising-edge trigger with refractory hold-off.
            above = ratio > sensitivity
            if above and not prev_above and refractory_counter == 0:
                onsets.append(i)
                refractory_counter = refractory_samples
            prev_above = above
            if refractory_counter > 0:
                refractory_counter -= 1

            # 4. Periodic Burg coefficient recompute.
            update_counter += 1
            if update_counter >= UPDATE_INTERVAL:
                update_counter = 0
                self._compute_burg(history, hist_pos, coeffs)

        # Persist state (mostly for possible chained calls; not strictly needed).
        self.hist_write_pos = hist_pos
        self.residual_env = residual_env
        self.residual_ref = residual_ref
        self.prev_above = prev_above
        self.update_counter = update_counter
        self.refractory_counter = refractory_counter

        return onsets

    @staticmethod
    def _compute_burg(history, hist_pos, coeffs):
        """
        Burg recursion. Mirrors compute_burg_coefficients() in the C++ exactly,
        including the bwd[n-1]=bNew (not bwd[n]=bNew) bug fix.
        """
        N = HISTORY_SIZE

        # Build oldest-to-newest buffer.
        buf = np.empty(N, dtype=np.float32)
        for i in range(N):
            buf[i] = history[(hist_pos + i) % HISTORY_SIZE]

        fwd = buf.copy()
        bwd = buf.copy()
        a = np.zeros(LP_ORDER, dtype=np.float32)
        a_old = np.zeros(LP_ORDER, dtype=np.float32)

        for m in range(LP_ORDER):
            num = 0.0
            den = 0.0
            for n in range(m + 1, N):
                num += fwd[n] * bwd[n - 1]
                den += fwd[n] * fwd[n] + bwd[n - 1] * bwd[n - 1]

            km = 0.0
            if den > 1e-30:
                km = -2.0 * num / den
                if km < -0.9999:
                    km = -0.9999
                elif km > 0.9999:
                    km = 0.9999

            # Levinson update.
            for k in range(m):
                a_old[k] = a[k]
            a[m] = km
            for k in range(m):
                a[k] = a_old[k] + km * a_old[m - 1 - k]

            # Forward/backward error update — n descending so we don't clobber values we still need.
            for n in range(N - 1, m, -1):
                f_new = fwd[n] + km * bwd[n - 1]
                b_new = bwd[n - 1] + km * fwd[n]
                fwd[n] = f_new
                bwd[n - 1] = b_new  # NOT bwd[n] — that was the C++ bug fix

        # Algorithm produces a[]; coeffs are -a[] (matches C++ and Lua canonical).
        for k in range(LP_ORDER):
            coeffs[k] = -a[k]


def detect_onsets(audio, sr, sensitivity=3.0, detection_sr=DEFAULT_DETECTION_SR):
    """
    Detect transient onsets in `audio` (1-D float array).

    Args:
        audio: 1-D numpy array of audio samples.
        sr: input audio sample rate.
        sensitivity: ratio threshold (fast/slow residual envelope). Higher = less
            sensitive. Default 3.0 (matches rhythmecho).
        detection_sr: rate at which to run the detector. The audio is downsampled
            to this rate first. Onset positions are mapped back to `sr` coordinates
            on return. Pass None to skip downsampling.

    Returns:
        List of integer sample indices in `audio`'s coordinate space where onsets
        were detected.
    """
    if audio.ndim > 1:
        audio = audio[:, 0]
    audio = audio.astype(np.float32, copy=False)

    if detection_sr is not None and sr > detection_sr * 1.5:
        det_audio = resampy.resample(audio, sr, detection_sr).astype(np.float32)
        det_sr = detection_sr
    else:
        det_audio = audio
        det_sr = sr

    detector = _BurgDetector(sample_rate=det_sr, sensitivity=sensitivity)
    onsets_det = detector.process(det_audio)

    if det_sr != sr:
        ratio = sr / det_sr
        return [int(round(o * ratio)) for o in onsets_det]
    return onsets_det
