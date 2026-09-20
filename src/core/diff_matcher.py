import difflib


class FuzzyDiffMatcher:
    """Computes alignment and similarity between two speech sessions."""

    def __init__(self, similar_threshold=0.65, different_threshold=0.35):
        self.similar_threshold = similar_threshold
        self.different_threshold = different_threshold

    def calculate_text_similarity(self, text_a, text_b):
        if not text_a and not text_b:
            return 1.0
        if not text_a or not text_b:
            return 0.0
        matcher = difflib.SequenceMatcher(
            None, text_a.strip().lower(), text_b.strip().lower()
        )
        return matcher.ratio()

    def compare_sessions(self, session_a, session_b):
        """Returns comparison metrics and aligned segment pairs."""
        prof_a = session_a.get("profile") or {}
        prof_b = session_b.get("profile") or {}

        metrics = {
            "session_a_id": session_a.get("session_id", "Session A"),
            "session_b_id": session_b.get("session_id", "Session B"),
            "duration_a": prof_a.get("effective_duration_seconds", 0.0),
            "duration_b": prof_b.get("effective_duration_seconds", 0.0),
            "duration_delta": round(
                prof_b.get("effective_duration_seconds", 0.0)
                - prof_a.get("effective_duration_seconds", 0.0),
                2,
            ),
            "words_a": prof_a.get("total_words", 0),
            "words_b": prof_b.get("total_words", 0),
            "words_delta": prof_b.get("total_words", 0) - prof_a.get("total_words", 0),
            "wpm_a": prof_a.get("speaking_pace_wpm", 0.0),
            "wpm_b": prof_b.get("speaking_pace_wpm", 0.0),
            "wpm_delta": round(
                prof_b.get("speaking_pace_wpm", 0.0)
                - prof_a.get("speaking_pace_wpm", 0.0),
                1,
            ),
            "pauses_a": prof_a.get("pauses_count", 0),
            "pauses_b": prof_b.get("pauses_count", 0),
            "pauses_delta": prof_b.get("pauses_count", 0)
            - prof_a.get("pauses_count", 0),
        }

        # Extract text segments from timeline or transcription
        items_a = [
            item
            for item in prof_a.get("timeline_items", [])
            if item.get("type") == "speech"
        ]
        items_b = [
            item
            for item in prof_b.get("timeline_items", [])
            if item.get("type") == "speech"
        ]

        full_text_a = " ".join([item.get("text", "") for item in items_a])
        full_text_b = " ".join([item.get("text", "") for item in items_b])
        metrics["overall_similarity"] = round(
            self.calculate_text_similarity(full_text_a, full_text_b), 2
        )

        aligned_pairs = []
        max_len = max(len(items_a), len(items_b))

        # Align segments sequentially, pairing them up
        for i in range(max_len):
            item_a = items_a[i] if i < len(items_a) else None
            item_b = items_b[i] if i < len(items_b) else None

            text_a = item_a.get("text", "") if item_a else ""
            text_b = item_b.get("text", "") if item_b else ""

            sim = self.calculate_text_similarity(text_a, text_b)
            if not text_a or not text_b:
                status = "missing"
            elif sim >= self.similar_threshold:
                status = "similar"
            elif sim <= self.different_threshold:
                status = "different"
            else:
                status = "moderate"

            aligned_pairs.append(
                {
                    "index": i + 1,
                    "item_a": item_a,
                    "item_b": item_b,
                    "similarity": round(sim, 2),
                    "status": status,
                }
            )

        return {"metrics": metrics, "aligned_pairs": aligned_pairs}
