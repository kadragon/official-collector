# Official Collector

This project automates the classification and processing of official documents.

## Supabase Setup

To use this application, you need to set up a Supabase project and configure the necessary database schema. Follow these steps:

1. **Enable `pg_vector` Extension**

   - Go to your Supabase project dashboard.
   - Navigate to `Database` > `Extensions`.
   - Search for `pg_vector` and enable it.

2. **Create `documents` Table**
   Execute the following SQL query in your Supabase SQL Editor:

   ```sql
   CREATE TABLE IF NOT EXISTS documents (
       id uuid PRIMARY KEY,
       content text,
       metadata jsonb,
       embedding vector(1536)
   );
   ```

3. **Create `match_documents` Function**
   Execute the following SQL query in your Supabase SQL Editor:

   ```sql
   CREATE OR REPLACE FUNCTION public.match_documents(
       query_embedding vector(1536),
       match_count int DEFAULT NULL,
       filter jsonb DEFAULT '{}'
   ) RETURNS TABLE (
       id uuid,
       content text,
       metadata jsonb,
       embedding vector(1536),
       similarity float
   )
   LANGUAGE plpgsql
   AS $$
   #variable_conflict use_column
   BEGIN
       RETURN QUERY
       SELECT
           id,
           content,
           metadata,
           embedding,
           1 - (documents.embedding <=> query_embedding) AS similarity
       FROM documents
       WHERE filter IS NULL OR metadata @> filter
       ORDER BY documents.embedding <=> query_embedding
       LIMIT match_count;
   END;
   $$;
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the root of your project and add the following:

   ```
   OPENAI_API_KEY=YOUR_OPENAI_API_KEY
   SUPABASE_URL=YOUR_SUPABASE_URL
   SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY
   SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
   ```

   - `YOUR_OPENAI_API_KEY`: Your OpenAI API key.
   - `YOUR_SUPABASE_URL`: Your Supabase project URL (found in Project Settings > API).
   - `YOUR_SUPABASE_ANON_KEY`: Your Supabase `anon` public key (found in Project Settings > API).
   - `YOUR_SUPABASE_SERVICE_ROLE_KEY`: Your Supabase `service_role` secret key (found in Project Settings > API). **Keep this key secure and do not expose it in client-side code.**

## Running the Application

To run the main application:

```bash
python src/main.py
```

## Running Tests

To run the Supabase integration tests (requires `SUPABASE_SERVICE_ROLE_KEY` to be set in `.env`):

```bash
python tests/test_ai_supabase.py
```
