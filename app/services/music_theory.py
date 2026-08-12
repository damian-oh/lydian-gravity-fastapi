from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_MODES = (
    "lydian",
    "ionian",
    "dorian",
    "mixolydian",
    "aeolian",
    "phrygian",
    "locrian",
)

MODE_INTERVALS: dict[str, tuple[int, ...]] = {
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "ionian": (0, 2, 4, 5, 7, 9, 11),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "aeolian": (0, 2, 3, 5, 7, 8, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "locrian": (0, 1, 3, 5, 6, 8, 10),
}

NOTE_TO_SEMITONE: dict[str, int] = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "F": 5,
    "E#": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
}

CHORD_QUALITIES = {
    "maj",
    "maj7",
    "maj9",
    "min",
    "m",
    "min7",
    "m7",
    "7",
    "sus4",
    "add9",
    "dim",
    "min7b5",
}

SHARP_CHROMATIC = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
FLAT_CHROMATIC = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")

# Semitone offset from a mode's tonic down to its relative major (ionian) tonic:
# D dorian shares its key signature with C major, so dorian maps to 2, etc.
MODE_TONIC_OFFSETS: dict[str, int] = {
    "ionian": 0,
    "dorian": 2,
    "phrygian": 4,
    "lydian": 5,
    "mixolydian": 7,
    "aeolian": 9,
    "locrian": 11,
}

# Semitone classes of the flat-side major keys F, Bb, Eb, Ab, and Db.
FLAT_MAJOR_SEMITONES = {5, 10, 3, 8, 1}


@dataclass(frozen=True)
class BuiltChord:
    root: str
    root_offset: int
    quality: str
    chord_name: str
    notes: tuple[str, ...]
    roman_numeral: str
    degree_label: str


@dataclass(frozen=True)
class NextStepChord:
    id: str
    chord_name: str
    root: str
    quality: str
    notes: tuple[str, ...]
    parent_mode: str
    reason: str
    tension: str


def is_valid_note(note: str) -> bool:
    return note in NOTE_TO_SEMITONE


def is_valid_mode(mode: str) -> bool:
    return mode in MODE_INTERVALS


def is_valid_chord_quality(quality: str) -> bool:
    return quality in CHORD_QUALITIES


def normalize_semitone(value: int) -> int:
    return value % 12


def get_preferred_chromatic(tonal_center: str, mode: str = "ionian") -> tuple[str, ...]:
    # The sharp/flat side of a key is a property of the key signature, which
    # depends on tonic AND mode: C dorian carries the two flats of Bb major.
    # Limitation: the 12-name tables cannot spell E#/B#/Cb/Fb or double
    # accidentals, so remote keys get single-accidental respellings. This is
    # deliberate -- chord validators and the audio transport only accept these
    # 21 note names. Must stay in lockstep with chord-catalog.ts.
    if "b" in tonal_center:
        return FLAT_CHROMATIC
    if "#" in tonal_center:
        return SHARP_CHROMATIC

    relative_major = normalize_semitone(
        NOTE_TO_SEMITONE.get(tonal_center, 0) - MODE_TONIC_OFFSETS.get(mode, 0)
    )

    return FLAT_CHROMATIC if relative_major in FLAT_MAJOR_SEMITONES else SHARP_CHROMATIC


def get_note_at_interval(
    tonal_center: str,
    semitone_offset: int,
    chromatic: tuple[str, ...] | None = None,
) -> str:
    if chromatic is None:
        chromatic = get_preferred_chromatic(tonal_center)
    base_semitone = NOTE_TO_SEMITONE.get(tonal_center, 0)

    return chromatic[normalize_semitone(base_semitone + semitone_offset)]


def build_pitch_collection(tonal_center: str, mode: str) -> list[str]:
    intervals = MODE_INTERVALS.get(mode, MODE_INTERVALS["ionian"])
    chromatic = get_preferred_chromatic(tonal_center, mode)

    return [
        get_note_at_interval(tonal_center, interval, chromatic)
        for interval in intervals
    ]


def get_stack_interval(scale: tuple[int, ...], degree_index: int, step: int) -> int:
    next_index = degree_index + step
    wrapped_index = next_index % len(scale)
    octave_shift = 12 if next_index >= len(scale) else 0

    return scale[wrapped_index] - scale[degree_index] + octave_shift


