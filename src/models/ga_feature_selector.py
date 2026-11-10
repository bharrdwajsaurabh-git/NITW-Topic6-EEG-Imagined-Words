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
