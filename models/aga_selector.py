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
