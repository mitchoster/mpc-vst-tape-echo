/* Port-local offline check (not upstream): every one of the 12 head/reverb modes
 * renders audible output, and the modes that include the spring (+R and Rev-only)
 * leave a decaying tail. Complements tests/test_dsp.cpp, which checks single paths.
 *
 *   g++ -O2 -std=c++17 tests/modes_render.cpp src/ported/core/TapeEchoDSP.cpp \
 *       -Isrc/ported/core -Isrc/ported/shared-dpf/dsp -lm -lpthread
 */
#include <cmath>
#include <cstdio>
#include <cstring>
#include "TapeEchoDSP.hpp"

using duskaudio::TapeEchoDSP;

static constexpr int N = 128;
static constexpr double Fs = 44100.0;

int main() {
    int fails = 0;
    for (int mode = 1; mode <= 12; ++mode) {
        TapeEchoDSP d;
        d.prepare(Fs, N);
        d.reset();
        d.setMode(mode);
        d.setRepeatRate(0.5f);
        d.setIntensity(0.45f);
        d.setEchoLevel(1.0f);
        d.setReverbLevel(0.6f);
        d.setMix(1.0f);          /* wet only: the initial dry leak is gone */
        d.setInputGain(0.7f);
        d.setWowFlutter(0.0f);
        d.setTapeAge(0.0f);
        d.setPingPong(false);

        float L[N], R[N];
        const float *in[2] = { L, R };
        float *out[2] = { L, R };

        /* let the per-sample smoothers glide to their targets */
        for (int b = 0; b < 128; ++b) {
            memset(L, 0, sizeof L);
            memset(R, 0, sizeof R);
            d.processBlock(in, out, 2, N);
        }

        double peak = 0, tailEnergy = 0;
        int lastTail = -1;
        const int blocks = 400;
        for (int b = 0; b < blocks; ++b) {
            memset(L, 0, sizeof L);
            memset(R, 0, sizeof R);
            if (b == 0) L[0] = R[0] = 0.8f;   /* single-sample impulse */
            d.processBlock(in, out, 2, N);
            for (int i = 0; i < N; ++i) {
                const double a = fabs((double)L[i]);
                if (a > peak) peak = a;
                if (b > 10 && a > 1e-5 && b > lastTail) lastTail = b;
                if (b > 10) tailEnergy += (double)L[i] * (double)L[i];
            }
        }

        const bool reverbMode = (mode >= 5 && mode <= 12);   /* R modes + Rev-only */
        printf("mode %2d %-5s peak=%.4f tail_energy=%.3e last_tail_block=%d\n",
               mode, reverbMode ? "(+R)" : "", peak, tailEnergy, lastTail);
        if (peak < 1e-3) { printf("  FAIL: mode %d renders (near) silence\n", mode); ++fails; }
        if (reverbMode && tailEnergy < 1e-6) { printf("  FAIL: mode %d has no spring tail\n", mode); ++fails; }
    }
    printf(fails ? "\n%d FAILURES\n" : "\nALL MODES PASS\n", fails);
    return fails ? 1 : 0;
}
