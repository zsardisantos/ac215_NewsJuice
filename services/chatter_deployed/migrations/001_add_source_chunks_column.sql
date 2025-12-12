-- Migration: Add source_chunks column to audio_history table
-- Purpose: Store the chunks used to generate daily briefs for context-aware Q&A
-- Date: 2025-12-04

ALTER TABLE audio_history
ADD COLUMN IF NOT EXISTS source_chunks JSONB DEFAULT NULL;

-- Add comment to document the column
COMMENT ON COLUMN audio_history.source_chunks IS 'JSON array of chunks used to generate daily brief. Format: {"chunks": [{"chunk_id": int, "chunk_text": string, "source_type": string, "score": float}]}';

-- Verify the column was added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'audio_history'
AND column_name = 'source_chunks';
