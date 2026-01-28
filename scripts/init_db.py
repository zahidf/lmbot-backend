"""
Script to initialise the database with tables and test data
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.persistence.database import init_db, engine
from sqlalchemy import text


async def create_vector_index():
    """Create vector similarity search index"""
    print("\n📊 Creating vector search index...")
    
    async with engine.begin() as conn:
        # Create IVFFlat index for faster similarity search
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
            ON document_chunks 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """))



async def create_test_user():
    """Create a test user"""
    
    from app.infrastructure.persistence.models.user_model import UserModel
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.infrastructure.persistence.database import async_session_factory
    import uuid
    
    async with async_session_factory() as session:
        # Check if test user exists
        result = await session.execute(
            text("SELECT id FROM users WHERE email = 'test@lanemark.com'")
        )
        if result.first():
            return
        
        # Create test user
        test_user = UserModel(
            id=uuid.uuid4(),
            email="test@lanemark.com",
            full_name="Test User",
            hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5L5L5L5L5L5L5",
            is_active=True
        )
        
        session.add(test_user)
        await session.commit()
        


async def main():
    """Main initialisation function"""
    
    try:

        await init_db()
        
        # Create vector index
        await create_vector_index()
        
        # Create test user
        await create_test_user()
        
        
    except Exception as e:
        print(f"\nError during initialisation: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())