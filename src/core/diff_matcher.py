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

        speaking_wpm_a = prof_a.get("speaking_pace_wpm", 0.0)
        speaking_wpm_b = prof_b.get("speaking_pace_wpm", 0.0)

        # Overall WPM based on total effective duration
        dur_a = prof_a.get("effective_duration_seconds", 0.0)
        dur_b = prof_b.get("effective_duration_seconds", 0.0)
        overall_wpm_a = prof_a.get(
            "overall_pace_wpm",
            (
                round(prof_a.get("total_words", 0) / (dur_a / 60.0), 1)
                if dur_a > 0
                else speaking_wpm_a
            ),
        )
        overall_wpm_b = prof_b.get(
            "overall_pace_wpm",
            (
                round(prof_b.get("total_words", 0) / (dur_b / 60.0), 1)
                if dur_b > 0
                else speaking_wpm_b
            ),
        )

        metrics = {
            "session_a_id": session_a.get("session_id", "Session A"),
            "session_b_id": session_b.get("session_id", "Session B"),
            "duration_a": dur_a,
            "duration_b": dur_b,
            "duration_delta": round(dur_b - dur_a, 2),
            "words_a": prof_a.get("total_words", 0),
            "words_b": prof_b.get("total_words", 0),
            "words_delta": prof_b.get("total_words", 0) - prof_a.get("total_words", 0),
            # Legacy/default speaking pace
            "wpm_a": speaking_wpm_a,
            "wpm_b": speaking_wpm_b,
            "wpm_delta": round(speaking_wpm_b - speaking_wpm_a, 1),
            # Segment WPM (excluding pauses)
            "speaking_wpm_a": speaking_wpm_a,
            "speaking_wpm_b": speaking_wpm_b,
            "speaking_wpm_delta": round(speaking_wpm_b - speaking_wpm_a, 1),
            # Overall WPM (including pauses / total duration)
            "overall_wpm_a": overall_wpm_a,
            "overall_wpm_b": overall_wpm_b,
            "overall_wpm_delta": round(overall_wpm_b - overall_wpm_a, 1),
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

        aligned_pairs = self.align_segments(items_a, items_b)
        return {"metrics": metrics, "aligned_pairs": aligned_pairs}

    def align_segments(self, items_a, items_b, gap_penalty=-0.4):
        """Aligns speech segments using Needleman-Wunsch global alignment with gaps."""
        n, m = len(items_a), len(items_b)
        if n == 0 and m == 0:
            return []

        # DP score matrix
        dp = [[0.0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            dp[i][0] = i * gap_penalty
        for j in range(1, m + 1):
            dp[0][j] = j * gap_penalty

        # Fill DP matrix
        for i in range(1, n + 1):
            text_a = items_a[i - 1].get("text", "")
            for j in range(1, m + 1):
                text_b = items_b[j - 1].get("text", "")
                sim = self.calculate_text_similarity(text_a, text_b)
                score = 2.5 * sim - 1.0
                dp[i][j] = max(
                    dp[i - 1][j - 1] + score,
                    dp[i - 1][j] + gap_penalty,
                    dp[i][j - 1] + gap_penalty,
                )

        # Backtrack to reconstruct optimal alignment sequence with gaps
        raw_pairs = []
        i, j = n, m
        while i > 0 or j > 0:
            if i > 0 and j > 0:
                text_a = items_a[i - 1].get("text", "")
                text_b = items_b[j - 1].get("text", "")
                sim = self.calculate_text_similarity(text_a, text_b)
                score = 2.5 * sim - 1.0
                if abs(dp[i][j] - (dp[i - 1][j - 1] + score)) < 1e-5:
                    raw_pairs.append((items_a[i - 1], items_b[j - 1], sim))
                    i -= 1
                    j -= 1
                    continue
            if i > 0 and abs(dp[i][j] - (dp[i - 1][j] + gap_penalty)) < 1e-5:
                raw_pairs.append((items_a[i - 1], None, 0.0))
                i -= 1
            else:
                raw_pairs.append((None, items_b[j - 1], 0.0))
                j -= 1

        raw_pairs.reverse()

        aligned_pairs = []
        for idx, (item_a, item_b, sim) in enumerate(raw_pairs, start=1):
            if not item_a or not item_b:
                status = "missing"
            elif sim >= self.similar_threshold:
                status = "similar"
            elif sim <= self.different_threshold:
                status = "different"
            else:
                status = "moderate"

            aligned_pairs.append(
                {
                    "index": idx,
                    "item_a": item_a,
                    "item_b": item_b,
                    "similarity": round(sim, 2),
                    "status": status,
                }
            )

        return aligned_pairs
