# Feature Definitions – AI Video Decision Engine

Ez a dokumentum tartalmazza az összes jelenleg implementált **feature-t** a projektben,
amelyeket a rendszer a segment-ek elemzésére használ.
Minden feature **raw, normalizálatlan**, és a DecisionEngine normalizálja, pontozza,
és platform-specifikusan értékeli.

---

## 1. Music Features (MusicAnalyzer)

| Feature | Definíció | Matematikai kifejezés | Megjegyzés |
|---------|-----------|----------------------|------------|
| `energy_peak` | RMS energia csúcs | `percentile(rms(audio), 95)` | Nagy amplitúdójú részek jelzése |
| `energy_change` | Dinamika | `abs(mean(rms[:20%]) - mean(rms[-20%]))` | Hangerő változás a szegmensben |
| `onset_density` | Ütemek / onset-ok sűrűsége | `len(detect_onsets(audio)) / duration` | Ritmus, tempó aktivitás |
| `harmonic_change` | Harmóniai változás | `variance(chroma(audio))` | Akkord, riff változatosság |
| `tempo` | BPM | `estimate_bpm(audio)` | Ritmus gyorsaság |

> Megjegyzés: minden feature raw érték, a normalizátor skálázza 0–1 közé.

---

## 2. Visual Features (VisualAnalyzer)

| Feature | Definíció | Matematikai kifejezés | Megjegyzés |
|---------|-----------|----------------------|------------|
| `hands_visible_ratio` | Hangszer és kéz láthatósága | `frames_with_hands / total_frames` | Fontos gitáros tartalomhoz |
| `face_visible_ratio` | Előadó felismerhetősége | `frames_with_face / total_frames` | Arckifejezés, emberi kapcsolat |
| `motion_intensity` | Vizuális dinamika | `mean(optical_flow(prev_frame, frame))` | Mozgás, energia |
| `framing_issue_ratio` | Levágott kéz/fej arány | `frames_with_cut / total_frames` | Hibás kompozíció jele |

---

## 3. Emotion Features (EmotionEstimator)

| Feature | Definíció | Matematikai kifejezés | Megjegyzés |
|---------|-----------|----------------------|------------|
| `build_up` | Fokozatos zenei építkezés | `max(slope(smooth(energy_curve)), 0)` | Climax előtti fokozódás |
| `climax_strength` | Csúcspont intenzitása | `max(energy_curve) - mean(energy_curve)` | Zenei tetőpont |
| `expressive_motion` | Zene + mozgás együtt | `motion_intensity * energy_change` | Vizualizált energia |
| `temporal_contrast` | Időbeli változatosság | `variance(energy_curve)` | Dinamika és variáció |

---

## 4. Platform Features (PlatformEvaluator)

| Feature | Definíció | Matematikai kifejezés | Megjegyzés |
|---------|-----------|----------------------|------------|
| `platform_score` | Összesített platform pont | `0.7*weighted_score + 0.2*hook_score + 0.1*loop_score` | Súlyozott összesített érték |
| `hook_score` | Első 2–4 másodperc figyelemfelkeltő ereje | `mean(energy_peak_first_sec[:hook_window])` | Platform-specifikus |
| `loop_score` | Loopability / replay potenciál | `0.5*motion_intensity + 0.5*energy_change` | Vizual + zenei integráció |
| `recommendations` | Ajánlások | pl. `"hook": "Consider stronger opening"` | Ha gyenge hook vagy platform score |

> Megjegyzés: Minden platformhoz (TikTok, Shorts, Reels) külön profil lehet a `config`-ban,
> ami meghatározza a súlyokat és hook window-t.

---

## 5. Összefüggések és pipeline

1. **Segment kiválasztás** – DecisionEngine
2. **Feature extraction** – MusicAnalyzer, VisualAnalyzer, EmotionEstimator
3. **Normalizálás** – Normalizer modul
4. **Score számítás** – ScoreCalculator modul
5. **Platform értékelés** – PlatformEvaluator
6. **Döntés + magyarázat** – DecisionEngine

> Ez biztosítja, hogy minden feature
> 1) tesztelhető,
> 2) platform-specifikus,
> 3) később ML-re cserélhető,
> 4) explainable legyen.

---

## 6. Megjegyzések a jövőre nézve

- Bővíthető új platformokkal (`Hook`, `Loop`, `Silent view`)
- Később ML modellek helyettesíthetik az analyzereket
- Feature értékek és threshold-ok a `config` fájlban paraméterezhetők
- Unit tesztek a Mock-olt komponensekkel már teljesen lefedik az összes feature-t

---

Ez a dokumentum **referenciaként is használható** minden fejlesztőnek és tesztelőnek, és közvetlenül mehet a **GitHub repo docs mappájába**.
