"""The milan look (H-036, docs/backgrounds/romantic_lights.md): matte dots, clearly visible and
giving no light of their own, drift on a smooth random wander over an almost black night with a
faint plum haze and a light dark border. When two of the middle layer meet, they linger a moment
and light up, a soft warm light blooms where they met and fades, and a faint memory of it stays.
On each marked word, two dots near that word drift together and meet just as it is sung, just
below the lyrics under that word. Behind the text on screen the dots and their light dim, so the
lyrics stay clear (the legibility rule); the calm lingers a little after the text leaves.

Ported from the approved sample songs/_review/backgrounds/lights2/milan_video.py. The dots are
a simulation, so frames must be drawn in order (frame(k) steps it to frame k)."""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from . import paint as P

W, H, Q = P.W, P.H, 4
MEET = 40.0                          # two middle dots this close have met
COOLDOWN = 6.0                       # a pair meets again only after this long
BELOW = 130.0                        # a marked word's meeting: this far below the lyrics
CALM, CALM_GROW, CALM_SOFT = 0.75, 70, 20   # behind the text: dim by this, box grown, edge (px)
CALM_RELEASE = 0.8                   # s: the calm fades this slowly after the text leaves
DOT = [P.lin(c) for c in ("#fff1dc", "#fff1dc", "#ffe2b0", "#ffc9d6")]
MATTE = [P.lin(c) for c in ("#d9d0c3", "#d9d0c3", "#dcc9a6", "#d9bcc5")]
GLOW, WARM = P.lin("#ffc4a8"), P.lin("#ffab86")


class Layer:
    """Dots on a smooth random wander: each velocity relaxes over tau and is nudged by noise, so
    a dot drifts and turns slowly; a soft push keeps it inside the frame."""

    def __init__(self, rng, n, speed, tau, size, level, dt):
        self.rng, self.tau, self.speed, self.dt = rng, tau, speed, dt
        self.p = np.stack([rng.uniform(40, W - 40, n), rng.uniform(40, H - 40, n)], 1)
        self.v = rng.normal(0, speed, (n, 2))
        self.size = rng.uniform(*size, n)
        self.level = rng.uniform(*level, n)
        self.col = rng.integers(len(DOT), size=n)

    def step(self) -> None:
        dt = self.dt
        a = math.exp(-dt / self.tau)
        self.v = self.v * a + self.speed * math.sqrt(1 - a * a) * self.rng.normal(0, 1, self.v.shape)
        for axis, lim in ((0, W), (1, H)):
            lo, hi = self.p[:, axis] < 60, self.p[:, axis] > lim - 60
            self.v[lo, axis] += (60 - self.p[lo, axis]) * 0.8 * dt
            self.v[hi, axis] -= (self.p[hi, axis] - (lim - 60)) * 0.8 * dt
        self.p += self.v * dt


