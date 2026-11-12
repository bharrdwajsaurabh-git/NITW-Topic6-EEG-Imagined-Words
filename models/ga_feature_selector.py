"""
models/ga_feature_selector.py
=============================
Evolutionary Optimization for EEG Imagined Speech Feature Selection.
Faithful implementation of the Genetic Algorithm (GA) feature optimization
framework described in:
"Feature Generation with Genetic Algorithms for Imagined Speech Electroencephalogram
Signal Classification" (Lara-Arellano et al., Eng 2025).
"""

import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from typing import Tuple, List, Optional


class GeneticFeatureSelector:
    """
    Genetic Algorithm to discover the optimal discriminative feature subset
    from high-dimensional EEG spatio-temporal features.
    """

    def __init__(
        self,
        n_population: int = 30,
        n_generations: int = 20,
        crossover_rate: float = 0.8,
        mutation_rate: float = 0.03,
        parsimony_penalty: float = 0.01,
        cv_splits: int = 3,
        random_state: int = 42
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
        self, chromosome: np.ndarray, X: np.ndarray, y: np.ndarray
    ) -> float:
        """
        Calculates fitness score: Cross-validation accuracy minus a small penalty
        for feature redundancy (parsimony).
        """
        selected_indices = np.where(chromosome == 1)[0]
        n_selected = len(selected_indices)

        if n_selected == 0:
            return 0.0

        X_subset = X[:, selected_indices]
        skf = StratifiedKFold(n_splits=self.cv_splits, shuffle=True, random_state=self.random_state)
        scores = []

        clf = SVC(kernel="rbf", C=1.0)

        for train_idx, val_idx in skf.split(X_subset, y):
            clf.fit(X_subset[train_idx], y[train_idx])
            preds = clf.predict(X_subset[val_idx])
            scores.append(accuracy_score(y[val_idx], preds))

        mean_acc = float(np.mean(scores))
        # Parsimony penalty favors compact representations
        penalty = self.parsimony_penalty * (n_selected / len(chromosome))
        fitness = mean_acc - penalty
        return fitness

    def fit(self, X: np.ndarray, y: np.ndarray) -> "GeneticFeatureSelector":
        """
        Runs genetic evolution over n_generations.
        """
        np.random.seed(self.random_state)
        n_features = X.shape[1]

        print(f"[*] Starting Genetic Algorithm Optimization:")
        print(f"    - Population: {self.n_population} | Generations: {self.n_generations}")
        print(f"    - Input Features: {n_features}")

        # Initialize random binary population (each feature has ~30% probability initially)
        population = (np.random.rand(self.n_population, n_features) < 0.3).astype(np.int8)

        # Ensure at least 1 feature is selected per individual
        for ind in population:
            if not np.any(ind):
                ind[np.random.randint(0, n_features)] = 1

        for gen in range(self.n_generations):
            fitness_scores = np.array([
                self._evaluate_fitness(ind, X, y) for ind in population
            ])

            gen_best_idx = np.argmax(fitness_scores)
            gen_best_fit = fitness_scores[gen_best_idx]
            self.history_.append(gen_best_fit)

            if gen_best_fit > self.best_fitness_:
                self.best_fitness_ = gen_best_fit
                self.best_mask_ = population[gen_best_idx].copy()

            selected_count = np.sum(self.best_mask_)
            print(
                f"    [Gen {gen+1:02d}/{self.n_generations:02d}] "
                f"Best Fitness: {self.best_fitness_:.4f} | "
                f"Active Features: {selected_count}/{n_features}"
            )

            # Elitism: retain top 2 individuals
            elite_indices = np.argsort(fitness_scores)[-2:]
            next_generation = [population[i].copy() for i in elite_indices]

            # Reproduction loop
            while len(next_generation) < self.n_population:
                # Tournament Selection (size 3)
                t1, t2 = np.random.choice(self.n_population, 3, replace=False), np.random.choice(self.n_population, 3, replace=False)
                parent1 = population[t1[np.argmax(fitness_scores[t1])]]
                parent2 = population[t2[np.argmax(fitness_scores[t2])]]

                # Crossover
                if np.random.rand() < self.crossover_rate:
                    cross_point = np.random.randint(1, n_features)
                    child1 = np.concatenate([parent1[:cross_point], parent2[cross_point:]])
                    child2 = np.concatenate([parent2[:cross_point], parent1[cross_point:]])
                else:
                    child1, child2 = parent1.copy(), parent2.copy()

                # Mutation
                for child in [child1, child2]:
                    mutation_mask = np.random.rand(n_features) < self.mutation_rate
                    child[mutation_mask] = 1 - child[mutation_mask]
                    if not np.any(child):
                        child[np.random.randint(0, n_features)] = 1
                    if len(next_generation) < self.n_population:
                        next_generation.append(child)

            population = np.array(next_generation)

        print(f"[+] Genetic Algorithm completed.")
        print(f"    - Optimal Subset: {np.sum(self.best_mask_)} / {n_features} features.")
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Projects feature matrix onto selected optimal feature subspace."""
        if self.best_mask_ is None:
            raise RuntimeError("Selector must be fitted before transforming.")
        return X[:, self.best_mask_ == 1]


class PaperRankGeneticSelector:
    """
    Primary Paper Genetic Algorithm Selector (Lara-Arellano et al., Eng MDPI 2025).
    Implements Rank Selection + Homogeneous Uniform Crossover + Bit-Flip Mutation
    with heuristic kNN search over k in {1, 3, 5, 7} evaluated inside train-only CV
    (zero holdout/test leakage). Supports both scalar feature-group selection and
    14-electrode + 6-band spatial-covariance masking.
    """
    def __init__(
        self,
        n_population: int = 40,
        n_generations: int = 20,
        mutation_rate: float = 0.04,
        k_candidates: tuple = (1, 3, 5, 7),
        metric: str = "cosine",
        cv_splits: int = 3,
        random_state: int = 42,
    ):
        self.n_population = n_population
        self.n_generations = n_generations
        self.mutation_rate = mutation_rate
        self.k_candidates = k_candidates
        self.metric = metric
        self.cv_splits = cv_splits
        self.random_state = random_state
        self.best_mask_: Optional[np.ndarray] = None
        self.best_k_: int = 1
        self.best_fitness_: float = -1.0
        self.history_: list = []

    def fit(self, X: np.ndarray, y: np.ndarray, block_slices: Optional[list] = None):
        """
        If `block_slices` is None, chromosome operates over all columns (`n_genes = X.shape[1]`).
        If `block_slices` is provided (list of boolean column masks per gene, e.g., 228 or 20 genes),
        chromosome toggles logical groups cleanly without column explosion.
        """
        from sklearn.neighbors import KNeighborsClassifier

        rng = np.random.RandomState(self.random_state)
        n_genes = len(block_slices) if block_slices is not None else X.shape[1]
        skf = StratifiedKFold(n_splits=self.cv_splits, shuffle=True, random_state=self.random_state)
        folds = list(skf.split(X, y))

        pop = (rng.rand(self.n_population, n_genes) < 0.65).astype(np.int8)
        pop[0] = np.ones(n_genes, dtype=np.int8)  # Ensure full-set genome is evaluated in Gen 0
        for g in pop:
            if not np.any(g):
                g[rng.randint(0, n_genes)] = 1

        # Pick heuristic k on train-only CV first
        best_k = self.k_candidates[0]
        best_k_acc = -1.0
        for kv in self.k_candidates:
            cs = []
            for ftr, fva in folds:
                wmode = "distance" if (kv > 1 and self.metric == "cosine") else "uniform"
                clf = KNeighborsClassifier(n_neighbors=kv, metric=self.metric, weights=wmode)
                clf.fit(X[ftr], y[ftr])
                cs.append(accuracy_score(y[fva], clf.predict(X[fva])))
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

        for gen in range(self.n_generations):
            fits = np.zeros(self.n_population, dtype=np.float64)
            for idx_i, chrom in enumerate(pop):
                cmask = expand_mask(chrom)
                Xs = X[:, cmask]
                if self.metric == "cosine":
                    Xn = Xs / (np.linalg.norm(Xs, axis=1, keepdims=True) + 1e-12)
                    sim = Xn @ Xn.T
                    Dist = 1.0 - sim
                else:
                    n2 = np.sum(Xs * Xs, axis=1)
                    Dist = np.maximum(n2[:, None] + n2[None, :] - 2.0 * (Xs @ Xs.T), 0.0)
                cs = []
                for ftr, fva in folds:
                    Dsub = Dist[np.ix_(fva, ftr)]
                    if best_k == 1:
                        pred = y[ftr][np.argmin(Dsub, axis=1)]
                    else:
                        nn = np.argpartition(Dsub, min(best_k, Dsub.shape[1] - 1), axis=1)[:, :best_k]
                        lbls = y[ftr][nn]
                        classes = np.unique(y[ftr])
                        if wmode == "distance":
                            d_nn = np.take_along_axis(Dsub, nn, axis=1)
                            w_nn = 1.0 / np.maximum(d_nn, 1e-4)
                        else:
                            w_nn = np.ones_like(lbls, dtype=np.float64)
                        probs = np.zeros((len(fva), len(classes)), dtype=np.float64)
                        for ci, cv in enumerate(classes):
                            probs[:, ci] = np.sum(w_nn * (lbls == cv), axis=1)
                        pred = classes[np.argmax(probs, axis=1)]
                    cs.append(float(np.mean(pred == y[fva])))
                fits[idx_i] = float(np.mean(cs))

            bi = int(np.argmax(fits))
            if fits[bi] > self.best_fitness_:
                self.best_fitness_ = float(fits[bi])
                self.best_mask_ = expand_mask(pop[bi])
            self.history_.append(float(self.best_fitness_))

            # Rank Selection + Elitism (top 2)
            elite_idx = np.argsort(fits)[-2:]
            next_pop = [pop[elite_idx[1]].copy(), pop[elite_idx[0]].copy()]
            ranks = np.argsort(np.argsort(fits)) + 1
            probs = ranks / float(np.sum(ranks))
            while len(next_pop) < self.n_population:
                pa = rng.choice(self.n_population, p=probs)
                pb = rng.choice(self.n_population, p=probs)
                # Homogeneous Uniform Crossover + Bit-Flip Mutation
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
