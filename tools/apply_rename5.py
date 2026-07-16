"""Description-review pass: fixes from a full human read of all 133
docstrings (requested review). Three classes:

1. Dangling references: the "Voynich Talk video" is Koen Gheuens'
   "The alphabet is smaller than you think" (YouTube channel Voynich
   Talk) — now attributed; a bogus future date on a forum ref dropped;
   leftover "/60"-style phase fragments expanded to real test names.
2. Session-relative language ("the previous agent", "the user asks",
   "USER OBSERVATION") reworded to stand alone for outside readers.
3. Old phase-numbered sub-test labels (57a, 38b...) -> plain letters.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = ROOT / 'scripts'

EDITS = {
 'abjad_hypothesis.py': [
  ('(b) Voynich Talk video: positional variant collapse → ~13 functional glyphs',
   "(b) Koen Gheuens' video \"The alphabet is smaller than you think\"\n      (YouTube, Voynich Talk): positional variant collapse → ~13 functional glyphs"),
  ("The Voynich Talk video's conclusion that \"13 is a disaster for European",
   "That video's conclusion that \"13 is a disaster for European"),
  ('THIS TEST TESTS: If we strip vowels', 'THE TEST: if we strip vowels')],
 'ae_minimal_pairs.py': [
  ('found the strongest section-level glyph pattern found anywhere in the suite.',
   'found the strongest section-level glyph pattern anywhere in the suite.')],
 'branching_entropy_segmentation.py': [
  ('Validate on a KNOWN verbose cipher (forward_process_models/60 model)',
   'Validate on a KNOWN verbose cipher (the forward_process_models /\n    positional_verbose_cipher model)')],
 'claims_correction_audit.py': [
  ('Redo of the four tasks the previous agent botched:',
   'Corrected redo of four earlier analyses whose first versions were flawed:')],
 'diacritic_audit.py': [
  ('Connected to: user observation of small marks above letters in f78r,',
   'Connected to: an observation of small marks above letters in f78r,')],
 'e_extension_morphology.py': [
  ('Petrasti (Voynich Ninja thread-5216, Aug 2026) observed',
   'Petrasti (Voynich Ninja thread-5216) observed')],
 'encoding_layer_sweep.py': [
  ('This is the\n      forward_process_models/60 mechanism that matched h_char.',
   'This is the mechanism from\n      forward_process_models / positional_verbose_cipher that matched h_char.'),
  ('forward_process_models-60 showed\n      this works on Italian',
   'forward_process_models and positional_verbose_cipher showed\n      this works on Italian'),
  ('VMS TARGET: same VMS_TARGET dict from german_genre_fingerprint/82.',
   'VMS TARGET: same VMS_TARGET dict as german_genre_fingerprint and\ncharm_incantation_fingerprint.')],
 'gallows_line_position_split.py': [
  ('DISCOVERY: User observation → quantitative confirmation.',
   "DISCOVERY: a reader's observation → quantitative confirmation.")],
 'hypothesis_discriminators.py': [
  ('(redo of 51d)', '(redo of a synthesis_stress_test sub-analysis)')],
 'latin_paragraph_initials.py': [
  ('CRITICAL INSIGHT (from user): The EVA transliteration labels',
   'CRITICAL INSIGHT: The EVA transliteration labels')],
 'line1_body_separation.py': [
  ('MOTIVATION (from Koen\'s "Alphabet is smaller than you think" video + our data):',
   'MOTIVATION (from Koen Gheuens\' video "The alphabet is smaller than\nyou think" — YouTube, Voynich Talk — plus our own data):'),
  ('gallows_positional_ecology/77b showed',
   'gallows_positional_ecology and gallows_line_position_split showed')],
 'mi_distance_curve.py': [
  ('Does our verbose cipher (forward_process_models/60 model) PRESERVE or DESTROY',
   'Does our verbose cipher (the forward_process_models /\n    positional_verbose_cipher model) PRESERVE or DESTROY')],
 'paragraph_framing.py': [
  ('USER OBSERVATION: Many paragraphs from f103r onwards',
   'OBSERVATION: many paragraphs from f103r onwards')],
 'paragraph_initial_analysis.py': [
  ('USER OBSERVATION: Many paragraphs seem to start with the same letter/glyph.',
   'OBSERVATION: many paragraphs seem to start with the same letter/glyph.')],
 'position_identity_decomposition.py': [
  ('  86 established LOOP chunks as functional characters',
   '  chunk_equivalence_classes established LOOP chunks as functional characters'),
  ('spectral_vowel_consonant/87R confirmed position dominates',
   'spectral_vowel_consonant and its revalidation confirmed position dominates')],
 'root_lexicon_self_audit.py': [
  ('hallucination and overfitting. The user (rightly) asks: are we',
   'hallucination and overfitting. The obvious skeptical question: are we')],
 'rtl_direction_test.py': [
  ('Connected to: Hebrew-like constructed morphology findings (4),',
   'Connected to: the Hebrew-like constructed morphology findings,'),
  ("and the user's observation that", 'and the observation that')],
 'sh_prefix_disentangle.py': [
  ('This test tests definitively whether', 'This test determines definitively whether')],
 'syntax_artifact_supplement.py': [
  ('FIX 1 (40b-fix): POSITION CONTROL\n  Original 40b assigned',
   'FIX 1: POSITION CONTROL\n  The original position-control test assigned'),
  ('FIX 2 (40a-fix): BOUNDARY CHARACTER OVER-CONTROL\n  Original 40a conditioned',
   'FIX 2: BOUNDARY CHARACTER OVER-CONTROL\n  The original boundary-character test conditioned')],
 'word_shape_validation.py': [
  ('THIS TEST TESTS WHETHER THE CIPHER PRODUCES VMS-LIKE WORD SHAPES.',
   'THE TEST: DOES THE CIPHER PRODUCE VMS-LIKE WORD SHAPES?')],
}

changed = set()
for fname, pairs in EDITS.items():
    p = S / fname
    text = p.read_text(encoding='utf-8', errors='replace')
    for old, new in pairs:
        if old not in text:
            print(f'MISS {fname}: {old[:60]!r}')
            continue
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')
    changed.add(p.stem)

# generic passes over every script
for p in sorted(S.glob('*.py')):
    text = p.read_text(encoding='utf-8', errors='replace')
    orig = text
    # residual "This test tests" awkwardness
    text = text.replace('This test tests:', 'This test covers:')
    text = text.replace('This test tests whether', 'This test examines whether')
    text = text.replace('This test tests EVERY', 'This test probes EVERY')
    # old phase-numbered sub-test labels: "57a)" -> "A)", '"56a:' -> '"A:'
    # (\b before the digits keeps folio ids like f72r3 safe)
    text = re.sub(r'\b\d{2,3}([a-z])\)', lambda m: m.group(1).upper() + ')', text)
    text = re.sub(r'(["\'])(\d{2,3})([a-z]):', lambda m: m.group(1) + m.group(3).upper() + ':', text)
    if text != orig:
        p.write_text(text, encoding='utf-8')
        changed.add(p.stem)

# union with the pass-4 refresh list -> single golden refresh
lst = ROOT / 'tools' / '_pass4_changed.txt'
union = set(lst.read_text(encoding='utf-8').split(',')) | changed
union.discard('')
lst.write_text(','.join(sorted(union)), encoding='utf-8')
print(f'pass 5 changed {len(changed)} scripts; union refresh list = {len(union)}')
