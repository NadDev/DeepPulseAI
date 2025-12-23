"""
Supabase Client Configuration
Handles connection to Supabase for Auth and User data
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")

# Public client (for frontend operations)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Service client (for backend admin operations - has elevated privileges)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if SUPABASE_SERVICE_KEY else None


def get_supabase() -> Client:
    """Get Supabase client for dependency injection"""
    return supabase


def get_supabase_admin() -> Client:
    """Get Supabase admin client for backend operations"""
    if not supabase_admin:
        raise ValueError("SUPABASE_SERVICE_KEY not configured")
    return supabase_admin
