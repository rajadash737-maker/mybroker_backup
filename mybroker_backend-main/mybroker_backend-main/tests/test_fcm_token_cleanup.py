from app.notifications import service as notification_service
from app.users.model import User


def test_unregistered_token_clears_only_matching_user_and_exact_token(admin_site_visit_api, monkeypatch):
    _, _, actors, *_rest = admin_site_visit_api
    Session = _rest[-1]
    db = Session()
    buyer = db.get(User, actors["buyer"].id)
    other_user = db.get(User, actors["admin"].id)
    buyer.fcm_token = "stale-token-for-buyer"
    other_user.fcm_token = "unrelated-valid-token"
    db.commit()

    monkeypatch.setattr(
        notification_service,
        "send_notification",
        lambda **kwargs: {"success": False, "error": "unregistered"},
    )
    notification_service.notify_users(
        db=db,
        users=[buyer],
        title="Test",
        body="Notification",
        notif_type="FCM_CLEANUP_TEST",
    )

    db.expire_all()
    assert db.get(User, buyer.id).fcm_token is None
    assert db.get(User, other_user.id).fcm_token == "unrelated-valid-token"
    db.close()


def test_unregistered_old_token_does_not_clear_replacement_token(admin_site_visit_api):
    from app.notifications.service import _clear_unregistered_fcm_token

    _, _, actors, *_rest = admin_site_visit_api
    Session = _rest[-1]
    db = Session()
    buyer = db.get(User, actors["buyer"].id)
    buyer.fcm_token = "replacement-token"
    db.commit()

    cleared = _clear_unregistered_fcm_token(
        db,
        user_id=buyer.id,
        token="older-token-reported-unregistered",
    )

    db.expire_all()
    assert cleared is False
    assert db.get(User, buyer.id).fcm_token == "replacement-token"
    db.close()


def test_unrelated_delivery_failure_keeps_user_token(admin_site_visit_api, monkeypatch):
    from app.notifications.service import notify_users

    _, _, actors, *_rest = admin_site_visit_api
    Session = _rest[-1]
    db = Session()
    buyer = db.get(User, actors["buyer"].id)
    buyer.fcm_token = "token-to-retain"
    db.commit()
    monkeypatch.setattr(
        notification_service,
        "send_notification",
        lambda **kwargs: {"success": False, "error": "fcm_send_failed"},
    )

    notify_users(db, [buyer], "Test", "Body", "FCM_GENERIC_FAILURE_TEST")

    db.expire_all()
    assert db.get(User, buyer.id).fcm_token == "token-to-retain"
    db.close()
