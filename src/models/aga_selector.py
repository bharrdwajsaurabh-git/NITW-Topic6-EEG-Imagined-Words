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
        return X[:, self.best_mask_ == 1]
