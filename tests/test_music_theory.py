import json
from pathlib import Path

import pytest

from app.services import music_theory as mt

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "theory_parity.json"


class TestPreferredChromatic:
    @pytest.mark.parametrize(
        ("tonic", "mode", "expected"),
        [
            ("C", "ionian", mt.SHARP_CHROMATIC),
            ("C", "lydian", mt.SHARP_CHROMATIC),
            ("C", "dorian", mt.FLAT_CHROMATIC),
            ("C", "aeolian", mt.FLAT_CHROMATIC),
            ("C", "phrygian", mt.FLAT_CHROMATIC),
            ("C", "locrian", mt.FLAT_CHROMATIC),
            ("D", "phrygian", mt.FLAT_CHROMATIC),
            ("D", "ionian", mt.SHARP_CHROMATIC),
            ("A", "locrian", mt.FLAT_CHROMATIC),
            ("E", "phrygian", mt.SHARP_CHROMATIC),
            ("B", "lydian", mt.SHARP_CHROMATIC),
            # Tonic spelling wins outright.
            ("F#", "dorian", mt.SHARP_CHROMATIC),
            ("Gb", "lydian", mt.FLAT_CHROMATIC),
            ("Bb", "ionian", mt.FLAT_CHROMATIC),
        ],
    )
    def test_choice_depends_on_tonic_and_mode(self, tonic, mode, expected):
        assert mt.get_preferred_chromatic(tonic, mode) is expected


class TestPitchCollection:
    def test_c_dorian_spelled_with_flats(self):
        assert mt.build_pitch_collection("C", "dorian") == [
            "C", "D", "Eb", "F", "G", "A", "Bb",
        ]

    def test_c_aeolian_spelled_with_flats(self):
        assert mt.build_pitch_collection("C", "aeolian") == [
            "C", "D", "Eb", "F", "G", "Ab", "Bb",
        ]

    def test_c_lydian_keeps_sharp_fourth(self):
        assert mt.build_pitch_collection("C", "lydian") == [
            "C", "D", "E", "F#", "G", "A", "B",
        ]

    def test_no_duplicate_semitones(self):
        for tonic in ("C", "G", "D", "F", "Bb", "F#", "E"):
            for mode in mt.SUPPORTED_MODES:
                collection = mt.build_pitch_collection(tonic, mode)
                semitones = [mt.NOTE_TO_SEMITONE[n] for n in collection]
                assert len(set(semitones)) == 7


class TestModeSeventhChords:
    def test_c_dorian_chord_names_use_flats(self):
        names = [c.chord_name for c in mt.build_mode_seventh_chords("C", "dorian")]
        assert names == ["Cm7", "Dm7", "Ebmaj7", "F7", "Gm7", "Am7b5", "Bbmaj7"]

    def test_chord_notes_use_the_tonal_center_chromatic(self):
        # Db lydian is flat-side; the min7b5 on its #IV must not flip to sharps.
        chords = mt.build_mode_seventh_chords("Db", "lydian")
        half_dim = next(c for c in chords if c.quality == "min7b5")
        assert half_dim.notes == ("G", "Bb", "Db", "F")

    def test_locrian_offset_six_labeled_flat_five(self):
        chords = mt.build_mode_seventh_chords("C", "locrian")
        labels = [c.degree_label for c in chords]
        assert labels == ["I", "bII", "bIII", "IV", "bV", "bVI", "bVII"]

    def test_lydian_offset_six_keeps_sharp_four(self):
        chords = mt.build_mode_seventh_chords("C", "lydian")
        assert chords[3].degree_label == "#IV"


class TestSecondaryDominant:
    def test_spelled_from_tonal_center_chromatic(self):
        chromatic = mt.get_preferred_chromatic("C", "dorian")
        diatonic = mt.build_mode_seventh_chords("C", "dorian")
        # V of bIII (Ebmaj7) has root Bb, not A#.
        secondary = mt.build_secondary_dominant(diatonic[2], "C", chromatic)
        assert secondary.chord_name == "Bb7"
        assert secondary.roman_numeral == "V/bIII"


