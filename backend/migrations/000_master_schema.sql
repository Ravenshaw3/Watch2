BEGIN;

-- Ensure required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    avatar_url VARCHAR(255),
    preferences TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    last_login TIMESTAMPTZ
);


-- Media files table
CREATE TABLE IF NOT EXISTS media_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL UNIQUE,
    file_size INTEGER NOT NULL,
    file_hash VARCHAR(64) UNIQUE,
    mime_type VARCHAR(100) NOT NULL,
    media_type VARCHAR(20) NOT NULL,
    category VARCHAR(100),
    duration_seconds INTEGER,
    title VARCHAR(255),
    year INTEGER,
    rating DOUBLE PRECISION,
    plot TEXT,
    director VARCHAR(255),
    genre VARCHAR(255),
    cast_list TEXT,
    runtime_minutes INTEGER,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    duration DOUBLE PRECISION,
    width INTEGER,
    height INTEGER,
    bitrate INTEGER,
    codec VARCHAR(50),
    container_format VARCHAR(20),
    thumbnail_path VARCHAR(500),
    poster_path VARCHAR(500),
    is_processed BOOLEAN DEFAULT FALSE,
    is_available BOOLEAN DEFAULT TRUE,
    processing_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    last_accessed TIMESTAMPTZ
);


-- Media metadata table
CREATE TABLE IF NOT EXISTS media_metadata (
    id SERIAL PRIMARY KEY,
    media_file_id INTEGER UNIQUE REFERENCES media_files(id) ON DELETE CASCADE,
    title VARCHAR(255),
    description TEXT,
    genre VARCHAR(100),
    year INTEGER,
    director VARCHAR(255),
    cast_list JSONB,
    rating VARCHAR(10),
    language VARCHAR(50),
    country VARCHAR(100),
    studio VARCHAR(255),
    tags JSONB,
    imdb_id VARCHAR(20),
    tmdb_id VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Transcoded files table
CREATE TABLE IF NOT EXISTS transcoded_files (
    id SERIAL PRIMARY KEY,
    original_file_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL,
    quality VARCHAR(20) NOT NULL,
    format VARCHAR(20) NOT NULL,
    file_size INTEGER,
    duration DOUBLE PRECISION,
    width INTEGER,
    height INTEGER,
    bitrate INTEGER,
    is_ready BOOLEAN DEFAULT FALSE,
    processing_progress INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS playlists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
    is_public BOOLEAN DEFAULT FALSE,
    is_smart BOOLEAN DEFAULT FALSE,
    smart_filters JSONB,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_playlists_owner_id ON playlists (owner_id);
CREATE INDEX IF NOT EXISTS ix_playlists_is_deleted ON playlists (is_deleted);

-- Playlist items table
CREATE TABLE IF NOT EXISTS playlist_items (
    id SERIAL PRIMARY KEY,
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    media_file_id INTEGER NOT NULL REFERENCES media_files(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW()
);


-- Watch history table
CREATE TABLE IF NOT EXISTS watch_history (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    media_file_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    watched_at TIMESTAMPTZ DEFAULT NOW(),
    watch_duration DOUBLE PRECISION,
    completion_percentage DOUBLE PRECISION,
    resume_position DOUBLE PRECISION
);


-- Viewing history table
CREATE TABLE IF NOT EXISTS viewing_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    media_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_watched_at TIMESTAMPTZ DEFAULT NOW(),
    watch_duration INTEGER DEFAULT 0,
    progress_percentage DOUBLE PRECISION DEFAULT 0.0,
    current_position INTEGER DEFAULT 0,
    completed VARCHAR(16) DEFAULT 'false',
    device_info TEXT,
    quality VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS ix_viewing_history_user_id ON viewing_history (user_id);
CREATE INDEX IF NOT EXISTS ix_viewing_history_media_id ON viewing_history (media_id);

-- Ratings table
CREATE TABLE IF NOT EXISTS ratings (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    media_file_id INTEGER REFERENCES media_files(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL,
    review TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);


-- System settings table used by settings endpoints
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Column alignment for legacy databases
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'users'
    ) THEN
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS username VARCHAR(50),
            ADD COLUMN IF NOT EXISTS email VARCHAR(100),
            ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255),
            ADD COLUMN IF NOT EXISTS full_name VARCHAR(100),
            ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(255),
            ADD COLUMN IF NOT EXISTS preferences TEXT,
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            ALTER COLUMN is_active SET DEFAULT TRUE,
            ALTER COLUMN is_superuser SET DEFAULT FALSE;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'media_files'
    ) THEN
        ALTER TABLE media_files
            ADD COLUMN IF NOT EXISTS category VARCHAR(100),
            ADD COLUMN IF NOT EXISTS duration_seconds INTEGER,
            ADD COLUMN IF NOT EXISTS title VARCHAR(255),
            ADD COLUMN IF NOT EXISTS year INTEGER,
            ADD COLUMN IF NOT EXISTS rating DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS plot TEXT,
            ADD COLUMN IF NOT EXISTS director VARCHAR(255),
            ADD COLUMN IF NOT EXISTS genre VARCHAR(255),
            ADD COLUMN IF NOT EXISTS cast_list TEXT,
            ADD COLUMN IF NOT EXISTS runtime_minutes INTEGER,
            ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS duration DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS width INTEGER,
            ADD COLUMN IF NOT EXISTS height INTEGER,
            ADD COLUMN IF NOT EXISTS bitrate INTEGER,
            ADD COLUMN IF NOT EXISTS codec VARCHAR(50),
            ADD COLUMN IF NOT EXISTS container_format VARCHAR(20),
            ADD COLUMN IF NOT EXISTS thumbnail_path VARCHAR(500),
            ADD COLUMN IF NOT EXISTS poster_path VARCHAR(500),
            ADD COLUMN IF NOT EXISTS is_processed BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS is_available BOOLEAN DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) DEFAULT 'pending',
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMPTZ;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'playlists'
    ) THEN
        ALTER TABLE playlists
            ADD COLUMN IF NOT EXISTS description TEXT,
            ADD COLUMN IF NOT EXISTS owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS is_smart BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS smart_filters JSONB,
            ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'playlist_items'
    ) THEN
        ALTER TABLE playlist_items
            ADD COLUMN IF NOT EXISTS position INTEGER,
            ADD COLUMN IF NOT EXISTS added_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'watch_history'
    ) THEN
        ALTER TABLE watch_history
            ADD COLUMN IF NOT EXISTS watch_duration DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS completion_percentage DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS resume_position DOUBLE PRECISION;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'ratings'
    ) THEN
        ALTER TABLE ratings
            ADD COLUMN IF NOT EXISTS review TEXT,
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
    END IF;
