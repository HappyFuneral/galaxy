# Patch: DecisionEngine.__init__ unexpected keyword 'scorers'

Cause:
- Your DecisionEngine originally accepted only (thresholds_cfg).
- Factory builds it with scorers/platform_evaluator/final_weights.

Fix:
- Replace backend/engine/decision_engine.py with the patched version.
- Replace backend/engine/factory.py with the patched version.
- Update config/thresholds.yaml to include decision_thresholds.

After applying, EngineRunner can call engine.evaluate(...) and still keep legacy engine.decide(...).
