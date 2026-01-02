import uuid
from firebase_admin import firestore

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

def new_notification(user_id: str, notification: dict):
    if not user_id:
        raise ValueError("User ID is required")

    notification_id = str(uuid.uuid4())
    
    notification_data = {
        **notification,
        'by': {
            'isSystem': True
        },
        'read': False,
        'createdAt': firestore.SERVER_TIMESTAMP,
        'id': notification_id
    }

    notifications_ref = db.collection("notifications").document(user_id)
    transaction = db.transaction()
    
    _run_transaction(transaction, notifications_ref, notification_data, notification_id)