from firebase_admin import firestore
from google.cloud.firestore_v1.transaction import Transaction
from google.cloud.firestore_v1.document import DocumentReference

@firestore.transactional
def check_credits_transaction(transaction: Transaction, user_ref: DocumentReference, credits: int):
    """
    Checks if user has limits, raises error if not. 
    Reserves credits by adding to 'pending'.
    """
    print("check_credits_transaction")
    
    # Get the document snapshot
    snapshot = user_ref.get(transaction=transaction)
    
    if not snapshot.exists:
        raise ValueError("User profile not found.")
    
    user_data = snapshot.to_dict()
    limits = user_data.get('limits', {})

    # --- Videos ---
    current_pending_videos = limits.get('pending_usage_videos', 0)
    current_used_videos = limits.get('used_usage_videos', 0)
    max_videos = limits.get('limit_videos', 0)

    if current_pending_videos + current_used_videos + video_credits > max_videos:
        available = max_videos - (current_used_videos + current_pending_videos)
        raise ValueError(f"Insufficient Video Credits. Available: {available}")

    # --- Images ---
    current_pending_images = limits.get('pending_usage_images', 0) 
    current_used_images = limits.get('used_usage_images', 0)
    max_images = limits.get('limit_images', 0)

    if current_pending_images + current_used_images + image_credits > max_images:
        available = max_images - (current_used_images + current_pending_images)
        raise ValueError(f"Insufficient Image Credits. Available: {available}")

    # --- Text ---
    current_pending_text = limits.get('pending_usage_text', 0)
    current_used_text = limits.get('used_usage_text', 0)
    max_text = limits.get('limit_text', 0)

    if current_pending_text + current_used_text + text_credits > max_text:
        available = max_text - (current_used_text + current_pending_text)
        raise ValueError(f"Insufficient Text Credits. Available: {available}")

    # Perform the update
    transaction.update(user_ref, {
        "limits.pending_usage_videos": current_pending_videos + video_credits,
        "limits.pending_usage_images": current_pending_images + image_credits,
        "limits.pending_usage_text": current_pending_text + text_credits,
    })

@firestore.transactional
def refund_credits_transaction(transaction: Transaction, user_ref: DocumentReference, video_credits: int, image_credits: int, text_credits: int):
    """
    Releases pending credits without moving them to used (e.g., failed generation).
    """
    snapshot = user_ref.get(transaction=transaction)
    
    if not snapshot.exists:
        return 

    user_data = snapshot.to_dict()
    limits = user_data.get('limits', {})

    current_pending_videos = limits.get('pending_usage_videos', 0)
    new_pending_videos = max(0, current_pending_videos - video_credits)

    current_pending_images = limits.get('pending_usage_images', 0)
    new_pending_images = max(0, current_pending_images - image_credits)

    current_pending_text = limits.get('pending_usage_text', 0)
    new_pending_text = max(0, current_pending_text - text_credits)

    transaction.update(user_ref, {
        "limits.pending_usage_videos": new_pending_videos,
        "limits.pending_usage_images": new_pending_images,
        "limits.pending_usage_text": new_pending_text,
    })

@firestore.transactional
def consume_credits_transaction(transaction: Transaction, user_ref: DocumentReference, video_credits: int, image_credits: int, text_credits: int):
    """
    Moves credits from 'pending' to 'used'.
    """
    snapshot = user_ref.get(transaction=transaction)
    
    if not snapshot.exists:
        raise ValueError("User profile not found during consumption.")

    user_data = snapshot.to_dict()
    limits = user_data.get('limits', {})

    # --- Videos ---
    current_pending_videos = limits.get('pending_usage_videos', 0)
    current_used_videos = limits.get('used_usage_videos', 0)
    new_pending_videos = max(0, current_pending_videos - video_credits)
    new_used_videos = current_used_videos + video_credits

    # --- Images ---
    current_pending_images = limits.get('pending_usage_images', 0)
    current_used_images = limits.get('used_usage_images', 0)
    new_pending_images = max(0, current_pending_images - image_credits)
    new_used_images = current_used_images + image_credits

    # --- Text ---
    current_pending_text = limits.get('pending_usage_text', 0)
    current_used_text = limits.get('used_usage_text', 0)
    new_pending_text = max(0, current_pending_text - text_credits)
    new_used_text = current_used_text + text_credits

    transaction.update(user_ref, {
        "limits.pending_usage_videos": new_pending_videos,
        "limits.used_usage_videos": new_used_videos,
        
        "limits.pending_usage_images": new_pending_images,
        "limits.used_usage_images": new_used_images,
        
        "limits.pending_usage_text": new_pending_text,
        "limits.used_usage_text": new_used_text,
    })