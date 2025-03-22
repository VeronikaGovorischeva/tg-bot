from config import ADMIN_IDS


def is_authorized(user_id):
    return user_id in ADMIN_IDS
