# Firebase Admin SDK initialization
# TODO: Phase 1 - Complete Firebase setup when credentials available

import structlog
from app.config import settings

logger = structlog.get_logger()


def initialize_firebase():
    """
    Initialize Firebase Admin SDK.
    Requires FIREBASE_CREDENTIALS_PATH in environment.
    """
    
    if not settings.FIREBASE_CREDENTIALS_PATH:
        logger.warning("firebase_not_configured", message="FIREBASE_CREDENTIALS_PATH not set")
        return None
    
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred, {
            'projectId': settings.FIREBASE_PROJECT_ID,
        })
        
        db = firestore.client()
        logger.info("firebase_initialized", project_id=settings.FIREBASE_PROJECT_ID)
        return db
        
    except Exception as e:
        logger.error("firebase_initialization_failed", error=str(e))
        return None


# Initialize on module import
firestore_client = initialize_firebase()
