from app_config import DEBUG_ENABLED


def debug_log(message):
    """Print debug messages only when LOCAL_AI_DEBUG=1 is set."""
    if DEBUG_ENABLED:
        print(f"[debug] {message}")
