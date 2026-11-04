\set ON_ERROR_STOP on

BEGIN;

GRANT CONNECT ON DATABASE ai_tourism_dev TO :"app_user";

GRANT USAGE ON SCHEMA identity, conversation, travel, knowledge,
    recommendation, integration, operations TO :"app_user";

-- The application can manage user/trip/conversation/recommendation/operations
-- records, but it can only read the knowledge catalogue and RAG corpus.
-- Curated facts, provenance, verification and embedding-space configuration
-- are written only by controlled import/migration processes.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA identity, conversation, travel,
        recommendation, integration, operations
    TO :"app_user";

-- Remove any earlier/broad knowledge grants; raw unverified rows must not be
-- directly readable by the runtime application role.
REVOKE ALL ON ALL TABLES IN SCHEMA knowledge FROM :"app_user";
GRANT SELECT ON
    knowledge.production_destinations,
    knowledge.production_destination_sources,
    knowledge.production_destination_categories,
    knowledge.production_destination_category_map,
    knowledge.production_destination_tags,
    knowledge.production_retrieval_documents,
    knowledge.production_retrieval_chunks,
    knowledge.active_embedding_spaces,
    knowledge.production_chunk_embeddings
TO :"app_user";

-- Dataset import batches are written only by controlled import tooling.
REVOKE ALL ON operations.dataset_import_batches FROM :"app_user";

GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA identity, conversation, travel,
        recommendation, integration, operations
    TO :"app_user";

ALTER DEFAULT PRIVILEGES FOR ROLE ai_tourism_owner IN SCHEMA identity, conversation,
    travel, recommendation, integration, operations
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app_user";

ALTER DEFAULT PRIVILEGES FOR ROLE ai_tourism_owner IN SCHEMA knowledge
    REVOKE SELECT ON TABLES FROM :"app_user";

ALTER DEFAULT PRIVILEGES FOR ROLE ai_tourism_owner IN SCHEMA identity, conversation,
    travel, recommendation, integration, operations
    GRANT USAGE, SELECT ON SEQUENCES TO :"app_user";

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0004_app_role_grants', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
