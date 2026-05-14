CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TABLE venues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(50) DEFAULT 'US',
    capacity INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER trg_venues_updated_at BEFORE UPDATE ON venues FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE artists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    genre VARCHAR(100),
    bio TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER trg_artists_updated_at BEFORE UPDATE ON artists FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    venue_id INTEGER REFERENCES venues(id),
    event_date TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER trg_events_updated_at BEFORE UPDATE ON events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE event_artists (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
    artist_id INTEGER REFERENCES artists(id),
    performance_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sections (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    capacity INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER trg_sections_updated_at BEFORE UPDATE ON sections FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER trg_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(12,2),
    status VARCHAR(20) DEFAULT 'pending',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER trg_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES sections(id),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO venues (name, city, state, country, capacity) VALUES
('Madison Square Garden', 'New York', 'NY', 'US', 20789),
('Staples Center', 'Los Angeles', 'CA', 'US', 19060),
('The O2 Arena', 'London', NULL, 'UK', 20000),
('Nippon Budokan', 'Tokyo', NULL, 'JP', 14471);

INSERT INTO artists (name, genre, bio) VALUES
('The Cosmic Beats', 'Electronic', 'A five-piece electronic band from Berlin'),
('Sarah Vaughan Jr.', 'Jazz', 'Contemporary jazz vocalist with a modern twist'),
('Los Amigos', 'Latin', 'High-energy Latin fusion band'),
('The Quantum Quartet', 'Classical', 'Award-winning string quartet');

INSERT INTO events (title, venue_id, event_date, status, description) VALUES
('Electronic Nights 2026', 1, '2026-08-15 20:00:00', 'scheduled', 'A night of electronic music featuring top artists'),
('Jazz Under the Stars', 2, '2026-09-20 19:30:00', 'scheduled', 'An evening of smooth jazz'),
('Latin Fiesta', 3, '2026-07-10 21:00:00', 'scheduled', 'Latin music festival'),
('Classical Masterpieces', 4, '2026-10-05 18:00:00', 'scheduled', 'Evening of classical masterpieces');

INSERT INTO event_artists (event_id, artist_id, performance_order) VALUES
(1, 1, 1),
(2, 2, 1),
(3, 3, 1),
(4, 4, 1);

INSERT INTO sections (event_id, name, price, capacity) VALUES
(1, 'VIP', 250.00, 500),
(1, 'General Admission', 89.00, 5000),
(1, 'Balcony', 150.00, 1000),
(2, 'VIP', 200.00, 300),
(2, 'General Admission', 75.00, 4000),
(3, 'VIP', 180.00, 400),
(3, 'General Admission', 65.00, 6000),
(4, 'VIP', 300.00, 200),
(4, 'General Admission', 100.00, 3000);

INSERT INTO customers (name, email, phone) VALUES
('John Doe', 'john@example.com', '+1-555-0101'),
('Jane Smith', 'jane@example.com', '+1-555-0102'),
('Bob Wilson', 'bob@example.com', '+1-555-0103');
