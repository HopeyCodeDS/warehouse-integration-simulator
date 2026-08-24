-- ERP owns Master Data and Orders
CREATE TABLE erp.products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE erp.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(100) UNIQUE NOT NULL,
    customer VARCHAR(255) NOT NULL,
    destination_dock VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE erp.order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES erp.orders(id) ON DELETE CASCADE,
    product_sku VARCHAR(50) NOT NULL, -- WMS will match against this SKU
    requested_qty INT NOT NULL,
    allocated_qty INT DEFAULT 0,
    picked_qty INT DEFAULT 0
);