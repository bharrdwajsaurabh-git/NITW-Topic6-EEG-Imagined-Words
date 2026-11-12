"""
models/aga_selector.py
======================
Adaptive Scalar Genetic Optimization, Multi-Scale Block Weighting, Soft Voting Ensemble,
Calibrated Out-of-Fold Stacking, and Uncertainty/Calibration Metrics.

Remediated audit items:
  - Flaw #6: All internal GA/block-weighting CV loops accept `groups` and enforce `GroupKFold`
    whenever `groups` is provided (zero overlapping-chunk leakage inside inner CV).
  - Flaw #9: Removes inaccurate "Pareto" label; explicitly documents scalar regularized objective
    `AdaptiveScalarGeneticSelector` (`acc + sparsity_weight * (1 - k/p)`).
  - Flaw #10: Supports `mutation_mode` in `('fixed', 'diversity_adaptive', 'diversity_stagnation')`
    for controlled multi-seed ablation.
  - Flaw #11: Clearly documents that `MultiScaleBlockAGA` learns 3 scalar block weights while
    keeping all 1,695 features active (`active_dims = sum(block_dims)`), NOT feature elimination.
  - Flaw #12 & #30: Distinguishes heuristic weighted soft voting (`MultiMetricSoftVotingClassifier`)
    with un-calibrated vote-share scores from genuine Out-of-Fold probability stacking & Platt
    calibration (`CalibratedManifoldStacker`), plus computes Balanced Accuracy, Macro-F1, Kappa,
    multiclass Brier score, Expected Calibration Error (ECE), and Block Bootstrap 95% CIs.
"""

import numpy as np
from sklearn.model_selection import StratifiedKFold, GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    cohen_kappa_score,
    log_loss,
)
from typing import Optional, Tuple, Dict, Any, List


def _make_inner_folds(
    y: np.ndarray, cv_splits: int, random_state: int, groups: Optional[np.ndarray] = None
) -> List[Tuple[np.ndarray, np.ndarray]]:
    if groups is not None:
        n_grp = len(np.unique(groups))
        k_splits = max(2, min(cv_splits, n_grp))
        gkf = GroupKFold(n_splits=k_splits)
        return list(gkf.split(np.zeros((len(y), 1)), y, groups=groups))
    skf = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=random_state)
    return list(skf.split(np.zeros((len(y), 1)), y))


