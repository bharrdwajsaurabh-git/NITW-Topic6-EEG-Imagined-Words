"""
models/ga_feature_selector.py
=============================
Evolutionary Optimization for EEG Imagined Speech Feature Selection.
Supports both standard `StratifiedKFold` (exploratory chunk splits) and strict
`GroupKFold(groups=block_ids)` so no overlapping chunks ever cross internal GA folds (Flaw #6).
"""

import numpy as np
from sklearn.model_selection import StratifiedKFold, GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score
from typing import Tuple, List, Optional


def _make_inner_cv(y: np.ndarray, cv_splits: int, random_state: int, groups: Optional[np.ndarray] = None):
    if groups is not None:
        n_groups = len(np.unique(groups))
        k_splits = max(2, min(cv_splits, n_groups))
        cv = GroupKFold(n_splits=k_splits)
        return list(cv.split(np.zeros((len(y), 1)), y, groups=groups))
    skf = StratifiedKFold(n_splits=cv_splits, shuffle=True, random_state=random_state)
    return list(skf.split(np.zeros((len(y), 1)), y))


class GeneticFeatureSelector:
    """
    Genetic Algorithm to discover a compact feature subset via inner CV accuracy
    minus a scalar parsimony penalty. Supports group-disjoint inner folds via `groups`.
    """

    def __init__(
        self,
        n_population: int = 30,
        n_generations: int = 20,
        crossover_rate: float = 0.8,
        mutation_rate: float = 0.03,
        parsimony_penalty: float = 0.01,
        cv_splits: int = 3,
        random_state: int = 42,
    ):
        self.n_population = n_population
        self.n_generations = n_generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.parsimony_penalty = parsimony_penalty
        self.cv_splits = cv_splits
        self.random_state = random_state
        self.best_mask_: Optional[np.ndarray] = None
        self.best_fitness_: float = -1.0
        self.history_: List[float] = []

    def _evaluate_fitness(
        self, chromosome: np.ndarray, X: np.ndarray, y: np.ndarray, folds: list
    ) -> float:
        selected_indices = np.where(chromosome == 1)[0]
        n_selected = len(selected_indices)
        if n_selected == 0:
            return 0.0

        X_subset = X[:, selected_indices]
        scores = []
        clf = SVC(kernel="rbf", C=1.0)
        for train_idx, val_idx in folds:
            scaler = StandardScaler()
            X_tr = scaler.fit_transform(X_subset[train_idx])
            X_va = scaler.transform(X_subset[val_idx])
            clf.fit(X_tr, y[train_idx])
            preds = clf.predict(X_va)
            scores.append(accuracy_score(y[val_idx], preds))

        mean_acc = float(np.mean(scores))
        penalty = self.parsimony_penalty * (n_selected / len(chromosome))
        return mean_acc - penalty

    def fit(
        self, X: np.ndarray, y: np.ndarray, groups: Optional[np.ndarray] = None
    ) -> "GeneticFeatureSelector":
        rng = np.random.RandomState(self.random_state)
        n_features = X.shape[1]
        folds = _make_inner_cv(y, self.cv_splits, self.random_state, groups=groups)

        population = (rng.rand(self.n_population, n_features) < 0.3).astype(np.int8)
        for ind in population:
            if not np.any(ind):
                ind[rng.randint(0, n_features)] = 1

        for _ in range(self.n_generations):
            fitness_scores = np.array(
                [self._evaluate_fitness(ind, X, y, folds) for ind in population]
            )
            gen_best_idx = int(np.argmax(fitness_scores))
            gen_best_fit = float(fitness_scores[gen_best_idx])
            self.history_.append(gen_best_fit)
            if gen_best_fit > self.best_fitness_:
                self.best_fitness_ = gen_best_fit
                self.best_mask_ = population[gen_best_idx].copy()

            elite_indices = np.argsort(fitness_scores)[-2:]
            next_generation = [population[i].copy() for i in elite_indices]
            while len(next_generation) < self.n_population:
                t1 = rng.choice(self.n_population, 3, replace=False)
                t2 = rng.choice(self.n_population, 3, replace=False)
                parent1 = population[t1[int(np.argmax(fitness_scores[t1]))]]
                parent2 = population[t2[int(np.argmax(fitness_scores[t2]))]]

                if rng.rand() < self.crossover_rate and n_features > 1:
                    cross_point = int(rng.randint(1, n_features))
                    child1 = np.concatenate([parent1[:cross_point], parent2[cross_point:]])
                    child2 = np.concatenate([parent2[:cross_point], parent1[cross_point:]])
                else:
                    child1, child2 = parent1.copy(), parent2.copy()

                for child in (child1, child2):
                    mut = rng.rand(n_features) < self.mutation_rate
                    child[mut] = 1 - child[mut]
                    if not np.any(child):
                        child[rng.randint(0, n_features)] = 1
                    if len(next_generation) < self.n_population:
                        next_generation.append(child)
            population = np.array(next_generation)

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.best_mask_ is None:
            raise RuntimeError("Selector must be fitted before transforming.")
        return X[:, self.best_mask_ == 1]


