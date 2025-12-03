from firebase_admin import firestore

def ChangeDDBBStatus(db, user_id, short_build_id, new_status,status_msg):
    user_ref = db.collection('users').document(user_id)
    
    doc_ref = user_ref.collection('generatedShorts').document(short_build_id)
    
    doc_ref.set({
        "genRequest.status": new_status,
        "genRequest.lastUpdatedAt": firestore.SERVER_TIMESTAMP
        "genRequest.statusMessage": status_msg,
    }, merge=True)