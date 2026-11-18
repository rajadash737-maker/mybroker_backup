import logging

from firebase_admin import messaging

from app.services import fcm_service


def test_send_notification_success(monkeypatch):
    monkeypatch.setattr(fcm_service, "_ensure_firebase_initialized", lambda: None)
    monkeypatch.setattr(fcm_service.messaging, "send", lambda message: "projects/test/messages/1")

    result = fcm_service.send_notification("registration-token", "Title", "Body")

    assert result == {"success": True, "message_id": "projects/test/messages/1"}


def test_unregistered_error_is_reported_without_logging_token(monkeypatch, caplog):
    token = "registration-token-do-not-log"
    monkeypatch.setattr(fcm_service, "_ensure_firebase_initialized", lambda: None)

    def reject(_message):
        raise messaging.UnregisteredError("NotRegistered")

    monkeypatch.setattr(fcm_service.messaging, "send", reject)
    with caplog.at_level(logging.DEBUG, logger="app.services.fcm_service"):
        result = fcm_service.send_notification(token, "Title", "Body")

    assert result == {"success": False, "error": "unregistered"}
    assert token not in caplog.text


def test_other_firebase_failure_is_not_misclassified_or_logged_with_token(monkeypatch, caplog):
    token = "registration-token-do-not-log"
    monkeypatch.setattr(fcm_service, "_ensure_firebase_initialized", lambda: None)

    def fail(_message):
        raise RuntimeError(f"network failure involving {token}")

    monkeypatch.setattr(fcm_service.messaging, "send", fail)
    with caplog.at_level(logging.WARNING, logger="app.services.fcm_service"):
        result = fcm_service.send_notification(token, "Title", "Body")

    assert result == {"success": False, "error": "fcm_send_failed"}
    assert token not in caplog.text
