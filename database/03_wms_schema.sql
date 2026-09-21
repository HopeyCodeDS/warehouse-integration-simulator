-- WMS owns Physical Layout, Stock, and Equipment Configuration
CREATE TABLE wms.locations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE wms.inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_sku VARCHAR(50) NOT NULL,
    location_id UUID REFERENCES wms.locations(id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_sku, location_id)
);

-- Equipment Configuration Tables
CREATE TABLE wms.equipment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    protocol VARCHAR(20) NOT NULL,
    ip_address VARCHAR(50),
    enabled BOOLEAN DEFAULT TRUE
);

CREATE TABLE wms.equipment_parameters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    equipment_id UUID REFERENCES wms.equipment(id) ON DELETE CASCADE,
    parameter VARCHAR(100) NOT NULL,
    value TEXT,
    UNIQUE(equipment_id, parameter)
);

CREATE TABLE wms.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(100) NOT NULL,
    correlation_id VARCHAR(100),
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);