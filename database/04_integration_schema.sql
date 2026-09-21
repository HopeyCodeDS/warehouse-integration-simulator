-- The Integration Engine's Audit Log
CREATE TABLE integration.integration_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source VARCHAR(50) NOT NULL,
    destination VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    correlation_id VARCHAR(100),
    payload JSONB,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);