class TestSuggestionAnchor:
    def _chord(self, chord_id, root, start_beat, order_index):
        return {
            "id": chord_id,
            "root": root,
            "quality": "maj7",
            "start_beat": start_beat,
            "order_index": order_index,
        }

    def test_selected_chord_id_wins(self):
        chords = [
            self._chord(1, "C", 0.0, 0),
            self._chord(2, "D", 4.0, 1),
            self._chord(3, "E", 8.0, 2),
        ]
        result = mt.generate_next_step_suggestions(
            "C", "ionian", chords, selected_chord_id=1
        )
        next_diatonic = result["suggested_chords"][0]
        # Anchored on C (degree I), so next is the II chord.
        assert next_diatonic["chord_name"] == "Dm7"

    def test_without_selection_musically_last_chord_wins(self):
        # Sent out of order: the chord at beat 8 is the anchor, not the array tail.
        chords = [
            self._chord(3, "E", 8.0, 2),
            self._chord(1, "C", 0.0, 0),
            self._chord(2, "D", 4.0, 1),
        ]
        result = mt.generate_next_step_suggestions("C", "ionian", chords)
        next_diatonic = result["suggested_chords"][0]
        # Anchored on E (degree III), so next is the IV chord.
        assert next_diatonic["chord_name"] == "Fmaj7"

    def test_enharmonic_root_still_anchors(self):
        # A chord stored with the old sharp spelling anchors onto the new
        # flat-spelled diatonic degree.
        chords = [self._chord(1, "D#", 0.0, 0)]
        result = mt.generate_next_step_suggestions("C", "dorian", chords)
        next_diatonic = result["suggested_chords"][0]
        # Eb is degree bIII of C dorian; next is IV.
        assert next_diatonic["chord_name"] == "F7"

    def test_empty_section_suggests_the_tonic(self):
        result = mt.generate_next_step_suggestions("C", "lydian", [])
        next_diatonic = result["suggested_chords"][0]
        assert next_diatonic["chord_name"] == "Cmaj7"

    def test_secondary_dominant_never_targets_the_tonic(self):
        diatonic = mt.build_mode_seventh_chords("C", "ionian")
        for chord in diatonic:
            result = mt.generate_next_step_suggestions(
                "C",
                "ionian",
                [self._chord(1, chord.root, 0.0, 0)],
            )
            secondary = result["suggested_chords"][1]
            assert secondary["id"] == "secondary-dominant"
            # V/I is the plain diatonic V; the target must never be the tonic.
            assert "point at Cmaj7" not in secondary["reason"]


class TestGravityCenter:
    def test_notes_stay_inside_the_mode(self):
        for tonic in ("C", "G", "F", "Bb", "E"):
            for mode in mt.SUPPORTED_MODES:
                result = mt.generate_next_step_suggestions(tonic, mode, [])
                collection = result["pitch_collection"]
                assert set(result["gravity_center"]) <= set(collection)

    def test_rare_tonic_spelling_is_normalized(self):
        result = mt.generate_next_step_suggestions("Cb", "ionian", [])
        assert result["gravity_center"][0] == result["pitch_collection"][0] == "B"


class TestMelodyPrompt:
    def test_lydian_prompt_names_the_sharp_fourth(self):
        result = mt.generate_next_step_suggestions("C", "lydian", [])
        assert "F#" in result["melody_prompt"]

    def test_phrygian_prompt_names_the_flat_second(self):
        result = mt.generate_next_step_suggestions("C", "phrygian", [])
        assert "Db" in result["melody_prompt"]


class TestParityFixture:
    def test_backend_matches_golden_fixture(self):
        fixture = json.loads(FIXTURE_PATH.read_text())
        assert len(fixture) == 63

        for key, expected in fixture.items():
            tonic, mode = key.split("|")
            chromatic = mt.get_preferred_chromatic(tonic, mode)
            assert mt.build_pitch_collection(tonic, mode) == expected["pitch_collection"]

            diatonic = mt.build_mode_seventh_chords(tonic, mode)
            actual_diatonic = [
                {
                    "chord_name": c.chord_name,
                    "root": c.root,
                    "quality": c.quality,
                    "notes": list(c.notes),
                    "roman_numeral": c.roman_numeral,
                    "degree_label": c.degree_label,
                }
                for c in diatonic
            ]
            assert actual_diatonic == expected["diatonic"], key

            actual_secondary = [
                {
                    "chord_name": sd.chord_name,
                    "root": sd.root,
                    "notes": list(sd.notes),
                    "target_degree_label": target.degree_label,
                }
                for target in diatonic[1:]
                for sd in [mt.build_secondary_dominant(target, tonic, chromatic)]
            ]
            assert actual_secondary == expected["secondary_dominants"], key
