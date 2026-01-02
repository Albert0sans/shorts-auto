from firebase_admin import firestore

from scripts.notification import NotificationEventType, send_notification

def ChangeDDBBStatus(db, user_id, short_build_id, new_status, status_msg:str=""):
    user_ref = db.collection('users').document(user_id)
    
    doc_ref = user_ref.collection('generatedShorts').document(short_build_id)
    
    doc_ref.set({
        "genRequest": {
            "status": new_status,
            "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
            "statusMessage": status_msg,
        }
    }, merge=True)
    if(new_status == "failed"):
        send_notification(db,user_id=user_id,event_type=NotificationEventType.SHORT_FAILED,target_id=short_build_id)
    elif(new_status == "completed"):
        send_notification(db,user_id=user_id,event_type=NotificationEventType.SHORT_GENERATED,target_id=short_build_id)
        
