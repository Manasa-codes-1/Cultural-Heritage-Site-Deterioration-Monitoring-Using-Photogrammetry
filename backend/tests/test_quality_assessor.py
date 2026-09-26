import numpy as np
from app.processing.quality_assessor import ImageQualityAssessor


def test_quality_assessor_sharp_image():
    assessor = ImageQualityAssessor(min_width=100, min_height=100, blur_threshold=50.0)
    # Generate high-contrast textured pattern
    sharp_img = np.zeros((200, 200, 3), dtype=np.uint8)
    sharp_img[::4, :] = 255
    sharp_img[:, ::4] = 255

    result = assessor.assess_array(sharp_img)
    assert result["valid"] is True
    assert result["blur"]["status"] == "pass"
    assert result["resolution"]["status"] == "pass"
    assert result["quality_score"] > 50.0


def test_quality_assessor_blurry_image():
    assessor = ImageQualityAssessor(min_width=100, min_height=100, blur_threshold=100.0)
    # Generate uniform/smooth flat image (variance of laplacian will be zero)
    flat_img = np.full((200, 200, 3), 128, dtype=np.uint8)

    result = assessor.assess_array(flat_img)
    assert result["valid"] is True
    assert result["blur"]["status"] == "fail"
    assert result["blur"]["score"] == 0.0


def test_quality_assessor_underexposed():
    assessor = ImageQualityAssessor(underexposure_thresh=40.0)
    # Pure dark image
    dark_img = np.full((200, 200, 3), 10, dtype=np.uint8)

    result = assessor.assess_array(dark_img)
    assert result["valid"] is True
    assert result["brightness"]["status"] == "fail"
    assert result["brightness"]["score"] < 40.0
