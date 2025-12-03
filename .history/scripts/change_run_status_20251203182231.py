from firebase_admin import  firestore
def ChangeDDBBStatus(db,user_id,short_build_id,new_status):
        user_ref = db.collection('users').document(user_id)
        
        doc_ref = user_ref.collection('generatedShorts').document(short_build_id)
        doc_ref.set({
                           "status": new_status,
                            "lastUpdatedAt": firestore.SERVER_TIMESTAMP
      }, merge=True)