class AdaptiveScalarGeneticSelector:
    """
    Scalar-Regularized Adaptive Genetic Feature Selector.
    Maximizes a single scalarized composite objective (inner CV accuracy + linear sparsity bonus)
    rather than multi-objective Pareto non-dominated sorting.
    Supports `mutation_mode`: 'fixed', 'diversity_adaptive', or 'diversity_stagnation'.
    """

    def __init__(
        self,
        n_population: int = 24,
        n_generations: int = 6,
        base_crossover_rate: float = 0.85,
        base_mutation_rate: float = 0.03,
        sparsity_weight: float = 0.02,
        mutation_mode: str = "diversity_adaptive",
        cv_splits: int = 3,
        random_state: int = 42,
    ):
        if mutation_mode not in ("fixed", "diversity_adaptive", "diversity_stagnation"):
            raise ValueError(f"Unsupported mutation_mode '{mutation_mode}'.")
        self.n_population = n_population
        self.n_generations = n_generations
        self.base_crossover_rate = base_crossover_rate
        self.base_mutation_rate = base_mutation_rate
        self.sparsity_weight = sparsity_weight
        self.mutation_mode = mutation_mode
        self.cv_splits = cv_splits
        self.random_state = random_state
        self.best_mask_: Optional[np.ndarray] = None
        self.best_fitness_: float = -1.0
        self.history_: list = []
        self.diversity_history_: list = []
        self.mutation_history_: list = []
        self.active_history_: list = []

    def fit(
        self, X: np.ndarray, y: np.ndarray, groups: Optional[np.ndarray] = None
    ) -> "AdaptiveScalarGeneticSelector":
        rng = np.random.RandomState(self.random_state)
        n_features = X.shape[1]
        population = (rng.rand(self.n_population, n_features) < 0.25).astype(np.int8)
        for ind in population:
            if not np.any(ind):
                ind[rng.randint(0, n_features)] = 1

        clf = SVC(kernel="rbf", C=1.5, gamma="scale")
        folds = _make_inner_folds(y, self.cv_splits, self.random_state, groups=groups)
        stagnation_count = 0

        for _ in range(self.n_generations):
            fitness_scores = []
            for ind in population:
                idx = np.where(ind == 1)[0]
                if len(idx) == 0:
                    fitness_scores.append(0.0)
                    continue
                scores = []
                for tr_idx, val_idx in folds:
                    sc = StandardScaler()
                    X_tr = sc.fit_transform(X[tr_idx][:, idx])
                    X_va = sc.transform(X[val_idx][:, idx])
                    clf.fit(X_tr, y[tr_idx])
                    scores.append(accuracy_score(y[val_idx], clf.predict(X_va)))
                acc = float(np.mean(scores))
                sparsity_bonus = self.sparsity_weight * (1.0 - (len(idx) / float(n_features)))
                fitness_scores.append(acc + sparsity_bonus)

            fitness_arr = np.array(fitness_scores)
            best_idx = int(np.argmax(fitness_arr))
            if fitness_arr[best_idx] > self.best_fitness_ + 1e-6:
                self.best_fitness_ = float(fitness_arr[best_idx])
                self.best_mask_ = population[best_idx].copy()
                stagnation_count = 0
            else:
                stagnation_count += 1

            pop_diversity = float(np.mean(np.var(population, axis=0)))
            if self.mutation_mode == "fixed":
                pm = float(self.base_mutation_rate)
            elif self.mutation_mode == "diversity_adaptive":
                pm = float(self.base_mutation_rate * (1.0 + 2.0 * np.exp(-10.0 * pop_diversity)))
            else:  # diversity_stagnation
                stag_boost = 1.0 + 0.35 * min(stagnation_count, 4)
                pm = float(self.base_mutation_rate * (1.0 + 2.0 * np.exp(-10.0 * pop_diversity)) * stag_boost)
            pm = min(pm, 0.25)

            self.history_.append(float(self.best_fitness_))
            self.diversity_history_.append(pop_diversity)
            self.mutation_history_.append(pm)
            self.active_history_.append(int(np.sum(self.best_mask_)))

            elite = [population[i].copy() for i in np.argsort(fitness_arr)[-2:]]
            new_pop = list(elite)
            while len(new_pop) < self.n_population:
                t1 = rng.choice(self.n_population, 3, replace=True)
                t2 = rng.choice(self.n_population, 3, replace=True)
                p1 = population[t1[int(np.argmax(fitness_arr[t1]))]]
                p2 = population[t2[int(np.argmax(fitness_arr[t2]))]]

                if rng.rand() < self.base_crossover_rate and n_features > 1:
                    pt = int(rng.randint(1, n_features))
                    c1 = np.concatenate([p1[:pt], p2[pt:]])
                    c2 = np.concatenate([p2[:pt], p1[pt:]])
                else:
                    c1, c2 = p1.copy(), p2.copy()

                for child in (c1, c2):
                    mut_mask = rng.rand(n_features) < pm
                    child[mut_mask] = 1 - child[mut_mask]
                    if not np.any(child):
                        child[rng.randint(0, n_features)] = 1
                    if len(new_pop) < self.n_population:
                        new_pop.append(child)
            population = np.array(new_pop)

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.best_mask_ is None:
            raise ValueError("AdaptiveScalarGeneticSelector must be fitted before transform().")
        return X[:, self.best_mask_ == 1]


# Backward-compatible alias with accurate documentation
AdaptiveGeneticFeatureSelector = AdaptiveScalarGeneticSelector


