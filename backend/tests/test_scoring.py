
from backend.engine.scoring import WeightedScoreCalculator

def test_scoring_final():
    cfg = {
        "weights": {"music":0.5,"visual":0.5,"emotion":0.0,"platform":0.0},
        "music_weights": {"a":1.0},
        "visual_weights": {"b":1.0},
        "emotion_weights": {}
    }
    s = WeightedScoreCalculator(cfg)
    scores = s.score({"music":{"a":1.0}, "visual":{"b":0.0}, "emotion":{}, "platform":{"platform_score":1.0}}, platform="tiktok")
    assert abs(scores["final"] - 0.5) < 1e-6
