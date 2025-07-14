danya_id, nika_id, tocha_id = "786580423", "1028639864", "679210513"
ADMIN_IDS = [danya_id, nika_id]

EXCLUDED_IDS = [tocha_id]


def is_authorized(user_id):
    return str(user_id) in ADMIN_IDS


def is_excluded_from_stats(user_id):
    return str(user_id) in EXCLUDED_IDS