class AdaptiveBandWeightGA:
    """Continuous per-band weight optimization with optional GroupKFold (`groups`)."""

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

    def fit(
        self, X_scaled: np.ndarray, y: np.ndarray, groups: Optional[np.ndarray] = None
    ) -> "AdaptiveBandWeightGA":
        from sklearn.model_selection import cross_val_score
        from sklearn.neighbors import KNeighborsClassifier

        rng = np.random.RandomState(self.random_state)
        pop = rng.uniform(0.3, 2.0, size=(self.n_population, self.n_bands))
        folds = _make_inner_folds(y, self.cv_splits, self.random_state, groups=groups)

        for _ in range(self.n_generations):
            fits = []
            for w in pop:
                Xw = self.apply_weights(X_scaled, w)
                knn = KNeighborsClassifier(
                    n_neighbors=self.k_neighbors, weights="distance", metric=self.metric, n_jobs=-1
                )
                cv_acc = float(np.mean(cross_val_score(knn, Xw, y, cv=folds, n_jobs=-1)))
                fits.append(cv_acc)
            fits_arr = np.array(fits)
            best_idx = int(np.argmax(fits_arr))
            if fits_arr[best_idx] > self.best_fitness_:
                self.best_fitness_ = float(fits_arr[best_idx])
                self.best_weights_ = (pop[best_idx] / (np.max(pop[best_idx]) + 1e-8)).copy()

            pop_diversity = float(np.mean(np.std(pop, axis=0)))
            adaptive_pm = float(0.20 * (1.0 + np.exp(-3.0 * pop_diversity)))
            self.history_.append(float(self.best_fitness_))
            self.diversity_history_.append(pop_diversity)
            self.mutation_history_.append(adaptive_pm)
            self.weights_history_.append(self.best_weights_.tolist())

            elite_idx = np.argsort(fits_arr)[-2:]
            new_pop = [pop[elite_idx[1]].copy(), pop[elite_idx[0]].copy()]
            while len(new_pop) < self.n_population:
                i1, i2 = rng.choice(self.n_population, 2, replace=False)
                pa = pop[i1] if fits_arr[i1] > fits_arr[i2] else pop[i2]
                i3, i4 = rng.choice(self.n_population, 2, replace=False)
                pb = pop[i3] if fits_arr[i3] > fits_arr[i4] else pop[i4]
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
    Multi-Scale Block-Weighting Adaptive Genetic Algorithm.
    NOTE (Flaw #11): Optimizes ONLY 3 positive scalar block weights across multi-resolution
    feature groups `block_dims`; all `sum(block_dims)` features remain active (block-scaling,
    NOT individual feature elimination).
    Supports `groups` (GroupKFold) for leakage-free inner evaluation (Flaw #6) and
    `mutation_mode` in `('fixed', 'diversity_adaptive', 'diversity_stagnation')` (Flaw #10).
    """

    def __init__(
        self,
        block_dims: tuple = (630, 735, 330),
        n_population: int = 18,
        n_generations: int = 10,
        cv_splits: int = 5,
        mutation_mode: str = "diversity_adaptive",
        base_mutation_step: float = 0.22,
        random_state: int = 42,
    ):
        if mutation_mode not in ("fixed", "diversity_adaptive", "diversity_stagnation"):
            raise ValueError(f"Unsupported mutation_mode '{mutation_mode}'.")
        self.block_dims = tuple(block_dims)
        self.n_blocks = len(self.block_dims)
        self.n_population = n_population
        self.n_generations = n_generations
        self.cv_splits = cv_splits
        self.mutation_mode = mutation_mode
        self.base_mutation_step = float(base_mutation_step)
        self.random_state = random_state
        self.best_weights_: Optional[np.ndarray] = None
        self.best_fitness_: float = -1.0
        self.history_: list = []
        self.diversity_history_: list = []
        self.mutation_history_: list = []
        self.weights_history_: list = []
        self.active_feature_count_: int = int(sum(self.block_dims))
        self.total_feature_count_: int = int(sum(self.block_dims))

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

    def fit(
        self,
        X_scaled: np.ndarray,
        y: np.ndarray,
        groups: Optional[np.ndarray] = None,
    ) -> "MultiScaleBlockAGA":
        rng = np.random.RandomState(self.random_state)
        folds = _make_inner_folds(y, self.cv_splits, self.random_state, groups=groups)

        starts = np.cumsum([0] + list(self.block_dims[:-1]))
        fold_blocks = []
        classes_all = np.unique(y)
        n_cls_all = len(classes_all)
        c2i_all = {int(c): i for i, c in enumerate(classes_all)}
        for ftr, fva in folds:
            b_dots, b_nt, b_nv = [], [], []
            for s, d in zip(starts, self.block_dims):
                bt = X_scaled[ftr, s : s + d].astype(np.float32, copy=False)
                bv = X_scaled[fva, s : s + d].astype(np.float32, copy=False)
                b_dots.append(bv @ bt.T)
                b_nt.append(np.sum(bt * bt, axis=1))
                b_nv.append(np.sum(bv * bv, axis=1))
            B_dots = np.stack(b_dots, axis=0)
            B_nt = np.stack(b_nt, axis=0)
            B_nv = np.stack(b_nv, axis=0)
            yt_idx = np.array([c2i_all[int(v)] for v in y[ftr]], dtype=np.int64)
            yv_idx = np.array([c2i_all[int(v)] for v in y[fva]], dtype=np.int64)
            fold_blocks.append((B_dots, B_nt, B_nv, yt_idx, yv_idx))

        pop = rng.uniform(0.35, 1.75, size=(self.n_population, self.n_blocks))
        pop[0] = np.array([1.40, 0.80, 0.40])[: self.n_blocks]
        pop[1] = np.array([1.00, 1.00, 0.50])[: self.n_blocks]
        pop[2] = np.ones(self.n_blocks)

        def eval_w(w: np.ndarray) -> float:
            w2 = (w * w).astype(np.float32)
            fold_scores = []
            for B_dots, B_nt, B_nv, yt_idx, yv_idx in fold_blocks:
                num = np.tensordot(w2, B_dots, axes=(0, 0))
                nt = w2 @ B_nt
                nv = w2 @ B_nv
                denom = np.sqrt(nv[:, None] * nt[None, :]) + np.float32(1e-12)
                sim = num / denom
                p1 = yt_idx[np.argmax(sim, axis=1)]
                k3 = min(3, sim.shape[1])
                top3 = np.argpartition(-sim, min(k3, sim.shape[1] - 1), axis=1)[:, :k3]
                tsim = np.take_along_axis(sim, top3, axis=1)
                tlbl = yt_idx[top3]
                w3 = 1.0 / np.maximum(1.0 - tsim, np.float32(1e-4))
                probs = np.zeros((len(yv_idx), n_cls_all), dtype=np.float32)
                row_ar = np.arange(len(yv_idx))
                for rank_i in range(k3):
                    np.add.at(probs, (row_ar, tlbl[:, rank_i]), w3[:, rank_i])
                p3 = np.argmax(probs, axis=1)
                fold_scores.append(0.65 * float(np.mean(p1 == yv_idx)) + 0.35 * float(np.mean(p3 == yv_idx)))
            return float(np.mean(fold_scores))

        stagnation_count = 0
        for gen in range(self.n_generations):
            fits = np.array([eval_w(ind) for ind in pop])
            bi = int(np.argmax(fits))
            if fits[bi] > self.best_fitness_ + 1e-6:
                self.best_fitness_ = float(fits[bi])
                self.best_weights_ = (pop[bi] / (np.mean(pop[bi]) + 1e-12)).copy()
                stagnation_count = 0
            else:
                stagnation_count += 1

            pop_diversity = float(np.mean(np.std(pop, axis=0)))
            if self.mutation_mode == "fixed":
                pm = float(self.base_mutation_step)
            elif self.mutation_mode == "diversity_adaptive":
                pm = float(self.base_mutation_step * (1.0 + np.exp(-3.0 * pop_diversity)))
            else:
                stag_boost = 1.0 + 0.25 * min(stagnation_count, 4)
                pm = float(self.base_mutation_step * (1.0 + np.exp(-3.0 * pop_diversity)) * stag_boost)

            self.history_.append(float(self.best_fitness_))
            self.diversity_history_.append(pop_diversity)
            self.mutation_history_.append(pm)
            self.weights_history_.append(np.round(self.best_weights_, 4).tolist())

            elite_idx = np.argsort(fits)[-2:]
            new_pop = [pop[elite_idx[1]].copy(), pop[elite_idx[0]].copy()]
            while len(new_pop) < self.n_population:
                i1, i2 = rng.choice(self.n_population, 2, replace=False)
                pa = pop[i1] if fits[i1] > fits[i2] else pop[i2]
                i3, i4 = rng.choice(self.n_population, 2, replace=False)
                pb = pop[i3] if fits[i3] > fits[i4] else pop[i4]
                child = np.clip(0.5 * (pa + pb) + rng.randn(self.n_blocks) * pm * 0.25, 0.20, 2.50)
                new_pop.append(child)
            pop = np.array(new_pop)

        return self

    def transform(self, X_scaled: np.ndarray) -> np.ndarray:
        if self.best_weights_ is None:
            raise ValueError("MultiScaleBlockAGA must be fitted before transform().")
        return self.apply_weights(X_scaled, self.best_weights_)


class MultiMetricSoftVotingClassifier:
    """
    Heuristic Weighted Soft-Voting Consensus Ensemble (NOT OOF stacking and NOT calibrated
    posterior probabilities — outputs un-calibrated neighbor vote fractions; Flaws #12, #30).
    Combines: k=1 Cosine, k=1 Pearson Correlation, k=k_base Distance-Weighted Cosine,
    and k=k_base Distance-Weighted Pearson Correlation.
    """

    def __init__(self, k_base: int = 3, weights: tuple = (3.0, 2.0, 1.0, 1.0)):
        self.k_base = int(k_base)
        self.weights = tuple(weights)
        self.classes_: Optional[np.ndarray] = None
        self.y_idx_: Optional[np.ndarray] = None
        self.X_cos_: Optional[np.ndarray] = None
        self.X_cor_: Optional[np.ndarray] = None
        self.is_calibrated_probabilities: bool = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MultiMetricSoftVotingClassifier":
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
        if k <= 1 or sim.shape[1] <= 1:
            nn = np.argmax(sim, axis=1)
            probs[np.arange(n_q), self.y_idx_[nn]] = 1.0
            return probs
        k_eff = min(k, sim.shape[1])
        top_idx = np.argpartition(-sim, min(k_eff, sim.shape[1] - 1), axis=1)[:, :k_eff]
        top_sim = np.take_along_axis(sim, top_idx, axis=1)
        dists = np.maximum(1.0 - top_sim, 1e-12)
        zero_mask = dists <= 1e-8
        w = np.where(zero_mask, 1.0, 1.0 / dists)
        lbls = self.y_idx_[top_idx]
        for qi in range(n_q):
            row_w = np.where(zero_mask[qi], 1.0, 0.0) if np.any(zero_mask[qi]) else w[qi]
            for ki in range(k_eff):
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
        return (w0 * p1_cos + w1 * p1_cor + w2 * pk_cos + w3 * pk_cor) / (w0 + w1 + w2 + w3)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


FastManifoldConsensusClassifier = MultiMetricSoftVotingClassifier


class CalibratedManifoldStacker:
    """
    True Out-of-Fold Stacking Meta-Learner with Multinomial Logistic Calibration (Flaws #12, #30).
    Combines four complementary calibrated/probabilistic base models inside OOF folds
    (respecting `groups` / GroupKFold when provided):
      1) L2-Regularized Multinomial Logistic Regression (cosine/tangent space)
      2) Shrinkage Linear Discriminant Analysis (Ledoit-Wolf / auto shrinkage)
      3) Platt-Calibrated L2 Ridge Classifier (`CalibratedClassifierCV(RidgeClassifier, cv=3)`)
      4) Multi-Metric Distance Soft Voter (`MultiMetricSoftVotingClassifier`)
    Meta-learner fits penalized multinomial LogisticRegression on OOF predicted log-probabilities.
    """

    def __init__(self, cv_splits: int = 4, random_state: int = 42):
        self.cv_splits = int(cv_splits)
        self.random_state = int(random_state)
        self.classes_: Optional[np.ndarray] = None
        self.base_models_: list = []
        self.meta_clf_: Optional[LogisticRegression] = None
        self.is_calibrated_probabilities: bool = True

    def _build_bases(self, n_samples: int, n_features: int):
        n_comp = max(2, min(192, max(2, n_samples - 2), n_features))
        return [
            LogisticRegression(C=0.1, max_iter=2000, tol=1e-3, random_state=self.random_state),
            Pipeline([
                ("pca", PCA(n_components=n_comp, svd_solver="randomized", random_state=self.random_state)),
                ("lda", LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")),
            ]),
            CalibratedClassifierCV(
                RidgeClassifier(alpha=100.0, random_state=self.random_state),
                cv=3,
                method="sigmoid",
                ensemble=False,
            ),
            MultiMetricSoftVotingClassifier(k_base=3, weights=(1.0, 1.0, 1.0, 1.0)),
        ]

    @staticmethod
    def _to_meta_features(probs_list: List[np.ndarray]) -> np.ndarray:
        eps = 1e-6
        logged = [np.log(np.clip(p, eps, 1.0 - eps)) for p in probs_list]
        return np.hstack(logged)

    def fit(
        self, X: np.ndarray, y: np.ndarray, groups: Optional[np.ndarray] = None
    ) -> "CalibratedManifoldStacker":
        self.classes_ = np.unique(y)
        n_c = len(self.classes_)
        folds = _make_inner_folds(y, self.cv_splits, self.random_state, groups=groups)

        oof_probs = [np.zeros((len(y), n_c), dtype=np.float64) for _ in range(4)]
        for ftr, fva in folds:
            bases = self._build_bases(len(ftr), X.shape[1])
            for m_idx, clf in enumerate(bases):
                clf.fit(X[ftr], y[ftr])
                oof_probs[m_idx][fva] = clf.predict_proba(X[fva])

        meta_X = self._to_meta_features(oof_probs)
        self.meta_clf_ = LogisticRegression(C=0.25, max_iter=2000, tol=1e-3, random_state=self.random_state)
        self.meta_clf_.fit(meta_X, y)

        self.base_models_ = self._build_bases(len(y), X.shape[1])
        for clf in self.base_models_:
            clf.fit(X, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.meta_clf_ is None:
            raise RuntimeError("CalibratedManifoldStacker must be fitted before predict_proba().")
        base_probs = [clf.predict_proba(X) for clf in self.base_models_]
        meta_X = self._to_meta_features(base_probs)
        return self.meta_clf_.predict_proba(meta_X)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


def compute_multiclass_ece(y_true_idx: np.ndarray, probs: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE) on predicted top-class confidence."""
    conf = np.max(probs, axis=1)
    pred = np.argmax(probs, axis=1)
    acc = (pred == y_true_idx).astype(np.float64)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true_idx)
    for b in range(n_bins):
        lo, hi = bins[b], bins[b + 1]
        if b == 0:
            mask = (conf >= lo) & (conf <= hi)
        else:
            mask = (conf > lo) & (conf <= hi)
        nb = int(np.sum(mask))
        if nb > 0:
            ece += (nb / float(n)) * abs(float(np.mean(acc[mask])) - float(np.mean(conf[mask])))
    return float(ece)


