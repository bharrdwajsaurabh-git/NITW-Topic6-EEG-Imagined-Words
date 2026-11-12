"""
models/aga_selector.py
======================
Adaptive Genetic Algorithm (AGA) Feature Selector with Dynamic Diversity Control.
Innovation 2 of Topic 6 (NIT Warangal).
"""

import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from typing import Optional


class AdaptiveGeneticFeatureSelector:
    """
    Enhanced Genetic Algorithm with:
    - Dynamic adaptive mutation scaling based on population phenotypic diversity
    - Dual-objective Pareto fitness balancing accuracy and feature sparsity
    - Elitism preservation
    """
    def __init__(
        self,
        n_population: int = 24,
        n_generations: int = 6,
        base_crossover_rate: float = 0.85,
        base_mutation_rate: float = 0.03,
        cv_splits: int = 3,
        random_state: int = 42
    ):
        self.n_population = n_population
        self.n_generations = n_generations
        self.base_crossover_rate = base_crossover_rate
        self.base_mutation_rate = base_mutation_rate
        self.cv_splits = cv_splits
        self.random_state = random_state
        self.best_mask_: Optional[np.ndarray] = None
        self.best_fitness_: float = -1.0
        self.history_: list = []
        self.diversity_history_: list = []
        self.mutation_history_: list = []
        self.active_history_: list = []

    def fit(self, X: np.ndarray, y: np.ndarray):
        np.random.seed(self.random_state)
        n_features = X.shape[1]
        population = (np.random.rand(self.n_population, n_features) < 0.25).astype(np.int8)

        for ind in population:
            if not np.any(ind):
                ind[np.random.randint(0, n_features)] = 1

        clf = SVC(kernel="rbf", C=1.5, gamma="scale")
        skf = StratifiedKFold(n_splits=self.cv_splits, shuffle=True, random_state=self.random_state)

        for gen in range(self.n_generations):
            fitness_scores = []
            for ind in population:
                idx = np.where(ind == 1)[0]
                if len(idx) == 0:
                    fitness_scores.append(0.0)
                    continue
                scores = []
                for tr_idx, val_idx in skf.split(X[:, idx], y):
                    clf.fit(X[tr_idx][:, idx], y[tr_idx])
                    scores.append(accuracy_score(y[val_idx], clf.predict(X[val_idx][:, idx])))
                acc = np.mean(scores)
                sparsity_bonus = 0.02 * (1.0 - (len(idx) / n_features))
                fitness_scores.append(acc + sparsity_bonus)

            fitness_scores = np.array(fitness_scores)
            best_idx = np.argmax(fitness_scores)
            if fitness_scores[best_idx] > self.best_fitness_:
                self.best_fitness_ = fitness_scores[best_idx]
                self.best_mask_ = population[best_idx].copy()

            pop_diversity = float(np.mean(np.var(population, axis=0)))
            adaptive_mutation = self.base_mutation_rate * (1.0 + 2.0 * np.exp(-10.0 * pop_diversity))

            self.history_.append(float(self.best_fitness_))
            self.diversity_history_.append(pop_diversity)
            self.mutation_history_.append(float(adaptive_mutation))
            self.active_history_.append(int(np.sum(self.best_mask_)))

            print(
                f"    [AGA Gen {gen+1:02d}/{self.n_generations:02d}] "
                f"Best Fit: {self.best_fitness_:.4f} | "
                f"Active: {np.sum(self.best_mask_)}/{n_features} | "
                f"Diversity: {pop_diversity:.4f} | Adaptive Pm: {adaptive_mutation:.4f}"
            )

            # Elitism: retain top 2
            elite = [population[i].copy() for i in np.argsort(fitness_scores)[-2:]]
            new_pop = list(elite)

            while len(new_pop) < self.n_population:
                t1, t2 = np.random.choice(self.n_population, 3), np.random.choice(self.n_population, 3)
                p1 = population[t1[np.argmax(fitness_scores[t1])]]
                p2 = population[t2[np.argmax(fitness_scores[t2])]]

                # Crossover
                if np.random.rand() < self.base_crossover_rate:
                    pt = np.random.randint(1, n_features)
                    c1 = np.concatenate([p1[:pt], p2[pt:]])
                    c2 = np.concatenate([p2[:pt], p1[pt:]])
                else:
                    c1, c2 = p1.copy(), p2.copy()

                # Adaptive Mutation
                for child in [c1, c2]:
                    mut_mask = np.random.rand(n_features) < adaptive_mutation
                    child[mut_mask] = 1 - child[mut_mask]
                    if not np.any(child):
                        child[np.random.randint(0, n_features)] = 1
                    if len(new_pop) < self.n_population:
                        new_pop.append(child)

            population = np.array(new_pop)

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.best_mask_ is None:
            raise ValueError("AdaptiveGeneticFeatureSelector must be fitted before transform().")
        return X[:, self.best_mask_ == 1]


