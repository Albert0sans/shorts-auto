from firebase_admin import firestore
from google.cloud.firestore_v1.transaction import Transaction
from google.cloud.firestore_v1.document import DocumentReference

def get_credit_costs(db) -> dict:
    """
    Fetches the dynamic credit costs from Firestore.
    Returns default values if the document does not exist.
    """
    try:
        config_ref = db.collection("plan").document("limits")
        doc = config_ref.get()
        
        if doc.exists:
            return doc.to_dict()
            
        # Default fallback values matching TypeScript
        return {
            "image_generation_cost": 1,
            "text_generation_cost": 1,
            "video_generation_cost": 5,
            "shorts_generation_cost": 5
        }
    except Exception as e:
        print(f"Error fetching credit costs: {e}")
        return {
            "image_generation_cost": 1,
            "text_generation_cost": 1,
            "video_generation_cost": 5,
            "shorts_generation_cost": 5
        }

@firestore.transactional
def check_credits_transaction(transaction: Transaction, user_ref: DocumentReference, credits: int):
    """
    Checks if user has enough general credits in their plan.
    Reserves credits by adding to 'pending_usage'.
    
    Args:
        transaction: The active Firestore transaction.
        user_ref: Reference to the user document.
        credits: The TOTAL calculated cost (int) for the requested operation.
    """
    # Get the document snapshot
    snapshot = user_ref.get(transaction=transaction)
    
    if not snapshot.exists:
        raise ValueError("User profile not found.")
    
    user_data = snapshot.to_dict()
    limits = user_data.get('limits', {})

    # Use the unified fields matching the TS implementation
    current_pending = limits.get('pending_usage', 0)
    current_used = limits.get('used_usage', 0)
    max_limit = limits.get('limit', 0)

    # Check capacity
    if current_pending + current_used + credits > max_limit:
        available = max_limit - (current_used + current_pending)
        raise ValueError(f"Insufficient Credits. Available: {available}")

    # Update pending usage
    transaction.update(user_ref, {
        "limits.pending_usage": current_pending + credits,
    })

@firestore.transactional
def refund_credits_transaction(transaction: Transaction, user_ref: DocumentReference, credits: int):
    """
    Releases pending credits without moving them to used (e.g., after a failed generation).
    """
    snapshot = user_ref.get(transaction=transaction)
    
    if not snapshot.exists:
        print("User not found during refund, skipping.")
        return 

    user_data = snapshot.to_dict()
    limits = user_data.get('limits', {})

    current_pending = limits.get('pending_usage', 0)
    
    # Ensure we don't go below zero
    new_pending = max(0, current_pending - credits)

    transaction.update(user_ref, {
        "limits.pending_usage": new_pending,
    })

@firestore.transactional
def consume_credits_transaction(transaction: Transaction, user_ref: DocumentReference, credits: int):
    """
    Moves credits from 'pending_usage' to 'used_usage'.
    Call this after successful generation.
    """
    snapshot = user_ref.get(transaction=transaction)
    
    if not snapshot.exists:
        raise ValueError("User profile not found during consumption.")

    user_data = snapshot.to_dict()
    limits = user_data.get('limits', {})

    current_pending = limits.get('pending_usage', 0)
    current_used = limits.get('used_usage', 0)

    # Move from pending to used
    new_pending = max(0, current_pending - credits)
    new_used = current_used + credits

    transaction.update(user_ref, {
        "limits.pending_usage": new_pending,
        "limits.used_usage": new_used,
    })