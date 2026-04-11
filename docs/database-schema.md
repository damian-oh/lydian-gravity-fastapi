# Database Schema

SQLite database with 5 tables. Auto-created on first run via `Base.metadata.create_all()`.

## Relationships

```
users (1) ──→ (many) song_sketches (1) ──→ (many) song_sections (1) ──→ (many) chords
                                                                   └──→ (many) melodic_notes
```

All foreign keys use `ON DELETE CASCADE`.

---

## `users`

User authentication.

| Column          | Type        | Constraints              | Description                         |
|-----------------|-------------|--------------------------|-------------------------------------|
| `id`            | Integer     | PK, autoincrement        | Primary key                         |
| `email`         | String(255) | UNIQUE, NOT NULL         | Login email                         |
| `password_hash` | String(255) | NOT NULL                 | Hashed password (never store plain) |
| `created_at`    | DateTime    | server_default `now()`   | Account creation time               |

---

## `song_sketches`

Song metadata. Theory-derived data (scales, tonal gravity, chord suggestions) is not stored — it is computed on demand via `/api/theory/*` endpoints.

| Column                | Type        | Constraints                          | Description                            |
|-----------------------|-------------|--------------------------------------|----------------------------------------|
| `id`                  | Integer     | PK, autoincrement                    | Primary key                            |
| `user_id`             | Integer     | FK → `users.id`, ON DELETE CASCADE   | Owner                                  |
| `title`               | String(200) | NOT NULL                             | Song title                             |
| `master_tonal_center` | String(10)  | NOT NULL                             | Root note (e.g. `"C"`, `"F#"`, `"Bb"`) |
| `master_mode`         | String(20)  | NOT NULL                             | Mode name (e.g. `"lydian"`, `"dorian"`)|
| `tempo_bpm`           | Integer     | NOT NULL                             | Beats per minute                       |
| `time_signature`      | String(10)  | NOT NULL, default `"4/4"`            | Time signature (e.g. `"4/4"`, `"6/8"`) |
| `notes`               | Text        | nullable                             | Free-form user notes / lyrics          |
| `created_at`          | DateTime    | server_default `now()`               | Auto-set on create                     |
| `updated_at`          | DateTime    | server_default `now()`, onupdate     | Auto-set on create and update          |

---

## `song_sections`

Song structure with a fixed section type and an optional custom label.

| Column           | Type        | Constraints                                  | Description                                                                       |
|------------------|-------------|----------------------------------------------|-----------------------------------------------------------------------------------|
| `id`             | Integer     | PK, autoincrement                            | Primary key                                                                       |
| `song_sketch_id` | Integer     | FK → `song_sketches.id`, ON DELETE CASCADE   | Parent song                                                                       |
| `section_type`   | String(1)   | NOT NULL                                     | `"A"` (Verse), `"B"` (Pre-Chorus/Bridge), `"C"` (Chorus), `"D"` (Primary-Bridge) |
| `label`          | String(50)  | nullable                                     | Custom display name (e.g. `"Verse 2"`, `"Final Chorus"`)                          |
| `order_index`    | Integer     | NOT NULL                                     | Sequential playback order within the song                                         |

### Section type reference

| Type | Meaning              |
|------|----------------------|
| `A`  | Verse                |
| `B`  | Pre-Chorus / Bridge  |
| `C`  | Chorus               |
| `D`  | Primary-Bridge       |

### Example rows

| id | song_sketch_id | section_type | label         | order_index |
|----|----------------|--------------|---------------|-------------|
| 1  | 1              | A            | Verse 1       | 0           |
| 2  | 1              | B            | Pre-Chorus    | 1           |
| 3  | 1              | C            | Chorus        | 2           |
| 4  | 1              | A            | Verse 2       | 3           |
| 5  | 1              | D            | Bridge        | 4           |
| 6  | 1              | C            | Final Chorus  | 5           |

---

## `chords`

Individual chords placed by the user in each section. Contains both decomposed fields (for the engine) and a display name (for extended chord notation like `"Cmaj7(#11)"`).

| Column           | Type        | Constraints                                | Description                                          |
|------------------|-------------|--------------------------------------------|------------------------------------------------------|
| `id`             | Integer     | PK, autoincrement                          | Primary key                                          |
| `section_id`     | Integer     | FK → `song_sections.id`, ON DELETE CASCADE | Parent section                                       |
| `order_index`    | Integer     | NOT NULL                                   | Sequence within the section (for UI sorting)         |
| `root`           | String(10)  | NOT NULL                                   | Root note (e.g. `"C"`, `"Bb"`)                       |
| `quality`        | String(10)  | NOT NULL                                   | Chord quality (e.g. `"maj"`, `"min7"`, `"dim"`)      |
| `chord_name`     | String(30)  | NOT NULL                                   | Full display name (e.g. `"Cmaj7(#11)"`, `"Am"`)      |
| `notes`          | Text        | NOT NULL                                   | JSON array of note names (e.g. `["C","E","G"]`)      |
| `start_beat`     | Float       | NOT NULL                                   | Beat position where the chord begins within the section |
| `duration_beats` | Float       | NOT NULL                                   | Duration in beats (e.g. `4.0` for whole note in 4/4) |
| `parent_mode`    | String(20)  | NOT NULL                                   | Mode this chord belongs to (for engine scale logic)  |

