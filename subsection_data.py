# subsection_data.py
"""Subsection to split number mapping data.

This data maps (chapter, subsection_name) tuples to split numbers.
Values can be either:
  - int: A single split number
  - list[int]: Multiple possible split numbers (first unused will be selected)
"""

SUBSECTION_MAP = {
    # Chapter 1
    (1, "st13_gamedesign_b_player_start_1"): 2,
    (1, "st13_gamedesign_b_player_start_2"): 3,
    (1, "st13_gamedesign_b_player_start_3"): 5,
    (1, "st13_gamedesign_b_player_start_4"): 7,
    (1, "st13_gamedesign_b_player_start_6"): 4,
    (1, "st13_gamedesign_b_player_start_7"): 6,

    # Chapter 2
    (2, "gd01_npc_player_check_1"): 3,
    (2, "gd01_npc_player_check_3"): 4,
    (2, "gd01_npc_player_check_4"): 5,
    (2, "gd01_npc_player_check_5"): 6,
    (2, "gd01_npc_player_check_6"): 2,

    # Chapter 3
    (3, "gd03_em_player_start_check_1"): 3,
    (3, "gd03_em_player_start_check_4"): 4,
    (3, "pl_start_village_inside"): 2,

    # Chapter 4
    (4, "gd04_player_start_1"): 3,
    (4, "player_start_1"): 4,
    (4, "player_start_3"): 7,
    (4, "player_start_4"): 5,
    (4, "player_start_village_a_3"): 2,
    (4, "test_player_start_2"): 6,

    # Chapter 5
    (5, "gd06_player_start_1"): 10,
    (5, "gd06_player_start_2"): 11,
    (5, "gd06_player_start_3"): 12,
    (5, "gd06_player_start_4"): 13,
    (5, "st06_asylummain_player_start_10"): 8,
    (5, "st06_asylummain_player_start_12"): 3,
    (5, "st06_asylummain_player_start_14"): 9,
    (5, "st06_asylummain_player_start_4"): 5,
    (5, "st06_asylummain_player_start_5"): 4,
    (5, "st06_asylummain_player_start_8"): 2,
    (5, "st06_asylummain_player_start_b"): 7,
    (5, "st06_asylummain_player_start_kidrescue_restart_a_02"): 6,

    # Chapter 6
    (6, "phase00_checkpoint_2"): 3,
    (6, "phase00_checkpoint_3"): 2,
    (6, "phase00_checkpoint_4"): 5,
    (6, "phase00_checkpoint_5"): 4,
    (6, "phase00_checkpoint_6"): 4,
    (6, "phase01_player_check_point_1"): 9,
    (6, "phase01_player_check_point_4"): 11,
    (6, "phase01_player_check_point_5"): 10,
    (6, "phase01_player_check_point_6"): 12,
    (6, "phase01_player_check_point_7"): 13,
    (6, "phase01_player_check_point_guillotine"): 6,
    (6, "phase01_player_check_point_guillotine_2"): 7,
    (6, "st21_gd_square_check_point_player_1"): 8,

    # Chapter 7
    (7, "cata_gd_b1_player_start_1"): 2,
    (7, "cata_gd_b1_player_start_2"): 3,
    (7, "cata_gd_b1_player_start_4"): 7,
    (7, "cata_gd_b1_player_start_5"): 5,
    (7, "cata_gd_b1_player_start_6"): 8,
    (7, "cata_gd_b4_player_start_7"): 11,
    (7, "cata_gd_b4_player_start_8"): 10,
    (7, "p04_gd_b2_player_start_1"): 6,
    (7, "p04_gd_b3_player_start_1"): 4,
    (7, "p04_gd_b4_player_start_1"): 9,

    # Chapter 8
    (8, "st02_cave_enemy_season1_player_start_1"): 3,
    (8, "st02_cave_game_system_player_checkpoint_1"): 4,
    (8, "st02_cave_game_system_player_checkpoint_2"): 5,
    (8, "st02_cave_game_system_player_checkpoint_3"): 6,
    (8, "st02_cave_game_system_player_checkpoint_4"): 7,
    (8, "st02_cave_game_system_player_start_1"): 2,

    # Chapter 9
    (9, "boogeymanbarnevent_player_start_2"): 9,
    (9, "boogeymanevent_player_start_1"): 6,
    (9, "boogeymanevent_player_start_3"): 8,
    (9, "boogeymanevent_player_start_at_piano_wire"): 7,
    (9, "gamedesign01_player_start_1"): [3, 4, 5],
    (9, "gamedesign01_player_start_2"): [3, 4, 5],
    (9, "gamedesign01_player_start_3"): [3, 4, 5],
    (9, "gamedesign01_player_start_4"): 2,

    # Chapter 10
    (10, "st08_alpha_player_start_1"): 10,
    (10, "st08_alpha_player_start_2"): 11,
    (10, "st08_bsmtmz_player_start_1"): 4,
    (10, "st08_bsmtmz_player_start_3"): 6,
    (10, "st08_bsmtmz_player_start_4"): 7,
    (10, "st08_bsmtmz_player_start_5"): 8,
    (10, "st08_bsmtmz_player_start_6"): 2,
    (10, "st08_bsmtmz_player_start_7"): 5,
    (10, "st08_bsmtmz_player_start_8"): 9,
    (10, "st08_bsmtmz_player_start_9"): 3,

    # Chapter 11
    (11, "p06a_gd_player_start_1"): 2,
    (11, "p06c_gd_player_start_4"): 5,
    (11, "st22_gamedesign_part_02_player_start_1"): 11,
    (11, "st22_gamedesign_part_02_player_start_2"): 12,
    (11, "st22_gamedesign_part_02_player_start_3"): 10,
    (11, "st22_gamedesign_part_03_player_start_1"): 15,
    (11, "st22_gamedesign_part_03_player_start_7"): 16,
    (11, "st22_p03_gd_a02_check_point_player_1"): 9,
    (11, "st22_p03_gd_checkpoint_1"): 6,
    (11, "st22_p03_gd_checkpoint_3"): 7,
    (11, "st22_p03_gd_checkpoint_4"): 8,
    (11, "st22_phase_02_game_player_start_5"): 3,
    (11, "st22_phase_02_game_player_start_6"): 4,
    (11, "st22_prop_new_office_00_player_start_44444"): 13,
    (11, "st22_prop_new_office_00_player_start_44445"): 14,

    # Chapter 12
    (12, "st23_gd_part_01_player_start_2"): 3,
    (12, "st23_gd_part_01_player_start_3"): 2,
    (12, "st23_gd_part_01_player_start_4"): 5,
    (12, "st23_gd_part_01_player_start_5"): 4,

    # Chapter 13
    (13, "st24_gd_hgr_player_start_1"): 3,
    (13, "st24_gd_hgr_player_start_10"): 6,
    (13, "st24_gd_hgr_player_start_3"): 5,
    (13, "st24_gd_hgr_player_start_4"): 4,
    (13, "st24_gd_hkt_e_kitchen_chekpoint_1"): 7,
    (13, "st24_gd_hkt_player_start_4"): 9,
    (13, "st24_gd_hkt_player_start_5"): 8,
    (13, "st24_gd_top_player_start_1"): 2,

    # Chapter 14
    (14, "st25_gd_rift_player_start_2"): 12,
    (14, "st25_gd_rift_player_start_3"): 13,
    (14, "st25_gd_sew_player_start_1"): 6,
    (14, "st25_gd_sew_player_start_2"): 8,
    (14, "st25_gd_sew_player_start_4"): 7,
    (14, "st25_gd_ss_player_start_3"): 9,
    (14, "st25_gd_ss_player_start_5"): 10,
    (14, "st25_gd_ss_player_start_6"): 11,
    (14, "st25_gd_sta_player_start_2"): 2,
    (14, "st25_gd_sta_player_start_3"): 3,
    (14, "st25_gd_sta_player_start_4"): 5,
    (14, "st25_gd_sta_player_start_5"): 4,

    # Chapter 15
    (15, "gd_l_battle_player_start_1"): 4,
    (15, "gd_l_battle_player_start_3"): 6,
    (15, "gd_l_battle_player_start_4"): 7,
    (15, "gd_l_battle_player_start_5"): 5,
    (15, "player_start_1"): 8,
    (15, "player_start_4"): 10,
    (15, "st40_gamedesign_part_01_player_restart_chase"): 12,
    (15, "st40_gamedesign_part_01_player_restart_dodge"): 13,
    (15, "st40_gamedesign_part_01_player_start_7"): 3,
    (15, "st40_gamedesign_part_01_player_start_bigstem_restaret"): 11,
    (15, "st40_gamedesign_part_01_player_start_restart_handgun"): 16,
    (15, "st40_gamedesign_part_01_player_start_rocket_restart"): 15,
    (15, "st40_gamedesign_part_01_player_start_rotary_start"): 2,
    (15, "st40_gamedesign_part_01_player_start_turret_restart"): 14,
}
