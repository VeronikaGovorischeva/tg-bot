danya_id, nika_id = 786580423, 1028639864
ADMIN_IDS = [danya_id,]


def is_authorized(user_id):
    return user_id in ADMIN_IDS