### Modal interchange detection

If a chord's `parent_mode` differs from the song's `master_mode`, the chord is borrowed via modal interchange. No separate flag is needed — the relationship is derived by comparing the two values.

**Example:** A song in C Lydian with an F major chord whose `parent_mode` is `"ionian"` → this chord is borrowed from the parallel Ionian mode (modal interchange).

### Example rows (song in C Lydian, Verse 1 section)

| id | section_id | order_index | root | quality | chord_name | notes              | start_beat | duration_beats | parent_mode |
|----|------------|-------------|------|---------|------------|--------------------|------------|----------------|-------------|
| 1  | 1          | 0           | C    | maj     | C          | `["C","E","G"]`    | 0.0        | 4.0            | lydian      |
| 2  | 1          | 1           | D    | maj     | D          | `["D","F#","A"]`   | 4.0        | 4.0            | lydian      |
| 3  | 1          | 2           | F    | maj     | F          | `["F","A","C"]`    | 8.0        | 4.0            | ionian      |
| 4  | 1          | 3           | G    | maj     | G          | `["G","B","D"]`    | 12.0       | 4.0            | lydian      |

---

## `melodic_notes`

Individual melody notes within a section. Supports the guided melody sketch feature. Pitch is stored as a MIDI note number (integer) for easy transposition math — display formatting to scientific notation (e.g. "C4") is done on the frontend.

| Column           | Type        | Constraints                                | Description                                            |
|------------------|-------------|--------------------------------------------|--------------------------------------------------------|
| `id`             | Integer     | PK, autoincrement                          | Primary key                                            |
| `section_id`     | Integer     | FK → `song_sections.id`, ON DELETE CASCADE | Parent section                                         |
| `pitch`          | Integer     | NOT NULL                                   | MIDI note number (e.g. `60` = C4, `67` = G4)           |
| `start_beat`     | Float       | NOT NULL                                   | Beat position where the note begins within the section |
| `duration_beats` | Float       | NOT NULL                                   | How long the note is held                              |

### MIDI note reference

| MIDI | Note |
|------|------|
| 48   | C3   |
| 60   | C4 (middle C) |
| 64   | E4   |
| 67   | G4   |
| 69   | A4 (440 Hz)   |
| 72   | C5   |

### Example rows (melody over Verse 1)

| id | section_id | pitch | start_beat | duration_beats |
|----|------------|-------|------------|----------------|
| 1  | 1          | 60    | 0.0        | 1.0            |
| 2  | 1          | 64    | 1.0        | 0.5            |
| 3  | 1          | 67    | 1.5        | 1.5            |
| 4  | 1          | 69    | 3.0        | 1.0            |

---

## Validation Rules

| Field                  | Rule                                                          |
|------------------------|---------------------------------------------------------------|
| `email`                | Valid email format, unique                                    |
| `master_tonal_center`  | Must be a valid note name in `ENHARMONIC_MAP` (notes.py)      |
| `master_mode`          | Must be a key in `MODE_INTERVALS` (scales.py)                 |
| `tempo_bpm`            | 20 ≤ value ≤ 300                                              |
| `time_signature`       | Must match pattern `"N/N"` (e.g. `"4/4"`, `"6/8"`)            |
| `section_type`         | Must be one of `"A"`, `"B"`, `"C"`, `"D"`                     |
| `order_index`          | Must be ≥ 0                                                   |
| `chord.root`           | Must be a valid note name in `ENHARMONIC_MAP`                 |
| `chord.quality`        | Must be a recognized value in `CHORD_QUALITIES` (chords.py)   |
| `start_beat`           | Must be ≥ 0                                                   |
| `duration_beats`       | Must be > 0                                                   |
| `pitch`                | Valid MIDI note number (0–127)                                |

## Cascade Behavior

| Action                 | Effect                                                    |
|------------------------|-----------------------------------------------------------|
| Delete a user          | Removes all their song sketches and all nested data       |
| Delete a song sketch   | Removes all sections, chords, and melodic notes           |
| Delete a section       | Removes all its chords and melodic notes                  |