class AdaptiveBandWeightGA:
    """
    Adaptive Genetic Algorithm for 6-Band Filter-Bank Riemannian Manifold Weighting.
    Evolves continuous weights over ['raw', 'delta', 'theta', 'alpha', 'beta', 'gamma']
    while preserving symmetric positive definite (SPD) geometry within every 105-dim block.
    """
    def __init__(
        self,
        n_bands: int = 6,
        band_dim: int = 105,
        n_population: int = 20,
        n_generations: int = 8,
        cv_splits: int = 3,
        k_neighbors: int = 3,
        metric: str = "cosine",
        random_state: int = 42,
    ):
        self.n_bands = n_bands
        self.band_dim = band_dim
        self.n_population = n_population
        self.n_generations = n_generations
        self.cv_splits = cv_splits
        self.k_neighbors = k_neighbors
        self.metric = metric
        self.random_state = random_state
        self.best_weights_: Optional[np.ndarray] = None
        self.best_fitness_: float = -1.0
        self.history_: list = []
        self.diversity_history_: list = []
        self.mutation_history_: list = []
        self.weights_history_: list = []

    def apply_weights(self, X: np.ndarray, weights: Optional[np.ndarray] = None) -> np.ndarray:
        w = self.best_weights_ if weights is None else weights
        out = X.copy()
        for b in range(self.n_bands):
            out[:, b * self.band_dim : (b + 1) * self.band_dim] *= float(w[b])
        return out

    def fit(self, X_scaled: np.ndarray, y: np.ndarray):
        from sklearn.model_selection import cross_val_score
        from sklearn.neighbors import KNeighborsClassifier

        rng = np.random.RandomState(self.random_state)
        pop = rng.uniform(0.3, 2.0, size=(self.n_population, self.n_bands))
        skf = StratifiedKFold(n_splits=self.cv_splits, shuffle=True, random_state=self.random_state)

        for gen in range(self.n_generations):
            fits = []
            for w in pop:
                Xw = self.apply_weights(X_scaled, w)
                knn = KNeighborsClassifier(
                    n_neighbors=self.k_neighbors, weights="distance", metric=self.metric, n_jobs=-1
                )
                cv_acc = float(np.mean(cross_val_score(knn, Xw, y, cv=skf, n_jobs=-1)))
                fits.append(cv_acc)

            fits = np.array(fits)
            best_idx = int(np.argmax(fits))
            if fits[best_idx] > self.best_fitness_:
                self.best_fitness_ = float(fits[best_idx])
                self.best_weights_ = (pop[best_idx] / (np.max(pop[best_idx]) + 1e-8)).copy()

            pop_diversity = float(np.mean(np.std(pop, axis=0)))
            adaptive_pm = float(0.20 * (1.0 + np.exp(-3.0 * pop_diversity)))

            self.history_.append(float(self.best_fitness_))
            self.diversity_history_.append(pop_diversity)
            self.mutation_history_.append(adaptive_pm)
            self.weights_history_.append(self.best_weights_.tolist())

            print(
                f"    [AGA BandGen {gen+1:02d}/{self.n_generations:02d}] "
                f"CV Acc: {self.best_fitness_*100:.2f}% | "
                f"Div: {pop_diversity:.4f} | Pm: {adaptive_pm:.4f} | "
                f"Weights: {np.round(self.best_weights_, 3).tolist()}"
            )

            elite_idx = np.argsort(fits)[-2:]
            new_pop = [pop[elite_idx[1]].copy(), pop[elite_idx[0]].copy()]
            while len(new_pop) < self.n_population:
                i1, i2 = rng.choice(self.n_population, 2, replace=False)
                pa = pop[i1] if fits[i1] > fits[i2] else pop[i2]
                i3, i4 = rng.choice(self.n_population, 2, replace=False)
                pb = pop[i3] if fits[i3] > fits[i4] else pop[i4]
                child = np.clip(0.5 * (pa + pb) + rng.randn(self.n_bands) * adaptive_pm * 0.35, 0.05, 2.5)
                new_pop.append(child)
            pop = np.array(new_pop)

        return self

    def transform(self, X_scaled: np.ndarray) -> np.ndarray:
        if self.best_weights_ is None:
            raise ValueError("AdaptiveBandWeightGA must be fitted before transform().")
        return self.apply_weights(X_scaled, self.best_weights_)


