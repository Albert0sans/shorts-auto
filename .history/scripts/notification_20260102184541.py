import uuid
from firebase_admin import firestore
class NotificationEventType:
    SHORT_GENERATED = "SHORT_GENERATED"
    SHORT_FAILED = "SHORT_FAILED"
db = firestore.client()

@firestore.transactional
def _run_transaction(transaction, doc_ref, data, notification_id):
    snapshot = doc_ref.get(transaction=transaction)

    if snapshot.exists:
        transaction.update(doc_ref, {
            f'items.{notification_id}': data
        })
    else:
        transaction.set(doc_ref, {
            'items': {
                notification_id: data
            }
        })

def send_notification(db, user_id, event_type=NotificationEventType.SHORT_GENERATED, target_id=None):
    if not user_id:
        return

    notification_id = str(uuid.uuid4())
    
    notif_type = "info"
    specific_type = "System"

    if event_type == NotificationEventType.SHORT_GENERATED:
        notif_type = "success"
        specific_type = "SHORT_GENERATED"
    elif event_type == NotificationEventType.SHORT_FAILED:
        notif_type = "error"
        specific_type = "SHORT_FAILED"

    notification_data = {
        'id': notification_id,
        'targetId': target_id,
        'type': notif_type,
        'specific_type': specific_type, 
        'tags':['shorts'],
        'createdAt': firestore.SERVER_TIMESTAMP,
        'read': False,
        'by': {
            'isSystem': True
        }
    }

    notifications_ref = db.collection("notifications").document(user_id)
    transaction = db.transaction()
    try:
        _run_notification_transaction(transaction, notifications_ref, notification_data, notification_id)
    except Exception as e:
        print(f"Failed to send notification: {e}")