def compute_multiclass_brier(y_true_idx: np.ndarray, probs: np.ndarray) -> float:
    """Computes multiclass Brier score: mean_i sum_c (p_ic - y_ic)^2."""
    n_c = probs.shape[1]
    one_hot = np.eye(n_c, dtype=np.float64)[y_true_idx]
    return float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))


def compute_classification_and_calibration_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray] = None,
    block_ids: Optional[np.ndarray] = None,
    n_bootstrap: int = 400,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Computes complete classification + calibration + block-bootstrap 95% CI summary (Flaws #27, #30).
    """
    classes = np.unique(np.concatenate([np.unique(y_true), np.unique(y_pred)]))
    out: Dict[str, Any] = {
        "n_samples": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "cohen_kappa": float(cohen_kappa_score(y_true, y_pred)),
    }

    per_class_rec = {}
    for c in classes:
        mask = y_true == c
        if np.any(mask):
            per_class_rec[int(c)] = float(np.mean(y_pred[mask] == y_true[mask]))
    out["per_class_recall"] = per_class_rec

    # Cluster / block bootstrap 95% CI (resamples 8s blocks if provided, else trials)
    rng = np.random.RandomState(random_state)
    boot_accs = []
    if block_ids is not None and len(block_ids) == len(y_true):
        uniq_b = np.unique(block_ids)
        b_to_idx = [np.where(block_ids == b)[0] for b in uniq_b]
        n_b = len(uniq_b)
        for _ in range(n_bootstrap):
            sampled_b = rng.randint(0, n_b, size=n_b)
            idx = np.concatenate([b_to_idx[j] for j in sampled_b])
            boot_accs.append(float(np.mean(y_pred[idx] == y_true[idx])))
        out["ci_unit"] = f"block_cluster_bootstrap(n_blocks={n_b})"
    else:
        n = len(y_true)
        for _ in range(n_bootstrap):
            idx = rng.randint(0, n, size=n)
            boot_accs.append(float(np.mean(y_pred[idx] == y_true[idx])))
        out["ci_unit"] = f"sample_bootstrap(n={n})"

    out["acc_ci95_low"] = float(np.percentile(boot_accs, 2.5))
    out["acc_ci95_high"] = float(np.percentile(boot_accs, 97.5))

    if y_proba is not None:
        class_to_pos = {int(c): i for i, c in enumerate(sorted(np.unique(y_true)))}
        if y_proba.shape[1] == len(class_to_pos):
            y_idx = np.array([class_to_pos[int(v)] for v in y_true], dtype=np.int64)
            probs = np.clip(y_proba.astype(np.float64), 1e-6, 1.0 - 1e-6)
            probs = probs / np.sum(probs, axis=1, keepdims=True)
            out["brier_score"] = compute_multiclass_brier(y_idx, probs)
            out["ece_10bin"] = compute_multiclass_ece(y_idx, probs, n_bins=10)
            out["mean_confidence"] = float(np.mean(np.max(probs, axis=1)))
            try:
                out["log_loss"] = float(log_loss(y_idx, probs, labels=list(range(len(class_to_pos)))))
            except Exception:
                out["log_loss"] = None
    return out