class MultiScaleBlockAGA:
    """
    Fast Multi-Scale Structural Adaptive Genetic Algorithm (MDRC-AGA v3).
    Optimizes post-scaler macro-scale weights over multi-resolution Riemannian views:
      Block 0: Mendeley 6-Band Whole-Brain Log-SPD (630D)
      Block 1: Fine 7-Band Sub-Spectral Theta/Alpha/Beta/Gamma Log-SPD (735D)
      Block 2: Broca-Wernicke 10-Electrode Speech-Motor 6-Band Log-SPD (330D)
    Uses exact block dot-product decomposition over internal Train-only CV (zero test leakage).
    """
    def __init__(
        self,
        block_dims: tuple = (630, 735, 330),
        n_population: int = 18,
        n_generations: int = 10,
        cv_splits: int = 5,
        random_state: int = 42,
    ):
        self.block_dims = tuple(block_dims)
        self.n_blocks = len(self.block_dims)
        self.n_population = n_population
        self.n_generations = n_generations
        self.cv_splits = cv_splits
        self.random_state = random_state
        self.best_weights_: Optional[np.ndarray] = None
        self.best_fitness_: float = -1.0
        self.history_: list = []
        self.diversity_history_: list = []
        self.mutation_history_: list = []
        self.weights_history_: list = []

    def apply_weights(self, X_scaled: np.ndarray, weights: Optional[np.ndarray] = None) -> np.ndarray:
        w = self.best_weights_ if weights is None else weights
        if w is None:
            return X_scaled
        out = X_scaled.copy()
        s = 0
        for dim, wi in zip(self.block_dims, w):
            out[:, s : s + dim] *= float(wi)
            s += dim
        return out

    def fit(self, X_scaled: np.ndarray, y: np.ndarray):
        rng = np.random.RandomState(self.random_state)
        skf = StratifiedKFold(n_splits=self.cv_splits, shuffle=True, random_state=self.random_state)

        starts = np.cumsum([0] + list(self.block_dims[:-1]))
        fold_blocks = []
        for ftr, fva in skf.split(X_scaled, y):
            b_dots, b_nt, b_nv = [], [], []
            for s, d in zip(starts, self.block_dims):
                bt = X_scaled[ftr, s : s + d]
                bv = X_scaled[fva, s : s + d]
                b_dots.append(bv @ bt.T)
                b_nt.append(np.sum(bt * bt, axis=1))
                b_nv.append(np.sum(bv * bv, axis=1))
            fold_blocks.append((b_dots, b_nt, b_nv, y[ftr], y[fva]))

        pop = rng.uniform(0.35, 1.75, size=(self.n_population, self.n_blocks))
        pop[0] = np.array([1.40, 0.80, 0.40])[: self.n_blocks]
        pop[1] = np.array([1.00, 1.00, 0.50])[: self.n_blocks]
        pop[2] = np.ones(self.n_blocks)

        def eval_w(w: np.ndarray) -> float:
            w2 = w * w
            fold_scores = []
            for b_dots, b_nt, b_nv, yt, yv in fold_blocks:
                num = np.zeros_like(b_dots[0])
                nt = np.zeros_like(b_nt[0])
                nv = np.zeros_like(b_nv[0])
                for bi in range(self.n_blocks):
                    num += w2[bi] * b_dots[bi]
                    nt += w2[bi] * b_nt[bi]
                    nv += w2[bi] * b_nv[bi]
                sim = num / (np.sqrt(np.outer(nv, nt)) + 1e-12)
                p1 = yt[np.argmax(sim, axis=1)]
                # Distance-weighted 3-NN combination for stability + peak separability
                top3 = np.argpartition(-sim, 3, axis=1)[:, :3]
                tsim = np.take_along_axis(sim, top3, axis=1)
                tlbl = yt[top3]
                w3 = 1.0 / np.maximum(1.0 - tsim, 1e-4)
                classes = np.unique(yt)
                probs = np.zeros((len(yv), len(classes)))
                for ci, cv in enumerate(classes):
                    probs[:, ci] = np.sum(w3 * (tlbl == cv), axis=1)
                p3 = classes[np.argmax(probs, axis=1)]
                fold_scores.append(0.65 * np.mean(p1 == yv) + 0.35 * np.mean(p3 == yv))
            return float(np.mean(fold_scores))

        for gen in range(self.n_generations):
            fits = np.array([eval_w(ind) for ind in pop])
            bi = int(np.argmax(fits))
            if fits[bi] > self.best_fitness_:
                self.best_fitness_ = float(fits[bi])
                # Normalize relative scale to preserve numerical magnitude cleanly
                self.best_weights_ = (pop[bi] / (np.mean(pop[bi]) + 1e-12)).copy()

            pop_diversity = float(np.mean(np.std(pop, axis=0)))
            adaptive_pm = float(0.18 * (1.0 + np.exp(-3.0 * pop_diversity)))
            self.history_.append(float(self.best_fitness_))
            self.diversity_history_.append(pop_diversity)
            self.mutation_history_.append(adaptive_pm)
            self.weights_history_.append(np.round(self.best_weights_, 4).tolist())

            print(
                f"    [MDRC-AGA v3 Gen {gen+1:02d}/{self.n_generations:02d}] "
                f"CV Score: {self.best_fitness_*100:.2f}% | Div: {pop_diversity:.4f} | "
                f"Pm: {adaptive_pm:.4f} | ScaleWeights: {np.round(self.best_weights_, 3).tolist()}"
            )

            elite_idx = np.argsort(fits)[-2:]
            new_pop = [pop[elite_idx[1]].copy(), pop[elite_idx[0]].copy()]
            while len(new_pop) < self.n_population:
                i1, i2 = rng.choice(self.n_population, 2, replace=False)
                pa = pop[i1] if fits[i1] > fits[i2] else pop[i2]
                i3, i4 = rng.choice(self.n_population, 2, replace=False)
                pb = pop[i3] if fits[i3] > fits[i4] else pop[i4]
                child = np.clip(0.5 * (pa + pb) + rng.randn(self.n_blocks) * adaptive_pm * 0.25, 0.20, 2.50)
                new_pop.append(child)
            pop = np.array(new_pop)

        return self

    def transform(self, X_scaled: np.ndarray) -> np.ndarray:
        if self.best_weights_ is None:
            raise ValueError("MultiScaleBlockAGA must be fitted before transform().")
        return self.apply_weights(X_scaled, self.best_weights_)


