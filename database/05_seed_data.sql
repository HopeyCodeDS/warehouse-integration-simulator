-- 1. ERP SEED DATA
INSERT INTO erp.products (sku, name, description) VALUES
('P100', 'Engine Block', 'Standard V6 engine block'),
('P200', 'Transmission Assembly', 'Automatic transmission unit'),
('P300', 'Brake Pad Set', 'Set of 4 ceramic brake pads');

-- 2. WMS SEED DATA
INSERT INTO wms.locations (name, type) VALUES
('Rack-A1', 'rack'), ('Rack-A2', 'rack'), ('Rack-B1', 'rack'),
('Dock-1', 'dock'), ('Dock-2', 'dock'), ('Dock-3', 'dock'),
('Conveyor-1', 'conveyor'), ('Conveyor-2', 'conveyor'), ('Staging-A', 'staging');

INSERT INTO wms.inventory (product_sku, location_id, quantity)
SELECT 'P100', id, 50 FROM wms.locations WHERE name = 'Rack-A1' UNION ALL
SELECT 'P200', id, 30 FROM wms.locations WHERE name = 'Rack-A2' UNION ALL
SELECT 'P300', id, 100 FROM wms.locations WHERE name = 'Rack-B1';

-- 3. EQUIPMENT CONFIGURATION SEED DATA
INSERT INTO wms.equipment (name, type, protocol, ip_address, enabled) VALUES
('Conveyor-1', 'conveyor', 'OPCUA', '192.168.1.10', TRUE),
('Robot-AMR-Ultra', 'robot', 'MQTT', '192.168.1.20', TRUE),
('Dock-3-Sensor', 'sensor', 'OPCUA', '192.168.1.30', TRUE);

INSERT INTO wms.equipment_parameters (equipment_id, parameter, value)
SELECT id, 'speed', '0.8' FROM wms.equipment WHERE name = 'Conveyor-1' UNION ALL
SELECT id, 'direction', 'forward' FROM wms.equipment WHERE name = 'Conveyor-1' UNION ALL
SELECT id, 'battery_limit', '20' FROM wms.equipment WHERE name = 'Robot-AMR-Ultra';