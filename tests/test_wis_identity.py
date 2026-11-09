"""Verify the interval-score identity against the unchanged archived R scorer."""
from __future__ import annotations

import csv
from fractions import Fraction
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ARTICLE = Path(__file__).resolve().parents[1]
SIZES = (2, 3, 7, 48, 51, 64, 2000)


def rho(probability, residual):
    return probability * residual if residual >= 0 else (probability - 1) * residual


def interval_score(alpha, lower, upper, observed):
    """Central interval score, evaluated independently of check loss."""
    score = upper - lower
    if observed < lower:
        score += 2 * (lower - observed) / alpha
    if observed > upper:
        score += 2 * (observed - upper) / alpha
    return score


def quantile_grid_score(values, observed):
    ordered = sorted(values)
    size = len(ordered)
    return Fraction(2, size) * sum(
        rho(Fraction(index, size + 1), observed - value)
        for index, value in enumerate(ordered, 1))


def interval_representation(values, observed):
    ordered = sorted(values)
    size = len(ordered)
    pairs = size // 2
    weighted_intervals = sum(
        Fraction(index, size + 1) * interval_score(
            Fraction(2 * index, size + 1),
            ordered[index - 1], ordered[size - index], observed)
        for index in range(1, pairs + 1))
    if size % 2:
        return (abs(observed - ordered[pairs]) / 2 + weighted_intervals) / (pairs + Fraction(1, 2))
    return weighted_intervals / pairs


def cases():
    for size in SIZES:
        regular = [Fraction(-3) + Fraction(6 * index, size - 1) for index in range(size)]
        tied = [Fraction(index // 4, max(1, (size - 1) // 4)) - 1 for index in range(size)]
        point = [Fraction(2, 3)] * size
        for name, values, observed in (
            ("below", regular, Fraction(-4)),
            ("inside", regular, Fraction(1, 7)),
            ("above", regular, Fraction(4)),
            ("boundary", regular, regular[0]),
            ("ties", tied, Fraction(-1, 3)),
            ("point_miss", point, Fraction(-1, 3)),
            ("point_hit", point, Fraction(2, 3)),
        ):
            yield f"s{size}_{name}", values, observed


class WeightedIntervalIdentityTests(unittest.TestCase):
    def test_even_sizes_have_no_separate_median_term(self):
        for name, values, observed in cases():
            if len(values) % 2 == 0:
                with self.subTest(case=name):
                    self.assertEqual(quantile_grid_score(values, observed),
                                     interval_representation(values, observed))

    def test_odd_sizes_match_median_inclusive_wis(self):
        for name, values, observed in cases():
            if len(values) % 2:
                with self.subTest(case=name):
                    self.assertEqual(quantile_grid_score(values, observed),
                                     interval_representation(values, observed))

    def test_pairing_identity_handles_interval_boundaries_and_point_intervals(self):
        for alpha in (Fraction(1, 4), Fraction(1, 2), Fraction(4, 5)):
            for lower, upper in ((Fraction(-2), Fraction(3)), (Fraction(2, 3), Fraction(2, 3))):
                for observed in (lower - 1, lower, (lower + upper) / 2, upper, upper + 1):
                    with self.subTest(alpha=alpha, bounds=(lower, upper), observed=observed):
                        pair = rho(alpha / 2, observed - lower) + rho(1 - alpha / 2, observed - upper)
                        self.assertEqual(pair, alpha * interval_score(alpha, lower, upper, observed) / 2)

    def test_archived_r_scorer_matches_the_independent_identity(self):
        rscript = shutil.which("Rscript")
        self.assertIsNotNone(rscript, "Rscript is required to verify the archived scoring implementation")
        expected = {}
        with tempfile.TemporaryDirectory(prefix="wis_identity_") as directory:
            temporary = Path(directory)
            input_path = temporary / "cases.csv"
            output_path = temporary / "scores.csv"
            driver = temporary / "check.R"
            with input_path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(("case", "observed", "sample"))
                for name, values, observed in cases():
                    expected[name] = interval_representation(values, observed)
                    # Deliberately unsorted: exercise the scorer's own ordering.
                    for value in reversed(values):
                        writer.writerow((name, float(observed), float(value)))
            driver.write_text('''args <- commandArgs(trailingOnly=TRUE)
source(args[[1]])
cases <- read.csv(args[[2]], stringsAsFactors=FALSE)
result <- do.call(rbind, lapply(split(cases, cases$case), function(x) {
    scored <- post_crps_quantile_approx(x$observed[[1]], matrix(x$sample, ncol=1))
    stopifnot(scored$n_samples_eff[[1]] == nrow(x))
    data.frame(case=x$case[[1]], score=scored$crps[[1]])
}))
write.csv(result, args[[3]], row.names=FALSE)
''')
            result = subprocess.run(
                [rscript, "--vanilla", str(driver),
                 str(ARTICLE / "artifacts/no_refit_revision/inputs/original_score_functions.R"),
                 str(input_path), str(output_path)],
                text=True, capture_output=True, timeout=60, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            with output_path.open(newline="") as stream:
                actual = {row["case"]: float(row["score"]) for row in csv.DictReader(stream)}
            self.assertEqual(set(actual), set(expected))
            for name, exact in expected.items():
                with self.subTest(case=name):
                    self.assertAlmostEqual(actual[name], float(exact), places=12)


if __name__ == "__main__":
    unittest.main()
