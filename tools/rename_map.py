"""Single source of truth for the test-rename refactor (2026-07-16).

Maps old script stem -> new script stem. Scripts absent from the map keep
their name (they were already clearly named); every script still gets its
"PHASE ..." headers and docstring title cleaned.

Used by tools/apply_rename.py; RENAME_MAP.md is generated from this dict.
"""

RENAME = {
    # -- formerly unclear non-phase names --------------------------------
    'attack_plan':                       'morphology_full_survey',
    'deep_dive':                         'root_type_grammar',
    'deep_dive_phase1':                  'root_type_stress_test',
    'four_tasks_audit':                  'claims_correction_audit',
    'leo_deepdive':                      'leo_sign_analysis',
    'crosssign_network':                 'zodiac_label_network',
    'currier_ab':                        'currier_register_comparison',
    'grammar_extraction':                'ring_grammar_extraction',
    'innermost_ring_dive':               'inner_ring_inventory',
    'medieval_degrees':                  'zodiac_degree_semantics',
    'pharma_comparison':                 'historical_pharma_comparison',
    'shorthand_analysis':                'pharma_shorthand_hypothesis',
    'coptic_probe_expanded':             'coptic_dictionary_probe',

    # -- phase19-31: zodiac + root-lexicon program -----------------------
    'phase19_zodiac_alignment':          'zodiac_ring_alignment',
    'phase20_template_subtraction':      'template_subtraction',
    'phase21_highest_leverage':          'zodiac_element_vocabulary',
    'phase22_unknown_roots':             'high_frequency_root_profiles',
    'phase23_full_translation':          'root_lexicon_translation',
    'phase24_classifier_semantics':      'gallows_classifier_semantics',
    'phase25_narrative_translation':     'narrative_reconstruction',
    'phase26_expansion':                 'root_lexicon_expansion',
    'phase27_self_audit':                'root_lexicon_self_audit',
    'phase28_statistical':               'root_significance_tests',
    'phase29_compounds':                 'compound_decomposition',
    'phase30_validation':                'compound_model_validation',
    'phase31_prefix_paradox':            'derivational_prefix_paradox',

    # -- phase32-38: morphology model audits -----------------------------
    'phase32_artifact_test':             'suffix_split_artifact_test',
    'phase33_cascade_audit':             'suffix_bug_cascade_audit',
    'phase34_model_audit':               'morphology_model_audit',
    'phase35_prefix_disentangle':        'sh_prefix_disentangle',
    'phase36_parser_free':               'morphology_artifact_test',
    'phase37_parser_free_analysis':      'parser_free_morphology',
    'phase38_bigram_null':               'bigram_null_stress_test',

    # -- phase39-51: syntax and synthesis --------------------------------
    'phase39_syntax':                    'word_order_syntax_test',
    'phase40_syntax_attack':             'syntax_artifact_attack',
    'phase40_supplement':                'syntax_artifact_supplement',
    'phase41_grammar':                   'syntactic_grammar_map',
    'phase42_class_system':              'two_class_section_grammar',
    'phase43_attack_classes':            'word_class_robustness',
    'phase44_word_classes':              'parser_free_word_classes',
    'phase45_word_predictability':       'word_predictability_decomposition',
    'phase46_mi_anatomy':                'mutual_information_anatomy',
    'phase47_word_network':              'word_transition_network',
    'phase48_cross_validation':          'structure_cross_validation',
    'phase49_generalization':            'line_boundary_generalization',
    'phase50_synthesis':                 'evidence_synthesis',
    'phase51_attack_synthesis':          'synthesis_stress_test',

    # -- phase52-60: hypothesis discrimination ---------------------------
    'phase52_discriminators':            'hypothesis_discriminators',
    'phase53_cipher_tests':              'cipher_identification_tests',
    'phase54_natlang_vs_cipher':         'language_vs_cipher',
    'phase55_vc_separation':             'vowel_consonant_separation',
    'phase56_syllabary_test':            'syllabary_hypothesis',
    'phase57_bax_test':                  'bax_decipherment_test',
    'phase58_cross_script':              'cross_script_fingerprint',
    'phase59_forward_model':             'forward_process_models',
    'phase60_positional_verbose':        'positional_verbose_cipher',

    # -- phase61-68: word anatomy + script re-analysis -------------------
    'phase61_word_shape_validation':     'word_shape_validation',
    'phase62_word_anatomy':              'word_functional_anatomy',
    'phase63_codicological_coherence':   'misbinding_coherence_test',
    'phase64_encoding_tournament':       'encoding_model_tournament',
    'phase65_reverse_engineer_script':   'script_reverse_engineering',
    'phase66_glyph_resegmentation':      'glyph_resegmentation',
    'phase67_run_length_morphology':     'run_length_morphology',
    'phase68_run_conditioned_transitions': 'run_conditioned_transitions',

    # -- phase71-82: paragraph/line structure + fingerprints -------------
    'phase71_paragraph_initials':        'paragraph_initial_analysis',
    'phase72_naibbe_calibration':        'naibbe_cipher_calibration',
    'phase73_abbreviation_model':        'abbreviation_shorthand_model',
    'phase74_paragraph_framing':         'paragraph_framing',
    'phase75_latin_mapping':             'latin_paragraph_initials',
    'phase76_vernacular_mapping':        'vernacular_paragraph_initials',
    'phase77_gallows_ecology':           'gallows_positional_ecology',
    'phase77b_line_position_gallows':    'gallows_line_position_split',
    'phase78_allograph_test':            'gallows_allograph_test',
    'phase79_gallows_collapse':          'gallows_collapse_vocabulary',
    'phase80_abjad_hypothesis':          'abjad_hypothesis',
    'phase81_german_genre_fingerprint':  'german_genre_fingerprint',
    'phase82_charm_fingerprint':         'charm_incantation_fingerprint',
    'phase82_line1_body_separation':     'line1_body_separation',

    # -- phase83-99: chunk grammar program -------------------------------
    'phase83_encoding_layer_sweep':      'encoding_layer_sweep',
    'phase83_subword_segmentation':      'branching_entropy_segmentation',
    'phase84_mi_meaning_area':           'mi_distance_curve',
    'phase85_chunk_fingerprint':         'chunk_fingerprint',
    'phase85_pelling_verbose_cipher':    'pelling_two_layer_cipher',
    'phase85R_revalidation':             'chunk_fingerprint_revalidation',
    'phase86_chunk_equivalence':         'chunk_equivalence_classes',
    'phase86R_revalidation':             'chunk_equivalence_revalidation',
    'phase87_gallows_null_test':         'gallows_null_test',
    'phase87_spectral_vc':               'spectral_vowel_consonant',
    'phase87R_revalidation':             'spectral_vc_revalidation',
    'phase88_position_identity':         'position_identity_decomposition',
    'phase89_context_divergence':        'cross_position_context_divergence',
    'phase90_crossword_chunk_mi':        'cross_word_chunk_dependencies',
    'phase91_zodiac_galenic_axis':       'zodiac_galenic_axis',
    'phase92_ae_minimal_pairs':          'ae_minimal_pairs',
    'phase93_currier_slot2_regime':      'currier_slot2_regime',
    'phase94_e_extension_morphology':    'e_extension_morphology',
    'phase95_currier_split_fingerprint': 'currier_split_fingerprint',
    'phase96_cluster_hchar':             'cluster_entropy_language_match',
    'phase97_slot_grammar_hchar':        'slot_grammar_entropy_model',
    'phase98_generative_chunk_model':    'generative_chunk_model',
    'phase99_script_typology':           'script_typology_comparison',

    # -- phase100-107: chunk-alphabet decipherment attempts --------------
    'phase100_decipherment':             'chunk_alphabet_decipherment',
    'phase101_currier_ab_dichotomy':     'currier_dichotomy_resolution',
    'phase102_historical_validation':    'historical_validation',
    'phase103_positional_class_decomposition': 'chunk_class_positions',
    'phase104_latin_ending_test':        'latin_inflection_ending_test',
    'phase105_cappelli_retest':          'cappelli_abbreviation_retest',
    'phase106_abbreviation_decode':      'f1r_abbreviation_decode',
    'phase106b_bench_variants':          'f1r_bench_substitution_variants',
    'phase106c_positional_freq_match':   'positional_frequency_language_match',
    'phase107_slot_mi_decomposition':    'chunk_slot_mutual_information',

    # -- phase108-111: research-program instruments ----------------------
    'phase108_controls_foundry':         'controls_foundry',
    'phase109_forgery_tournament':       'forgery_tournament',
    'phase110_alphabet_space_search':    'alphabet_space_search',
    'phase111_segmentation_agnostic':    'space_free_segmentation',
}

# bare phaseNN tokens that appear in strings (result filenames, prose
# cross-references). Numbers owned by exactly one script resolve globally;
# ambiguous numbers (multiple scripts share the number) resolve to the
# containing script's own stem first, and are reported for manual review
# when found elsewhere.
NUMBER_OWNERS = {}
for old, new in RENAME.items():
    import re as _re
    m = _re.match(r'phase(\d+[a-zA-Z]?)_', old)
    if m:
        NUMBER_OWNERS.setdefault(m.group(1), []).append((old, new))
