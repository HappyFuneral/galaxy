
from backend.pipeline.segmenter import generate_sliding_segments

def test_segments():
    segs = generate_sliding_segments(200.0, window_s=45.0, step_s=15.0)
    assert len(segs) > 0
    assert segs[0].start == 0.0
