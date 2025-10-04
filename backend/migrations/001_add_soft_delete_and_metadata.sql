BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'users'
    ) THEN
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
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
            ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

DO $$
DECLARE
    has_duration_column BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'media_files'
          AND column_name = 'duration'
    ) INTO has_duration_column;

    IF has_duration_column THEN
        EXECUTE format(
            'UPDATE media_files
             SET duration_seconds = COALESCE(duration_seconds, CAST(duration AS INTEGER))
             WHERE duration_seconds IS NULL
               AND duration IS NOT NULL'
        );
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'playlists'
    ) THEN
        ALTER TABLE playlists
            ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_users_is_deleted ON users (is_deleted);
CREATE INDEX IF NOT EXISTS ix_media_files_is_deleted ON media_files (is_deleted);
CREATE INDEX IF NOT EXISTS ix_playlists_is_deleted ON playlists (is_deleted);

COMMIT;
