class SpeechProfiler:
    """Analyzes transcribed segments and word timestamps to compute delivery profiles and pauses."""

    def __init__(self, pause_threshold_seconds=1.5):
        self.pause_threshold = pause_threshold_seconds

    def analyze(self, segments, global_duration_seconds, phone_timer_data=None):
        """Processes segments into speech blocks, pauses, and pacing metrics."""
        phone_timer_data = phone_timer_data or {}
        phone_starts = phone_timer_data.get("starts", [])
        if not phone_starts and phone_timer_data.get("start_time_seconds") is not None:
            phone_starts = [
                {
                    "start_time_seconds": phone_timer_data["start_time_seconds"],
                    "duration_seconds": phone_timer_data.get("duration_seconds", 180),
                }
            ]

        if not segments:
            timeline_items = []
            for entry in phone_starts:
                st = entry.get("start_time_seconds", 0.0)
                dur = entry.get("duration_seconds", 180.0)
                timeline_items.append(
                    {
                        "type": "phone_timer_start",
                        "start": round(st, 2),
                        "end": round(st, 2),
                        "duration": round(dur, 2),
                        "label": f"Phone Timer Started ({round(dur, 0):.0f}s)",
                    }
                )
                if st + dur <= global_duration_seconds:
                    timeline_items.append(
                        {
                            "type": "phone_timer_alarm",
                            "start": round(st + dur, 2),
                            "end": round(st + dur, 2),
                            "duration": 0.0,
                            "label": "Phone Alarm Rang",
                        }
                    )
            timeline_items.sort(key=lambda x: x["start"])
            return {
                "effective_duration_seconds": round(global_duration_seconds, 2),
                "last_speech_time_seconds": 0.0,
                "trailing_silence_seconds": round(global_duration_seconds, 2),
                "total_words": 0,
                "effective_speaking_time_seconds": 0.0,
                "total_pause_time_seconds": 0.0,
                "speaking_pace_wpm": 0.0,
                "overall_pace_wpm": 0.0,
                "pauses_count": 0,
                "phone_timer_starts": phone_starts,
                "timeline_items": timeline_items,
            }

        timeline_items = []
        total_words = 0
        effective_speaking_time = 0.0
        total_pause_time = 0.0
        pauses_count = 0

        # Check for initial pause before first speech
        first_start = segments[0]["start"]
        if first_start >= self.pause_threshold:
            timeline_items.append(
                {
                    "type": "pause",
                    "start": 0.0,
                    "end": round(first_start, 2),
                    "duration": round(first_start, 2),
                    "label": f"Intro Pause ({round(first_start, 1)}s)",
                }
            )
            total_pause_time += first_start
            pauses_count += 1

        for i, seg in enumerate(segments):
            seg_start = seg["start"]
            seg_end = seg["end"]
            seg_text = seg.get("text", "").strip()
            words_in_seg = len(seg_text.split()) if seg_text else 0
            seg_duration = max(0.01, seg_end - seg_start)
            seg_wpm = round((words_in_seg / (seg_duration / 60.0)), 1)

            total_words += words_in_seg
            effective_speaking_time += seg_duration

            timeline_items.append(
                {
                    "type": "speech",
                    "index": i + 1,
                    "start": round(seg_start, 2),
                    "end": round(seg_end, 2),
                    "duration": round(seg_duration, 2),
                    "text": seg_text,
                    "word_count": words_in_seg,
                    "wpm": seg_wpm,
                }
            )

            # Check gap between this segment and next segment
            if i < len(segments) - 1:
                next_start = segments[i + 1]["start"]
                gap = next_start - seg_end
                if gap >= self.pause_threshold:
                    timeline_items.append(
                        {
                            "type": "pause",
                            "start": round(seg_end, 2),
                            "end": round(next_start, 2),
                            "duration": round(gap, 2),
                            "label": f"Pause ({round(gap, 1)}s)",
                        }
                    )
                    total_pause_time += gap
                    pauses_count += 1

        last_speech_time = segments[-1]["end"]
        effective_duration = min(global_duration_seconds, last_speech_time)
        trailing_silence = max(0.0, global_duration_seconds - last_speech_time)

        speaking_wpm = (
            round(total_words / (effective_speaking_time / 60.0), 1)
            if effective_speaking_time > 0
            else 0.0
        )
        overall_wpm = (
            round(total_words / (effective_duration / 60.0), 1)
            if effective_duration > 0
            else 0.0
        )

        for entry in phone_starts:
            st = entry.get("start_time_seconds", 0.0)
            dur = entry.get("duration_seconds", 180.0)
            timeline_items.append(
                {
                    "type": "phone_timer_start",
                    "start": round(st, 2),
                    "end": round(st, 2),
                    "duration": round(dur, 2),
                    "label": f"Phone Timer Started ({round(dur, 0):.0f}s)",
                }
            )
            alarm_t = st + dur
            if alarm_t <= global_duration_seconds:
                timeline_items.append(
                    {
                        "type": "phone_timer_alarm",
                        "start": round(alarm_t, 2),
                        "end": round(alarm_t, 2),
                        "duration": 0.0,
                        "label": f"Phone Alarm Rang ({round(dur, 0):.0f}s timer)",
                    }
                )

        timeline_items.sort(key=lambda x: x["start"])

        return {
            "effective_duration_seconds": round(effective_duration, 2),
            "last_speech_time_seconds": round(last_speech_time, 2),
            "trailing_silence_seconds": round(trailing_silence, 2),
            "total_words": total_words,
            "effective_speaking_time_seconds": round(effective_speaking_time, 2),
            "total_pause_time_seconds": round(total_pause_time, 2),
            "speaking_pace_wpm": speaking_wpm,
            "overall_pace_wpm": overall_wpm,
            "pauses_count": pauses_count,
            "phone_timer_starts": phone_starts,
            "timeline_items": timeline_items,
        }
