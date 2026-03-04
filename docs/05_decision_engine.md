
# Decision Engine (V1)

## Responsibilities
The DecisionEngine orchestrates:
- feature extraction (delegated to analyzers)
- normalization (delegated)
- score calculation (delegated)
- decision thresholds
- explanation

It is **pure logic**: analyzers/normalizers are injected, so unit tests can mock everything.

## Interfaces
- FeatureAnalyzer.extract(segment) -> dict
- Normalizer.normalize(features, ctx) -> dict
- ScoreCalculator.calculate(norm_features) -> float
- PlatformEvaluator.evaluate(segment, ctx, platform) -> dict

## Output
DecisionResult includes:
- decision label
- final_score
- score breakdown
- explanation (strong/weak points)
- creator recommendations (optional)