class PaperRankGeneticSelector:
    """
    Primary Paper Genetic Algorithm Selector (Lara-Arellano et al., Eng MDPI 2025).
    Rank Selection + Homogeneous Uniform Crossover + Bit-Flip Mutation
    with heuristic kNN search over k in {1, 3, 5, 7}.
    Respects `groups` (GroupKFold) inside all GA evaluations when provided.
    """

    def __init__(
        self,
        n_population: int = 40,
        n_generations: int = 20,
        mutation_rate: float = 0.04,
        k_candidates: Tuple[int, ...] = (1, 3, 5, 7),
        metric: str = "cosine",
        cv_splits: int = 3,
        random_state: int = 42,
    ):
        self.n_population = n_population
        self.n_generations = n_generations
        self.mutation_rate = mutation_rate
        self.k_candidates = tuple(k_candidates)
        self.metric = metric
        self.cv_splits = cv_splits
        self.random_state = random_state
        self.best_mask_: Optional[np.ndarray] = None
        self.best_k_: int = 1
        self.best_fitness_: float = -1.0
        self.history_: List[float] = []

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        block_slices: Optional[list] = None,
        groups: Optional[np.ndarray] = None,
    ) -> "PaperRankGeneticSelector":
        rng = np.random.RandomState(self.random_state)
        n_genes = len(block_slices) if block_slices is not None else X.shape[1]
        folds = _make_inner_cv(y, self.cv_splits, self.random_state, groups=groups)

        # Pre-scale each inner fold using only that fold's training rows (zero val leakage)
        scaled_folds = []
        for ftr, fva in folds:
            sc = StandardScaler()
            Xtr_s = sc.fit_transform(X[ftr])
            Xva_s = sc.transform(X[fva])
            scaled_folds.append((Xtr_s, y[ftr], Xva_s, y[fva]))

        pop = (rng.rand(self.n_population, n_genes) < 0.65).astype(np.int8)
        pop[0] = np.ones(n_genes, dtype=np.int8)
        for g in pop:
            if not np.any(g):
                g[rng.randint(0, n_genes)] = 1

        # Select heuristic k strictly inside internal folds
        best_k = self.k_candidates[0]
        best_k_acc = -1.0
        for kv in self.k_candidates:
            cs = []
            for Xtr_s, yt, Xva_s, yv in scaled_folds:
                kv_eff = min(kv, len(Xtr_s))
                wmode = "distance" if (kv_eff > 1 and self.metric == "cosine") else "uniform"
                clf = KNeighborsClassifier(n_neighbors=kv_eff, metric=self.metric, weights=wmode)
                clf.fit(Xtr_s, yt)
                cs.append(accuracy_score(yv, clf.predict(Xva_s)))
            sc_k = float(np.mean(cs))
            if sc_k > best_k_acc:
                best_k_acc = sc_k
                best_k = int(kv)
        self.best_k_ = best_k
        wmode = "distance" if (best_k > 1 and self.metric == "cosine") else "uniform"

        def expand_mask(chrom: np.ndarray) -> np.ndarray:
            if block_slices is None:
                return chrom.astype(bool)
            col_mask = np.zeros(X.shape[1], dtype=bool)
            for active, bm in zip(chrom, block_slices):
                if active:
                    col_mask |= bm
            if not np.any(col_mask):
                col_mask[:] = True
            return col_mask

        for _ in range(self.n_generations):
            fits = np.zeros(self.n_population, dtype=np.float64)
            for idx_i, chrom in enumerate(pop):
                cmask = expand_mask(chrom)
                cs = []
                for Xtr_s, yt, Xva_s, yv in scaled_folds:
                    Xt = Xtr_s[:, cmask]
                    Xv = Xva_s[:, cmask]
                    if self.metric == "cosine":
                        Xtn = Xt / (np.linalg.norm(Xt, axis=1, keepdims=True) + 1e-12)
                        Xvn = Xv / (np.linalg.norm(Xv, axis=1, keepdims=True) + 1e-12)
                        Dsub = 1.0 - (Xvn @ Xtn.T)
                    else:
                        nt2 = np.sum(Xt * Xt, axis=1)
                        nv2 = np.sum(Xv * Xv, axis=1)
                        Dsub = np.maximum(nv2[:, None] + nt2[None, :] - 2.0 * (Xv @ Xt.T), 0.0)

                    if best_k == 1:
                        pred = yt[np.argmin(Dsub, axis=1)]
                    else:
                        ke = min(best_k, Dsub.shape[1])
                        nn = np.argpartition(Dsub, min(ke, Dsub.shape[1] - 1), axis=1)[:, :ke]
                        lbls = yt[nn]
                        classes = np.unique(yt)
                        if wmode == "distance":
                            d_nn = np.take_along_axis(Dsub, nn, axis=1)
                            w_nn = 1.0 / np.maximum(d_nn, 1e-4)
                        else:
                            w_nn = np.ones_like(lbls, dtype=np.float64)
                        probs = np.zeros((len(Xv), len(classes)), dtype=np.float64)
                        for ci, cv in enumerate(classes):
                            probs[:, ci] = np.sum(w_nn * (lbls == cv), axis=1)
                        pred = classes[np.argmax(probs, axis=1)]
                    cs.append(float(np.mean(pred == yv)))
                fits[idx_i] = float(np.mean(cs))

            bi = int(np.argmax(fits))
            if fits[bi] > self.best_fitness_:
                self.best_fitness_ = float(fits[bi])
                self.best_mask_ = expand_mask(pop[bi])
            self.history_.append(float(self.best_fitness_))

            elite_idx = np.argsort(fits)[-2:]
            next_pop = [pop[elite_idx[1]].copy(), pop[elite_idx[0]].copy()]
            ranks = np.argsort(np.argsort(fits)) + 1
            probs = ranks / float(np.sum(ranks))
            while len(next_pop) < self.n_population:
                pa = int(rng.choice(self.n_population, p=probs))
                pb = int(rng.choice(self.n_population, p=probs))
                cross_mask = rng.rand(n_genes) < 0.5
                child = np.where(cross_mask, pop[pa], pop[pb]).astype(np.int8)
                flip = rng.rand(n_genes) < self.mutation_rate
                child[flip] = 1 - child[flip]
                if not np.any(child):
                    child[rng.randint(0, n_genes)] = 1
                next_pop.append(child)
            pop = np.array(next_pop, dtype=np.int8)

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.best_mask_ is None:
            raise RuntimeError("Selector must be fitted before transforming.")
        return X[:, self.best_mask_]
