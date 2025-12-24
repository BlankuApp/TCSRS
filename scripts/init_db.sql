-- Topic-Centric SRS Database Schema for Supabase
-- This script initializes the database tables for the SRS API

-- Create decks table
CREATE TABLE IF NOT EXISTS decks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    prompt TEXT NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create topics table
CREATE TABLE IF NOT EXISTS topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deck_id UUID NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    stability DOUBLE PRECISION NOT NULL DEFAULT 24.0 CHECK (stability > 0),
    difficulty DOUBLE PRECISION NOT NULL DEFAULT 5.0 CHECK (difficulty >= 1 AND difficulty <= 10),
    next_review TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_reviewed TIMESTAMPTZ,
    cards JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    avatar TEXT,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    ai_prompts JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_topics_deck_id ON topics(deck_id);
CREATE INDEX IF NOT EXISTS idx_topics_next_review ON topics(next_review);
CREATE INDEX IF NOT EXISTS idx_decks_user_id ON decks(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON user_profiles(username);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_decks_updated_at
    BEFORE UPDATE ON decks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_topics_updated_at
    BEFORE UPDATE ON topics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE decks IS 'Decks contain topics organized by user';
COMMENT ON TABLE topics IS 'Topics represent subject areas with SRS parameters and embedded cards array';
COMMENT ON COLUMN topics.cards IS 'JSONB array storing cards with card_type, intrinsic_weight, and card_data fields';
COMMENT ON TABLE user_profiles IS 'User profile information with role and AI prompt preferences. Role changes require manual database updates.';
COMMENT ON COLUMN user_profiles.ai_prompts IS 'JSONB storing custom AI prompts dictionary for different operations';

-- ===========================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ===========================================

-- Enable RLS on all tables
ALTER TABLE decks ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;

-- ===========================================
-- DECKS TABLE POLICIES
-- ===========================================

-- Users can select their own decks
CREATE POLICY "Users can view own decks"
ON decks FOR SELECT
USING (auth.uid()::text = user_id);

-- Users can insert their own decks
CREATE POLICY "Users can create own decks"
ON decks FOR INSERT
WITH CHECK (auth.uid()::text = user_id);

-- Users can update their own decks
CREATE POLICY "Users can update own decks"
ON decks FOR UPDATE
USING (auth.uid()::text = user_id)
WITH CHECK (auth.uid()::text = user_id);

-- Users can delete their own decks
CREATE POLICY "Users can delete own decks"
ON decks FOR DELETE
USING (auth.uid()::text = user_id);

-- ===========================================
-- TOPICS TABLE POLICIES
-- ===========================================

-- Users can select topics in their decks
CREATE POLICY "Users can view topics in own decks"
ON topics FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM decks
    WHERE decks.id = topics.deck_id
    AND decks.user_id = auth.uid()::text
  )
);

-- Users can insert topics into their decks
CREATE POLICY "Users can create topics in own decks"
ON topics FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM decks
    WHERE decks.id = topics.deck_id
    AND decks.user_id = auth.uid()::text
  )
);

-- Users can update topics in their decks
CREATE POLICY "Users can update topics in own decks"
ON topics FOR UPDATE
USING (
  EXISTS (
    SELECT 1 FROM decks
    WHERE decks.id = topics.deck_id
    AND decks.user_id = auth.uid()::text
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM decks
    WHERE decks.id = topics.deck_id
    AND decks.user_id = auth.uid()::text
  )
);

-- Users can delete topics in their decks
CREATE POLICY "Users can delete topics in own decks"
ON topics FOR DELETE
USING (
  EXISTS (
    SELECT 1 FROM decks
    WHERE decks.id = topics.deck_id
    AND decks.user_id = auth.uid()::text
  )
);

-- ===========================================
-- USER_PROFILES TABLE POLICIES
-- ===========================================

-- All authenticated users can view any user profile
CREATE POLICY "Authenticated users can view all profiles"
ON user_profiles FOR SELECT
USING (auth.uid() IS NOT NULL);

-- Users can insert their own profile
CREATE POLICY "Users can create own profile"
ON user_profiles FOR INSERT
WITH CHECK (auth.uid()::text = user_id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
ON user_profiles FOR UPDATE
USING (auth.uid()::text = user_id)
WITH CHECK (auth.uid()::text = user_id);

-- Users can delete their own profile
CREATE POLICY "Users can delete own profile"
ON user_profiles FOR DELETE
USING (auth.uid()::text = user_id);
