class SpeechProfiler:
    """Analyzes transcribed segments, pauses, and phone timer events into an inline timeline."""

    def __init__(self, pause_threshold_seconds=1.5):
        self.pause_threshold = pause_threshold_seconds

    def _format_time(self, seconds):
        sec = max(0, int(seconds))
        return f"{sec // 60:02d}:{sec % 60:02d}"

    def analyze(self, segments, global_duration_seconds, phone_timer_data=None):
        """Processes segments into speech blocks, pauses, and pacing metrics with inline events."""
        phone_timer_data = phone_timer_data or {}
        phone_starts = phone_timer_data.get("starts", [])
        if not phone_starts and phone_timer_data.get("start_time_seconds") is not None:
            phone_starts = [
                {
                    "start_time_seconds": phone_timer_data["start_time_seconds"],
                    "duration_seconds": phone_timer_data.get("duration_seconds", 180),
                }
            ]

        # Gather point events
        events = []
        for entry in phone_starts:
            st = entry.get("start_time_seconds", 0.0)
            dur = entry.get("duration_seconds", 180.0)
            events.append(
                {
                    "type": "phone_timer_start",
                    "time": round(st, 2),
                    "duration": round(dur, 2),
                    "label": f"Phone Timer Started ({self._format_time(dur)})",
                }
            )
            alarm_t = st + dur
            if alarm_t <= global_duration_seconds + 0.5:
                events.append(
                    {
                        "type": "phone_timer_alarm",
                        "time": round(alarm_t, 2),
                        "duration": 0.0,
                        "label": f"Phone Alarm Rang ({self._format_time(dur)} timer)",
                    }
                )

        if not segments:
            timeline_items = []
            for ev in sorted(events, key=lambda x: x["time"]):
                timeline_items.append(
                    {
                        "type": ev["type"],
                        "start": ev["time"],
                        "end": ev["time"],
                        "duration": ev.get("duration", 0.0),
                        "label": ev["label"],
                    }
                )
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

        # Integrate events into segments by splitting speech blocks inline
        integrated_items = self._integrate_events_into_segments(segments, events)

        timeline_items = []
        total_words = 0
        effective_speaking_time = 0.0
        total_pause_time = 0.0
        pauses_count = 0

        # Check for initial pause before first speech
        first_speech = next(
            (item for item, itype in integrated_items if itype == "speech"), None
        )
        if first_speech and first_speech["start"] >= self.pause_threshold:
            intro_gap = first_speech["start"]
            timeline_items.append(
                {
                    "type": "pause",
                    "start": 0.0,
                    "end": round(intro_gap, 2),
                    "duration": round(intro_gap, 2),
                    "label": f"Intro Pause ({round(intro_gap, 1)}s)",
                }
            )
            total_pause_time += intro_gap
            pauses_count += 1

        last_speech_end = 0.0
        speech_idx = 1

        for idx, (data, itype) in enumerate(integrated_items):
            if itype == "speech":
                seg_start = data["start"]
                seg_end = data["end"]
                seg_text = data.get("text", "").strip()
                words_in_seg = len(seg_text.split()) if seg_text else 0
                seg_dur = max(0.01, seg_end - seg_start)
                seg_wpm = round((words_in_seg / (seg_dur / 60.0)), 1)

                total_words += words_in_seg
                effective_speaking_time += seg_dur

                # Check pause between previous speech end and this speech start
                if (
                    last_speech_end > 0.0
                    and (seg_start - last_speech_end) >= self.pause_threshold
                ):
                    pause_dur = seg_start - last_speech_end
                    timeline_items.append(
                        {
                            "type": "pause",
                            "start": round(last_speech_end, 2),
                            "end": round(seg_start, 2),
                            "duration": round(pause_dur, 2),
                            "label": f"Pause ({round(pause_dur, 1)}s)",
                        }
                    )
                    total_pause_time += pause_dur
                    pauses_count += 1

                timeline_items.append(
                    {
                        "type": "speech",
                        "index": speech_idx,
                        "start": round(seg_start, 2),
                        "end": round(seg_end, 2),
                        "duration": round(seg_dur, 2),
                        "text": seg_text,
                        "word_count": words_in_seg,
                        "wpm": seg_wpm,
                    }
                )
                speech_idx += 1
                last_speech_end = seg_end

            else:
                timeline_items.append(
                    {
                        "type": itype,
                        "start": round(data["time"], 2),
                        "end": round(data["time"], 2),
                        "duration": round(data.get("duration", 0.0), 2),
                        "label": data["label"],
                    }
                )

        def _sort_key(item):
            itype = item.get("type", "")
            if itype in ("phone_timer_start", "phone_timer_alarm"):
                prio = 1
            elif itype == "pause":
                prio = 2
            else:
                prio = 3
            return (item["start"], prio)

        timeline_items.sort(key=_sort_key)

        last_speech_time = last_speech_end
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

    def _integrate_events_into_segments(self, segments, events):
        """Splits speech segments at event boundaries and inserts events in chronological order."""
        if not events:
            return [(dict(s), "speech") for s in segments]

        sorted_events = sorted(events, key=lambda x: x["time"])
        current_items = [(dict(s), "speech") for s in segments]

        for ev in sorted_events:
            ev_time = ev["time"]
            new_items = []
            inserted = False

            for item_data, item_type in current_items:
                if inserted or item_type != "speech":
                    new_items.append((item_data, item_type))
                    continue

                seg_start = item_data["start"]
                seg_end = item_data["end"]

                if ev_time < seg_start:
                    new_items.append((ev, ev["type"]))
                    new_items.append((item_data, item_type))
                    inserted = True
                elif seg_start <= ev_time <= seg_end:
                    words = item_data.get("words", [])
                    if words:
                        words_before = [
                            w
                            for w in words
                            if w["end"] <= ev_time
                            or (
                                w["start"] < ev_time
                                and (ev_time - w["start"] >= w["end"] - ev_time)
                            )
                        ]
                        words_after = [w for w in words if w not in words_before]
                    else:
                        text_parts = item_data.get("text", "").split()
                        dur = max(0.01, seg_end - seg_start)
                        ratio = max(0.0, min(1.0, (ev_time - seg_start) / dur))
                        cut = int(len(text_parts) * ratio)
                        if 0 < cut < len(text_parts):
                            words_before = text_parts[:cut]
                            words_after = text_parts[cut:]
                        else:
                            words_before = []
                            words_after = []

                    if words and words_before and words_after:
                        part1 = {
                            "start": seg_start,
                            "end": words_before[-1]["end"],
                            "text": " ".join(w["word"].strip() for w in words_before),
                            "words": words_before,
                        }
                        part2 = {
                            "start": words_after[0]["start"],
                            "end": seg_end,
                            "text": " ".join(w["word"].strip() for w in words_after),
                            "words": words_after,
                        }
                        new_items.append((part1, "speech"))
                        new_items.append((ev, ev["type"]))
                        new_items.append((part2, "speech"))
                        inserted = True
                    elif not words and words_before and words_after:
                        mid = round(ev_time, 2)
                        part1 = {
                            "start": seg_start,
                            "end": mid,
                            "text": " ".join(words_before),
                        }
                        part2 = {
                            "start": mid,
                            "end": seg_end,
                            "text": " ".join(words_after),
                        }
                        new_items.append((part1, "speech"))
                        new_items.append((ev, ev["type"]))
                        new_items.append((part2, "speech"))
                        inserted = True
                    else:
                        # Event is right at boundary
                        if ev_time - seg_start <= seg_end - ev_time:
                            new_items.append((ev, ev["type"]))
                            new_items.append((item_data, item_type))
                        else:
                            new_items.append((item_data, item_type))
                            new_items.append((ev, ev["type"]))
                        inserted = True
                else:
                    new_items.append((item_data, item_type))

            if not inserted:
                new_items.append((ev, ev["type"]))

            current_items = new_items

        return current_items