class FastManifoldConsensusClassifier:
    """
    Fast BLAS-accelerated implementation of Multi-Metric Soft Consensus Ensemble:
      Weights [3, 2, 1, 1] over:
        - k=1 Cosine nearest manifold
        - k=1 Pearson Correlation nearest manifold
        - k=3 Distance-weighted Cosine manifold
        - k=3 Distance-weighted Pearson Correlation manifold
    Caches L2-normalized and centered-L2 float32 reference matrices at fit() time
    to deliver <50 ms total end-to-end single-trial BCI decoding latency.
    """
    def __init__(self, k_base: int = 3, weights: tuple = (3.0, 2.0, 1.0, 1.0)):
        self.k_base = int(k_base)
        self.weights = tuple(weights)
        self.classes_: Optional[np.ndarray] = None
        self.y_idx_: Optional[np.ndarray] = None
        self.X_cos_: Optional[np.ndarray] = None
        self.X_cor_: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.classes_, self.y_idx_ = np.unique(y, return_inverse=True)
        Xf = X.astype(np.float32, copy=False)
        self.X_cos_ = Xf / (np.linalg.norm(Xf, axis=1, keepdims=True) + 1e-12)
        Xc = Xf - np.mean(Xf, axis=1, keepdims=True)
        self.X_cor_ = Xc / (np.linalg.norm(Xc, axis=1, keepdims=True) + 1e-12)
        return self

    def _vote_probs_from_sim(self, sim: np.ndarray, k: int) -> np.ndarray:
        n_q = sim.shape[0]
        n_c = len(self.classes_)
        probs = np.zeros((n_q, n_c), dtype=np.float64)
        if k == 1:
            nn = np.argmax(sim, axis=1)
            probs[np.arange(n_q), self.y_idx_[nn]] = 1.0
            return probs
        top_idx = np.argpartition(-sim, k, axis=1)[:, :k]
        top_sim = np.take_along_axis(sim, top_idx, axis=1)
        dists = np.maximum(1.0 - top_sim, 1e-12)
        # If exact distance == 0 match exists, follow sklearn kNN zero-distance rule
        zero_mask = dists <= 1e-8
        w = np.where(zero_mask, 1.0, 1.0 / dists)
        lbls = self.y_idx_[top_idx]
        for qi in range(n_q):
            if np.any(zero_mask[qi]):
                row_w = np.where(zero_mask[qi], 1.0, 0.0)
            else:
                row_w = w[qi]
            for ki in range(k):
                probs[qi, lbls[qi, ki]] += row_w[ki]
            s = probs[qi].sum()
            if s > 0:
                probs[qi] /= s
        return probs

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        Xf = X.astype(np.float32, copy=False)
        q_cos = Xf / (np.linalg.norm(Xf, axis=1, keepdims=True) + 1e-12)
        sim_cos = q_cos @ self.X_cos_.T

        qc = Xf - np.mean(Xf, axis=1, keepdims=True)
        q_cor = qc / (np.linalg.norm(qc, axis=1, keepdims=True) + 1e-12)
        sim_cor = q_cor @ self.X_cor_.T

        p1_cos = self._vote_probs_from_sim(sim_cos, 1)
        p1_cor = self._vote_probs_from_sim(sim_cor, 1)
        pk_cos = self._vote_probs_from_sim(sim_cos, self.k_base)
        pk_cor = self._vote_probs_from_sim(sim_cor, self.k_base)

        w0, w1, w2, w3 = self.weights
        P = (w0 * p1_cos + w1 * p1_cor + w2 * pk_cos + w3 * pk_cor) / (w0 + w1 + w2 + w3)
        return P

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]
