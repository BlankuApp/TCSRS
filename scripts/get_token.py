"""
Simple script to get a JWT token from Supabase for testing.
Usage: python scripts/get_token.py
"""
import os

from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()

def get_token():
    """Sign in to Supabase and print the JWT token"""
    # Get Supabase credentials from environment
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        return
    
    # Create Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Get credentials from user
    email = input("Enter email: ")
    password = input("Enter password: ")
    
    try:
        # Sign in
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        # Print token
        if response.session:
            token = response.session.access_token
            print("\n" + "="*80)
            print("JWT TOKEN:")
            print("="*80)
            print(token)
            print("="*80)
            print(f"\nUser ID: {response.user.id}")
            print(f"Email: {response.user.email}")
            print("\nUse this token in your requests:")
            print(f'Authorization: Bearer {token}')
        else:
            print("Error: No session returned")
            
    except Exception as e:
        print(f"Authentication failed: {e}")

if __name__ == "__main__":
    get_token()
