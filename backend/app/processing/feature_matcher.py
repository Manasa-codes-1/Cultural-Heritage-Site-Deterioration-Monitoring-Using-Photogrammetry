from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import cv2
import numpy as np
from app.core.config import settings


class ImageFeatureMatcher:
    """
    OpenCV ORB & BFMatcher-based Feature Matching and Survey Collection Readiness Engine.
    
    Responsibilities:
    - Extract invariant keypoints and binary descriptors using ORB.
    - Perform pairwise feature matching using Brute-Force Matcher with Hamming norm.
    - Filter candidate matches using Lowe's ratio test.
    - Evaluate pairwise feature correspondence and heuristic overlap indicators.
    - Construct an image connectivity graph for the survey collection.
    - Identify isolated and weakly connected camera viewpoints.
    - Classify overall collection photogrammetric readiness.
    
    IMPORTANT RESEARCH DISCLAIMER:
    This module provides an engineering-level image-quality and feature-correspondence
    assessment intended to support photogrammetric preprocessing. Its thresholds are
    configurable heuristics and should not be interpreted as universally validated
    photogrammetry quality criteria.
    """

    def __init__(
        self,
        max_features: int = settings.MATCHING_MAX_FEATURES,
        ratio_thresh: float = settings.MATCHING_RATIO_THRESH,
        min_good_matches: int = settings.MATCHING_MIN_GOOD_MATCHES,
        warn_good_matches: int = settings.MATCHING_WARN_GOOD_MATCHES,
        min_keypoints: int = settings.MATCHING_MIN_KEYPOINTS,
        max_image_dim: int = settings.MATCHING_IMAGE_MAX_DIM,
        max_pairs_per_survey: int = settings.MATCHING_MAX_PAIRS_PER_SURVEY,
    ):
        self.max_features = max_features
        self.ratio_thresh = ratio_thresh
        self.min_good_matches = min_good_matches
        self.warn_good_matches = warn_good_matches
        self.min_keypoints = min_keypoints
        self.max_image_dim = max_image_dim
        self.max_pairs_per_survey = max_pairs_per_survey

    def extract_features(
        self, image_input: Path | np.ndarray
    ) -> Tuple[List[cv2.KeyPoint], Optional[np.ndarray], Tuple[int, int]]:
        """
        Extracts ORB keypoints and descriptors from an image file or NumPy array.
        Resizes temporarily if dimensions exceed max_image_dim for CPU efficiency.
        """
        if isinstance(image_input, Path):
            if not image_input.exists():
                return [], None, (0, 0)
            img = cv2.imread(str(image_input))
            if img is None:
                return [], None, (0, 0)
        else:
            img = image_input

        h, w = img.shape[:2]
        channels = img.shape[2] if len(img.shape) > 2 else 1

        # Resize if dimensions exceed threshold for fast CPU matching
        scale = 1.0
        max_dim = max(h, w)
        if max_dim > self.max_image_dim:
            scale = self.max_image_dim / float(max_dim)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if channels > 1 else img

        orb = cv2.ORB_create(
            nfeatures=self.max_features,
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=31,
            firstLevel=0,
            WTA_K=2,
            scoreType=cv2.ORB_HARRIS_SCORE,
            patchSize=31,
            fastThreshold=20,
        )

        keypoints, descriptors = orb.detectAndCompute(gray, None)
        return keypoints, descriptors, (w, h)

    def match_descriptors(
        self,
        keypoints_a: List[cv2.KeyPoint],
        descriptors_a: Optional[np.ndarray],
        keypoints_b: List[cv2.KeyPoint],
        descriptors_b: Optional[np.ndarray],
    ) -> Dict[str, Any]:
        """
        Performs pairwise matching using BFMatcher (Hamming distance) and Lowe's ratio test.
        """
        kps_a_count = len(keypoints_a)
        kps_b_count = len(keypoints_b)

        # Check for insufficient keypoints
        if (
            descriptors_a is None
            or descriptors_b is None
            or kps_a_count < self.min_keypoints
            or kps_b_count < self.min_keypoints
        ):
            return {
                "keypoints_a": kps_a_count,
                "keypoints_b": kps_b_count,
                "candidate_matches": 0,
                "good_matches": 0,
                "match_ratio": 0.0,
                "estimated_overlap": "Insufficient Features",
                "status": "INSUFFICIENT_FEATURES",
                "recommendation": (
                    f"One or both images have fewer than {self.min_keypoints} keypoints "
                    f"(Image A: {kps_a_count}, Image B: {kps_b_count}). "
                    "Ensure adequate texture and sharp focus."
                ),
            }

        # BFMatcher with NORM_HAMMING for ORB binary descriptors
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        # k-NN match with k=2
        try:
            knn_matches = bf.knnMatch(descriptors_a, descriptors_b, k=2)
        except Exception:
            knn_matches = []

        candidate_count = len(knn_matches)
        good_matches = []

        # Apply Lowe's ratio test
        for match_pair in knn_matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < self.ratio_thresh * n.distance:
                    good_matches.append(m)

        good_count = len(good_matches)
        min_kps = max(min(kps_a_count, kps_b_count), 1)
        match_ratio = round(good_count / float(min_kps), 3)

        # Classify status & overlap indicator
        if good_count >= self.min_good_matches:
            status = "GOOD"
            if good_count >= 80:
                overlap = "High Correspondence (Heuristic)"
            else:
                overlap = "Moderate Correspondence (Heuristic)"
            recommendation = (
                f"Sufficient feature correspondence verified ({good_count} good matches, "
                f"ratio {match_ratio:.2f}). Suitable baseline for camera pose estimation."
            )
        elif good_count >= self.warn_good_matches:
            status = "WARNING"
            overlap = "Weak Correspondence (Heuristic)"
            recommendation = (
                f"Marginal feature correspondence ({good_count} good matches). "
                "Camera baseline may be wide; supplementary intermediate view recommended."
            )
        else:
            status = "POOR"
            overlap = "Minimal / Insufficient Correspondence (Heuristic)"
            recommendation = (
                f"Inadequate feature correspondence ({good_count} good matches < {self.warn_good_matches}). "
                "Viewpoints likely lack sufficient spatial overlap or exhibit excessive perspective distortion."
            )

        return {
            "keypoints_a": kps_a_count,
            "keypoints_b": kps_b_count,
            "candidate_matches": candidate_count,
            "good_matches": good_count,
            "match_ratio": match_ratio,
            "estimated_overlap": overlap,
            "status": status,
            "recommendation": recommendation,
        }

    def select_pairs(self, image_ids: List[str]) -> List[Tuple[str, str]]:
        """
        Intelligently selects pairs to compare without combinatorial explosion.
        - For small sets (<= 12), tests all N*(N-1)/2 pairs.
        - For larger sets, prioritizes sequential/neighbor and stride pairs up to max_pairs.
        """
        n = len(image_ids)
        if n < 2:
            return []

        all_pairs = []
        if n <= 12:
            for i in range(n):
                for j in range(i + 1, n):
                    all_pairs.append((image_ids[i], image_ids[j]))
            return all_pairs

        # Priority 1: Contiguous sequential pairs (i <-> i+1)
        for i in range(n - 1):
            all_pairs.append((image_ids[i], image_ids[i + 1]))

        # Priority 2: Stride-2 pairs (i <-> i+2)
        for i in range(n - 2):
            if len(all_pairs) >= self.max_pairs_per_survey:
                break
            all_pairs.append((image_ids[i], image_ids[i + 2]))

        # Priority 3: Stride-3 pairs (i <-> i+3)
        for i in range(n - 3):
            if len(all_pairs) >= self.max_pairs_per_survey:
                break
            all_pairs.append((image_ids[i], image_ids[i + 3]))

        return all_pairs[: self.max_pairs_per_survey]

    def analyze_survey_collection(
        self,
        images_info: List[Dict[str, Any]],  # list of {"id": str, "filename": str, "path": Path}
    ) -> Dict[str, Any]:
        """
        Performs collection-level matching, builds connectivity graph, and evaluates readiness.
        """
        total_images = len(images_info)
        if total_images < 2:
            return {
                "images_analyzed": total_images,
                "pairs_analyzed": 0,
                "good_pairs": 0,
                "warning_pairs": 0,
                "poor_pairs": 0,
                "average_good_matches": 0.0,
                "readiness_status": "INSUFFICIENT_IMAGE_CONNECTIVITY",
                "isolated_image_ids": [img["id"] for img in images_info],
                "weakly_connected_image_ids": [],
                "connectivity_nodes": [
                    {"id": img["id"], "filename": img["filename"], "degree": 0, "status": "isolated"}
                    for img in images_info
                ],
                "connectivity_edges": [],
                "pair_results": [],
                "recommendations": [
                    "A minimum of 3 overlapping survey images is required for multi-view photogrammetric reconstruction."
                ],
                "is_heuristic": True,
            }

        # 1. Extract features for all images once (cache descriptors)
        cached_features: Dict[str, Tuple[List[cv2.KeyPoint], Optional[np.ndarray]]] = {}
        for img_info in images_info:
            img_id = img_info["id"]
            kps, descs, _ = self.extract_features(img_info["path"])
            cached_features[img_id] = (kps, descs)

        # 2. Select image pairs
        image_ids = [img["id"] for img in images_info]
        pairs_to_test = self.select_pairs(image_ids)

        pair_results: List[Dict[str, Any]] = []
        good_pairs = 0
        warning_pairs = 0
        poor_pairs = 0
        total_good_matches = 0

        # Adjacency tracking for connectivity
        degree_map: Dict[str, int] = {img_id: 0 for img_id in image_ids}
        edges: List[Dict[str, Any]] = []

        # 3. Match each pair
        for img_a_id, img_b_id in pairs_to_test:
            kps_a, descs_a = cached_features[img_a_id]
            kps_b, descs_b = cached_features[img_b_id]

            match_res = self.match_descriptors(kps_a, descs_a, kps_b, descs_b)
            status = match_res["status"]

            if status == "GOOD":
                good_pairs += 1
                degree_map[img_a_id] += 1
                degree_map[img_b_id] += 1
            elif status == "WARNING":
                warning_pairs += 1
            else:
                poor_pairs += 1

            total_good_matches += match_res["good_matches"]

            # Add to edge list if good or warning
            if status in ("GOOD", "WARNING"):
                edges.append({
                    "source": img_a_id,
                    "target": img_b_id,
                    "good_matches": match_res["good_matches"],
                    "match_ratio": match_res["match_ratio"],
                    "status": status,
                })

            pair_record = {
                "image_a_id": img_a_id,
                "image_b_id": img_b_id,
                **match_res,
            }
            pair_results.append(pair_record)

        pairs_analyzed = len(pairs_to_test)
        avg_good = round(total_good_matches / max(pairs_analyzed, 1), 1)

        # 4. Classify nodes: isolated, weakly_connected, well_connected
        isolated_ids: List[str] = []
        weakly_connected_ids: List[str] = []
        nodes: List[Dict[str, Any]] = []

        id_to_filename = {img["id"]: img["filename"] for img in images_info}

        for img_id, degree in degree_map.items():
            if degree == 0:
                node_status = "isolated"
                isolated_ids.append(img_id)
            elif degree == 1:
                node_status = "weakly_connected"
                weakly_connected_ids.append(img_id)
            else:
                node_status = "well_connected"

            nodes.append({
                "id": img_id,
                "filename": id_to_filename.get(img_id, "unknown"),
                "degree": degree,
                "status": node_status,
            })

        # 5. Evaluate overall survey photogrammetric readiness
        recommendations: List[str] = []

        if total_images < 3:
            readiness = "INSUFFICIENT_IMAGE_CONNECTIVITY"
            recommendations.append("A minimum of 3 overlapping survey images is required for 3D reconstruction.")
        elif len(isolated_ids) >= total_images * 0.40 or good_pairs == 0:
            readiness = "RECAPTURE_REQUIRED"
            recommendations.append(
                f"{len(isolated_ids)} of {total_images} images are completely isolated with no verified feature matches. "
                "Recapture survey with closer viewpoint spacing (recommended 60-80% visual overlap)."
            )
        elif len(isolated_ids) > 0 or len(weakly_connected_ids) > 0 or (pairs_analyzed > 0 and good_pairs / pairs_analyzed < 0.5):
            readiness = "READY_WITH_WARNINGS"
            if isolated_ids:
                names = [id_to_filename.get(i, i) for i in isolated_ids[:3]]
                recommendations.append(
                    f"Isolated images detected ({', '.join(names)}). "
                    "These views may fail to register in Structure-from-Motion. Supplement with bridging viewpoints."
                )
            if weakly_connected_ids:
                names = [id_to_filename.get(i, i) for i in weakly_connected_ids[:3]]
                recommendations.append(
                    f"Weakly connected images detected ({', '.join(names)} with only 1 matching view). "
                    "Consider additional cross-angle coverage."
                )
            if good_pairs / max(pairs_analyzed, 1) < 0.5:
                recommendations.append(
                    f"Over half of analyzed image pairs ({poor_pairs + warning_pairs}/{pairs_analyzed}) "
                    "show weak or poor correspondence. Review viewing angle angular disparity."
                )
        else:
            readiness = "READY"
            recommendations.append(
                f"Robust feature connectivity confirmed across {good_pairs} image pairs. "
                f"All {total_images} images are interconnected with 2 or more strong matches. "
                "Dataset meets optical requirements for Structure-from-Motion."
            )

        return {
            "images_analyzed": total_images,
            "pairs_analyzed": pairs_analyzed,
            "good_pairs": good_pairs,
            "warning_pairs": warning_pairs,
            "poor_pairs": poor_pairs,
            "average_good_matches": avg_good,
            "readiness_status": readiness,
            "isolated_image_ids": isolated_ids,
            "weakly_connected_image_ids": weakly_connected_ids,
            "connectivity_nodes": nodes,
            "connectivity_edges": edges,
            "pair_results": pair_results,
            "recommendations": recommendations,
            "is_heuristic": True,
        }


# Global default instance
feature_matcher = ImageFeatureMatcher()