END $$;

-- Index alignment for legacy databases
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'users'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'username'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_users_username ON public.users (username)';
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'email'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_users_email ON public.users (email)';
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'is_deleted'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_users_is_deleted ON public.users (is_deleted)';
        END IF;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'media_files'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'media_files' AND column_name = 'file_hash'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_media_files_file_hash ON public.media_files (file_hash)';
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'media_files' AND column_name = 'is_deleted'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_media_files_is_deleted ON public.media_files (is_deleted)';
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'media_files' AND column_name = 'media_type'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_media_files_media_type ON public.media_files (media_type)';
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'media_files' AND column_name = 'category'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_media_files_category ON public.media_files (category)';
        END IF;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'playlists'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'playlists' AND column_name = 'owner_id'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_playlists_owner_id ON public.playlists (owner_id)';
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'playlists' AND column_name = 'is_deleted'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_playlists_is_deleted ON public.playlists (is_deleted)';
        END IF;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'playlist_items'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'playlist_items' AND column_name = 'playlist_id'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_playlist_items_playlist_id ON public.playlist_items (playlist_id)';
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'playlist_items' AND column_name = 'media_file_id'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_playlist_items_media_file_id ON public.playlist_items (media_file_id)';
        END IF;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'watch_history'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'watch_history' AND column_name = 'user_id'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_watch_history_user_id ON public.watch_history (user_id)';
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'watch_history' AND column_name = 'media_file_id'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_watch_history_media_file_id ON public.watch_history (media_file_id)';
        END IF;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'viewing_history'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'viewing_history' AND column_name = 'user_id'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_viewing_history_user_id ON public.viewing_history (user_id)';
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'viewing_history' AND column_name = 'media_id'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_viewing_history_media_id ON public.viewing_history (media_id)';
        END IF;
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'ratings'
    ) THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'ratings' AND column_name = 'user_id'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_ratings_user_id ON public.ratings (user_id)';
        END IF;
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'ratings' AND column_name = 'media_file_id'
        ) THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS ix_ratings_media_file_id ON public.ratings (media_file_id)';
        END IF;
    END IF;
END $$;

COMMIT;
