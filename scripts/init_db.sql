-- Topic-Centric SRS Database Schema for Supabase
-- This script initializes the database tables for the SRS API

-- Create decks table
CREATE TABLE IF NOT EXISTS decks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
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
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create cards table with polymorphic card_data JSONB column
CREATE TABLE IF NOT EXISTS cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    card_type VARCHAR(50) NOT NULL CHECK (card_type IN ('qa_hint', 'multiple_choice')),
    intrinsic_weight DOUBLE PRECISION NOT NULL DEFAULT 1.0 CHECK (intrinsic_weight >= 0.5 AND intrinsic_weight <= 2.0),
    card_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_topics_deck_id ON topics(deck_id);
CREATE INDEX IF NOT EXISTS idx_topics_next_review ON topics(next_review);
CREATE INDEX IF NOT EXISTS idx_cards_topic_id ON cards(topic_id);
CREATE INDEX IF NOT EXISTS idx_cards_card_type ON cards(card_type);
CREATE INDEX IF NOT EXISTS idx_decks_user_id ON decks(user_id);

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

CREATE TRIGGER update_cards_updated_at
    BEFORE UPDATE ON cards
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE decks IS 'Decks contain topics organized by user';
COMMENT ON TABLE topics IS 'Topics represent subject areas with SRS parameters';
COMMENT ON TABLE cards IS 'Cards belong to topics, polymorphic via card_data JSONB';
COMMENT ON COLUMN cards.card_data IS 'JSONB storing type-specific fields (question, answer, choices, etc.)';
