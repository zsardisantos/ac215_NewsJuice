-- Create Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create User Preferences Table
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    preference_key VARCHAR(255) NOT NULL,
    preference_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, preference_key)
);

-- Create Audio History Table
CREATE TABLE IF NOT EXISTS audio_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    question_text TEXT,
    podcast_text TEXT,
    audio_url TEXT,
    source_chunks TEXT, -- JSON string or JSONB
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