class Scene:
    look = "milan"
    in_order = True                  # a simulation: frames one after another

    def __init__(self, facts):
        self.facts = facts
        self.dt = 1 / facts.fps
        rng = np.random.default_rng(facts.seed)
        base = P.gradient([(0.0, "#020107"), (0.5, "#04030c"), (1.0, "#010104")])
        P.blob(base, 540, 900, 700, 800, P.lin("#2a1a44"), 0.025)   # a very faint plum haze
        self.base = base
        self.far = Layer(rng, 14, 6.0, 5.0, (3.0, 4.5), (0.35, 0.5), self.dt)
        self.mid = Layer(rng, 28, 20.0, 3.5, (7.0, 10.0), (0.85, 1.0), self.dt)
        self.scrim = 1 - 0.3 * P.scrim(*self.facts.lyric_centre)   # calm behind the lyrics
        self.vig = P.vignette(0.3, border=0.42)
        self.plans, self.last_met, self.blooms = {}, {}, []   # blooms: (t, x, y, marked)
        self.met = set()                                       # marked words whose dots have met
        self.memory = np.zeros((H // Q, W // Q, 3), np.float32)
        self.calm = np.zeros((H // Q, W // Q), np.float32)   # 1 behind the text on screen
        self.linger = np.zeros(len(self.mid.p))
        self.k = -1

    def describe(self) -> str:
        marked = sum(1 for b in self.blooms if b[3])
        return (f"drifting matte dots; {len(self.blooms)} meetings so far "
                f"({marked} on marked words)")

    def _step(self, t: float) -> None:
        """Move the dots one frame and record the meetings (the simulation)."""
        mid = self.mid
        for layer in (self.far, mid):
            layer.step()
        steering = set()
        for s, _marked, cx, cy in self.facts.marks:     # a marked word draws two dots together
            if s not in self.plans and t >= s - 2.6:
                bottom = self.facts.lyric_box[3] if self.facts.lyric_box else cy + 60
                target = np.array([cx, min(bottom + BELOW, H - 200.0)])   # under the word
                busy = {i for p in self.plans.values() for i in p[:2]}
                order = [i for i in np.argsort(np.hypot(*(mid.p - target).T)) if i not in busy]
                if len(order) < 2:
                    continue
                a, b = int(order[0]), int(order[1])
                self.plans[s] = (a, b, mid.p[[a, b]].copy(), target, t)
            if s not in self.plans:
                continue
            a, b, start, target, ts = self.plans[s]
            u = min(max((t - ts) / max(s - ts, 1e-6), 0), 1)
            pair = tuple(sorted((a, b)))
            if u < 1:
                steering.update(pair)
                e = P.smooth(u)
                for j, i in enumerate((a, b)):
                    side = np.array([-14.0 if j == 0 else 14.0, 0.0])
                    new = start[j] * (1 - e) + (target + side * (1 - e)) * e + mid.v[i] * self.dt * (1 - e)
                    mid.v[i] = (new - mid.p[i]) / self.dt
                    mid.p[i] = new
            elif s not in self.met:          # they meet once, as the word is sung, cooldown or not
                self.met.add(s)
                self.last_met[pair] = t
                self.blooms.append((t, float(target[0]), float(target[1]), True))
                self.linger[[a, b]] = 1.0
                mid.v[[a, b]] = np.array([[-8.0, -3.0], [8.0, 3.0]])   # then they drift apart
        d = np.hypot(mid.p[:, None, 0] - mid.p[None, :, 0], mid.p[:, None, 1] - mid.p[None, :, 1])
        for i, j in zip(*np.nonzero(np.triu(d < MEET, 1))):       # two dots that meet: light
            i, j = int(i), int(j)
            if i in steering or j in steering or t - self.last_met.get((i, j), -99) <= COOLDOWN:
                continue
            self.last_met[(i, j)] = t
            cx, cy = (mid.p[i] + mid.p[j]) / 2
            self.blooms.append((t, float(cx), float(cy), False))
            self.linger[[i, j]] = 1.0
        mid.v *= (1 - 0.7 * self.linger)[:, None] ** self.dt      # they linger where they met
        self.linger *= math.exp(-self.dt / 1.2)
        self.memory *= 0.5 ** (self.dt / 20)                       # memories fade very slowly
        for tb, bx, by, marked in self.blooms:
            if 0 <= t - tb < self.dt:
                P.stamp(self.memory, Q, bx, by, 34, 34, WARM if marked else GLOW,
                        0.035 if marked else 0.018)

    def _calm(self, ink, steps: int) -> None:
        """Where the text is this frame (its box, grown and softened) the calm is full at once, so
        the text is never over a bright dot; elsewhere it fades over CALM_RELEASE."""
        target = np.zeros_like(self.calm)
        if ink is not None:
            x0, y0 = max(int((ink[0] - CALM_GROW) / Q), 0), max(int((ink[1] - CALM_GROW) / Q), 0)
            x1, y1 = int((ink[2] + CALM_GROW) / Q) + 1, int((ink[3] + CALM_GROW) / Q) + 1
            target[y0:y1, x0:x1] = 1.0
            target = ndimage.gaussian_filter(target, CALM_SOFT / Q)
        self.calm = np.maximum(target, self.calm * math.exp(-steps * self.dt / CALM_RELEASE))

    def frame(self, k: int, ink=None) -> np.ndarray:
        """Frame k of the background, (H, W, 3) uint8 sRGB, with the text's box `ink` over it.
        Frames must come in order."""
        if k <= self.k:
            raise ValueError(f"milan frames must come in order: {k} after {self.k}")
        steps = k - self.k
        while self.k < k:
            self.k += 1
            self._step(self.k * self.dt)
        self._calm(ink, steps)
        t = k * self.dt
        glow = np.zeros_like(self.memory)
        for tb, bx, by, marked in self.blooms:
            age = t - tb
            if 0 <= age < 5:
                env = min(age / 0.3, 1) * math.exp(-max(age - 0.3, 0) / 1.4)
                r = (46 if marked else 28) + (50 if marked else 30) * min(age / 1.2, 1)
                P.stamp(glow, Q, bx, by, r, r, WARM if marked else GLOW, (0.3 if marked else 0.16) * env)
        for i in range(len(self.mid.p)):                 # the meeting dots light up while they meet
            if self.linger[i] > 0.02:
                P.stamp(glow, Q, *self.mid.p[i], 22, 22, DOT[self.mid.col[i]], 0.35 * self.linger[i])
        glow = glow + np.stack([ndimage.gaussian_filter(glow[..., c], 3) for c in range(3)], -1) * 0.5
        quiet = 1 - CALM * self.calm
        x = self.base + P.up((glow + self.memory) * quiet[..., None])   # the only light: meetings
        for layer in (self.far, self.mid):               # the dots: matte, no glow of their own
            for i in range(len(layer.p)):
                px, py = layer.p[i]
                q = quiet[min(max(int(py / Q), 0), H // Q - 1), min(max(int(px / Q), 0), W // Q - 1)]
                P.disc(x, px, py, layer.size[i], MATTE[layer.col[i]], layer.level[i] * q)
        x *= self.scrim
        return P.finish(x, bloom=0.0, bloom_sigma=1, knee=0.45, soft=0.5, vig=self.vig)
