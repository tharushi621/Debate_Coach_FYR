# Test evidence (generated 2026-11-16 22:08)

Machine: Windows-10-10.0.26200-SP0 · Python 3.11.0
Automated run: 88 passed, 0 failed, 0 skipped, out of 88 tests (`pytest tests`).

| Thesis test case | Automated tests that exercised it | Result |
|---|---|---|
| 7.4 TC1 Debate topic selection | 2 | PASS |
| 7.4 TC2 Debate side selection | 2 | PASS |
| 7.4 TC3 Empty argument validation | 3 | PASS |
| 7.4 TC4 Short argument validation | 1 | PASS |
| 7.4 TC5 Toulmin component extraction | 2 | PASS |
| 7.4 TC6 Score range 1-5 | 5 | PASS |
| 7.4 TC7 Overall score calculation | 6 | PASS |
| 7.4 TC8 Weakness-to-intervention mapping | 4 | PASS |
| 7.4 TC9 LLM JSON parsing | 1 | PASS |
| 7.4 TC10 Database record creation | 1 | PASS |
| 7.5 TC1 Session creation and argument submission | 1 | PASS |
| 7.5 TC2-4 Analysis -> scoring -> diagnosis -> opponent | 2 | PASS |
| 7.5 TC5 Adaptive response stored in database | 2 | PASS |
| 7.5 TC6 Progress tracking integration | 2 | PASS |
| 7.6 TC1/2 End-to-end and multi-turn workflow | 2 | PASS |
| 7.6 TC3 API functionality | 2 | PASS |
| 7.6 TC5 Database persistence across restart | 1 | PASS |

## Manual checks (not run by the computer; tick when you have really done them)

- [ ] 7.6 TC4 Browser compatibility (Chrome, Edge, Firefox): open the Streamlit app in each browser and tick here
- [ ] 7.6 TC1 End-to-end through the real Streamlit page with a real model: play one debate and tick here

## Every automated test as run

- PASS: test_a_single_copied_column_is_flagged_even_when_another_column_differs
- PASS: test_agreement_resolution_and_reference
- PASS: test_ai_notice_is_not_repeated_on_result_pages_but_stays_on_the_how_it_works_page
- PASS: test_an_all_no_ghostwriting_column_is_not_mistaken_for_copying
- PASS: test_api_engine_error_kinds_and_side_mapping
- PASS: test_api_engine_maps_real_shapes
- PASS: test_api_exposes_topics_custom_motion_and_end
- PASS: test_api_flow_and_persistence
- PASS: test_api_only_supports_the_adaptive_mode
- PASS: test_argument_map_marks_found_missing_and_the_main_gap_and_escapes_text
- PASS: test_baselines_return_valid_labels_and_replies
- PASS: test_blind_sheets_hide_the_arm_and_analysis_reads_ratings
- PASS: test_blinded_arms_get_flat_xp_and_no_quality_signal
- PASS: test_blinding_no_quality_xp_for_control_arms
- PASS: test_claim_wording_matches_what_data_can_support
- PASS: test_coach_workbooks_have_own_order_and_round_trip
- PASS: test_conversation_history_reaches_the_opponent
- PASS: test_crew_has_seven_agents_with_a_debate_orchestrator
- PASS: test_crew_runs_all_agents_in_order_and_saves_the_turn
- PASS: test_custom_motion_is_validated_and_stored
- PASS: test_data_survives_restart
- PASS: test_developer_and_non_adaptive_sessions_never_count
- PASS: test_diagnose_compares_all_arms_on_the_same_items
- PASS: test_diagnosis_drives_intervention
- PASS: test_eight_labellers_use_a_strict_majority_and_report_fleiss_kappa
- PASS: test_eval_respects_split_and_logs_every_test_run
- PASS: test_evaluation_needs_human_labels
- PASS: test_every_table_gets_rows_for_a_turn
- PASS: test_every_weakness_has_a_training_family
- PASS: test_every_weakness_has_intervention
- PASS: test_fallback_and_source_are_persisted
- PASS: test_finish_debate_does_not_mutate_and_levels_up
- PASS: test_full_turn_and_progress
- PASS: test_full_turn_points_badges_and_no_mutation
- PASS: test_guardrail_replaces_leaky_or_toothless_reply
- PASS: test_identical_ratings_in_both_files_are_flagged_not_reported_as_agreement
- PASS: test_invalid_labels_are_rejected
- PASS: test_json_extraction_tolerates_prose
- PASS: test_leaky_reply_is_replaced_and_recorded_as_fallback
- PASS: test_level_up_flag
- PASS: test_levels
- PASS: test_levels_monotonic
- PASS: test_llm_diagnosis_accepted_when_valid_and_near_lowest
- PASS: test_llm_diagnosis_rejected_falls_back_to_lowest_dimension
- PASS: test_low_score_still_encouraging
- PASS: test_majority_and_plurality_rules_exclude_undecided_items_instead_of_guessing
- PASS: test_mastery_tiers_and_progress_to_the_next_tier
- PASS: test_mcnemar_counts_discordant_pairs
- PASS: test_new_session_is_active_and_an_ended_session_rejects_arguments
- PASS: test_nickname_rules_and_availability
- PASS: test_no_emoji_anywhere_in_the_interface_code
- PASS: test_no_mock_model_or_control_arms_left_in_app
- PASS: test_objective_points_become_xp_only_when_the_full_report_is_shown
- PASS: test_objectives_follow_the_scores_and_award_points
- PASS: test_one_row_per_participant_uses_the_longest_session_and_can_be_anonymised
- PASS: test_outcome_labels
- PASS: test_pilot_tables_from_database
- PASS: test_predict_resumes_and_analyse_scores_both_references
- PASS: test_preprocess_keeps_meaning_of_curly_quotes_and_dashes
- PASS: test_progress_has_the_thesis_6_2_7_fields
- PASS: test_rate_limit_is_waited_out_and_never_reported_as_none
- PASS: test_rater_workbooks_round_trip_into_the_analysis
- PASS: test_ratings_use_the_latest_submission_of_each_participant
- PASS: test_recommend_steps_up_and_changes_category
- PASS: test_reply_generation_resumes_after_a_failure_without_redoing_finished_items
- PASS: test_report_and_study_summary_work_on_an_empty_database
- PASS: test_report_flags_participant_count_mismatch
- PASS: test_report_reads_a_diagnostic_run_and_cross_checks_the_thesis
- PASS: test_score_bars_use_tone_classes
- PASS: test_score_clamping_overall_and_default_is_flagged
- PASS: test_sheets_are_blind_balanced_and_deterministic
- PASS: test_sheets_are_never_overwritten_once_labels_exist
- PASS: test_soft_flags_identify_but_do_not_reject
- PASS: test_stale_cached_modules_are_replaced_on_the_next_run
- PASS: test_streak
- PASS: test_streak_builds_and_resets
- PASS: test_thesis_example_overall_is_2_86
- PASS: test_thesis_motions_are_stored_in_the_database
- PASS: test_tie_break_prefers_more_consequential
- PASS: test_token_hashed_expires_and_logout
- PASS: test_topics_complete_and_no_repeat
- PASS: test_toss_is_fair_and_maps_sides
- PASS: test_training_feedback_is_actionable
- PASS: test_unknown_llm_backend_is_an_error_not_a_silent_mock
- PASS: test_validation_rejects_empty_short_duplicate
- PASS: test_weakness_change_after_turn_1_is_counted_like_thesis_7_10
- PASS: test_wilson_interval_matches_reference_values
- PASS: test_wilson_interval_matches_thesis_example