def get_seventh_quality(intervals: tuple[int, int, int]) -> str:
    third, fifth, seventh = intervals

    if third == 4 and fifth == 7 and seventh == 11:
        return "maj7"
    if third == 4 and fifth == 7 and seventh == 10:
        return "7"
    if third == 3 and fifth == 7 and seventh == 10:
        return "min7"

    return "min7b5"


def build_chord_notes(
    root: str,
    quality: str,
    chromatic: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    quality_intervals: dict[str, tuple[int, ...]] = {
        "maj": (0, 4, 7),
        "maj7": (0, 4, 7, 11),
        "maj9": (0, 4, 7, 11, 14),
        "min": (0, 3, 7),
        "m": (0, 3, 7),
        "min7": (0, 3, 7, 10),
        "m7": (0, 3, 7, 10),
        "7": (0, 4, 7, 10),
        "sus4": (0, 5, 7),
        "add9": (0, 4, 7, 14),
        "dim": (0, 3, 6),
        "min7b5": (0, 3, 6, 10),
    }

    return tuple(
        get_note_at_interval(root, interval, chromatic)
        for interval in quality_intervals.get(quality, (0, 4, 7))
    )


def format_mode_label(mode: str) -> str:
    return f"{mode[:1].upper()}{mode[1:]}"


def quality_suffix(quality: str) -> str:
    return {
        "maj": "",
        "maj7": "maj7",
        "maj9": "maj9",
        "min": "m",
        "m": "m",
        "min7": "m7",
        "m7": "m7",
        "7": "7",
        "sus4": "sus4",
        "add9": "add9",
        "dim": "dim",
        "min7b5": "m7b5",
    }.get(quality, quality)


def scale_degree_label(root_offset: int, mode: str = "ionian") -> str:
    if root_offset == 6:
        # Offset 6 is diatonic only in lydian (#IV) and locrian, where it is
        # the mode's own diminished fifth, not a raised fourth.
        return "bV" if mode == "locrian" else "#IV"

    return {
        0: "I",
        1: "bII",
        2: "II",
        3: "bIII",
        4: "III",
        5: "IV",
        7: "V",
        8: "bVI",
        9: "VI",
        10: "bVII",
        11: "VII",
    }.get(root_offset, "I")


def build_roman_numeral(root_offset: int, quality: str, mode: str = "ionian") -> str:
    base = scale_degree_label(root_offset, mode)
    suffix = {
        "maj7": "maj7",
        "7": "7",
        "min7": "7",
        "min7b5": "ø7",
    }.get(quality, "")

    return (
        f"{base.lower()}{suffix}"
        if quality in {"min7", "min7b5"}
        else f"{base}{suffix}"
    )


def build_mode_seventh_chords(tonal_center: str, mode: str) -> list[BuiltChord]:
    scale = MODE_INTERVALS.get(mode, MODE_INTERVALS["ionian"])
    chromatic = get_preferred_chromatic(tonal_center, mode)
    chords: list[BuiltChord] = []

    for degree_index, root_offset in enumerate(scale):
        intervals = (
            get_stack_interval(scale, degree_index, 2),
            get_stack_interval(scale, degree_index, 4),
            get_stack_interval(scale, degree_index, 6),
        )
        quality = get_seventh_quality(intervals)
        root = get_note_at_interval(tonal_center, root_offset, chromatic)
        chords.append(
            BuiltChord(
                root=root,
                root_offset=root_offset,
                quality=quality,
                chord_name=f"{root}{quality_suffix(quality)}",
                notes=build_chord_notes(root, quality, chromatic),
                roman_numeral=build_roman_numeral(root_offset, quality, mode),
                degree_label=scale_degree_label(root_offset, mode),
            )
        )

    return chords


def build_secondary_dominant(
    target_chord: BuiltChord,
    tonal_center: str,
    chromatic: tuple[str, ...] | None = None,
) -> BuiltChord:
    root = get_note_at_interval(target_chord.root, 7, chromatic)

    return BuiltChord(
        root=root,
        root_offset=normalize_semitone(
            NOTE_TO_SEMITONE[root] - NOTE_TO_SEMITONE[tonal_center]
        ),
        quality="7",
        chord_name=f"{root}7",
        notes=build_chord_notes(root, "7", chromatic),
        roman_numeral=f"V/{target_chord.degree_label}",
        degree_label=target_chord.degree_label,
    )


def get_chord_signature(chord: BuiltChord) -> str:
    return f"{chord.root}|{chord.quality}"


def generate_next_step_suggestions(
    tonal_center: str,
    mode: str,
    chords: list[dict],
    selected_chord_id: int | None = None,
) -> dict[str, object]:
    pitch_collection = build_pitch_collection(tonal_center, mode)
    chromatic = get_preferred_chromatic(tonal_center, mode)
    diatonic_chords = build_mode_seventh_chords(tonal_center, mode)
    active_chord = None
    if selected_chord_id is not None:
        active_chord = next(
            (chord for chord in chords if chord.get("id") == selected_chord_id),
            None,
        )
    if active_chord is None and chords:
        # No explicit selection: anchor on the musically last chord, not on
        # whatever order the client happened to send the array in.
        active_chord = max(
            chords,
            key=lambda chord: (
                chord.get("start_beat", 0.0),
                chord.get("order_index", 0),
            ),
        )
    active_root = active_chord.get("root") if active_chord else None
    # Match by semitone rather than name so chords persisted with the other
    # enharmonic spelling (e.g. a stored "D#" against a diatonic "Eb") still
    # anchor on the right degree. An empty section leaves active_index at -1,
    # which deterministically suggests the tonic chord below.
    active_semitone = NOTE_TO_SEMITONE.get(active_root) if active_root else None
    active_index = next(
        (
            index
            for index, chord in enumerate(diatonic_chords)
            if NOTE_TO_SEMITONE[chord.root] == active_semitone
        ),
        -1,
    )
    next_diatonic = diatonic_chords[(active_index + 1) % len(diatonic_chords)]
    target_for_dominant = diatonic_chords[(active_index + 2) % len(diatonic_chords)]
    secondary = build_secondary_dominant(target_for_dominant, tonal_center, chromatic)
    diatonic_signatures = {get_chord_signature(chord) for chord in diatonic_chords}
    borrowed_source_mode = "ionian" if mode != "ionian" else "dorian"
    borrowed_chord = next(
        (
            chord
            for chord in build_mode_seventh_chords(tonal_center, borrowed_source_mode)
            if get_chord_signature(chord) not in diatonic_signatures
        ),
        build_mode_seventh_chords(tonal_center, borrowed_source_mode)[0],
    )

    suggestions = [
        NextStepChord(
            id="next-diatonic",
            chord_name=next_diatonic.chord_name,
            root=next_diatonic.root,
            quality=next_diatonic.quality,
            notes=next_diatonic.notes,
            parent_mode=mode,
            reason=(
                f"Continue inside {tonal_center} {format_mode_label(mode)} with "
                f"{next_diatonic.roman_numeral} for a stable next bar."
            ),
            tension="grounded",
        ),
        NextStepChord(
            id="secondary-dominant",
            chord_name=secondary.chord_name,
            root=secondary.root,
            quality=secondary.quality,
            notes=secondary.notes,
            parent_mode="secondary dominant",
            reason=(
                f"Use {secondary.roman_numeral} to point at {target_for_dominant.chord_name} "
                "before returning to the modal field."
            ),
            tension="release",
        ),
        NextStepChord(
            id="modal-interchange",
            chord_name=borrowed_chord.chord_name,
            root=borrowed_chord.root,
            quality=borrowed_chord.quality,
            notes=borrowed_chord.notes,
            parent_mode=borrowed_source_mode,
            reason=(
                f"Borrow from parallel {format_mode_label(borrowed_source_mode)} "
                "for contrast without changing tonal center."
            ),
            tension="borrowed",
        ),
    ]

    return {
        "pitch_collection": pitch_collection,
        "gravity_center": [
            tonal_center,
            get_note_at_interval(tonal_center, 7),
            get_note_at_interval(tonal_center, 2),
        ],
        "suggested_chords": [
            {
                "id": suggestion.id,
                "chord_name": suggestion.chord_name,
                "root": suggestion.root,
                "quality": suggestion.quality,
                "notes": list(suggestion.notes),
                "parent_mode": suggestion.parent_mode,
                "reason": suggestion.reason,
                "tension": suggestion.tension,
            }
            for suggestion in suggestions
        ],
        "melody_prompt": (
            f"Lean on {pitch_collection[2]} or {pitch_collection[6]} for color, then resolve toward "
            f"{tonal_center} when the phrase needs rest."
        ),
        "rhythmic_prompt": "Try one sustained note across the bar line, then answer with shorter motion on the next chord.",
        "interchange_insight": (
            f"A borrowed {borrowed_chord.chord_name} reads as parallel {format_mode_label(borrowed_source_mode)} "
            f"against the {tonal_center} {format_mode_label(mode)} center."
        ),
    }
