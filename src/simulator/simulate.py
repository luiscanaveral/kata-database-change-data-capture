import os
import random
import time
import logging
from datetime import datetime, timedelta
import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cdc-simulator')

DB_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
DB_NAME = os.environ.get('POSTGRES_DB', 'ticketdb')
DB_USER = os.environ.get('POSTGRES_USER', 'postgres')
DB_PASS = os.environ.get('POSTGRES_PASSWORD', 'postgres')

VENUE_NAMES = [
    'The Forum', 'Wembley Stadium', 'Red Rocks Amphitheatre', 'Sydney Opera House',
    'Hollywood Bowl', 'Royal Albert Hall', 'Barclays Center', 'United Center',
]
CITIES = ['New York', 'Los Angeles', 'London', 'Tokyo', 'Sydney', 'Berlin', 'Paris', 'Chicago',
          'San Francisco', 'Miami', 'Denver', 'Nashville']
STATES = ['NY', 'CA', 'IL', 'FL', 'CO', 'TN', 'TX', 'WA', 'MA', 'GA']
COUNTRIES = ['US', 'UK', 'JP', 'AU', 'DE', 'FR']

GENRE_ARTIST_PAIRS = [
    ('The Crimson Rays', 'Rock'), ('Luna Eclipse', 'Pop'), ('Delta Blues Band', 'Blues'),
    ('Neon Pulse', 'Electronic'), ('Atlas & The Argonauts', 'Indie'), ('Veridian', 'Alternative'),
    ('The Midnight Howlers', 'Rock'), ('Saffron Dreams', 'R&B'), ('Cascade', 'Electronic'),
    ('The Ivory Keys', 'Classical'), ('Bronze Horizon', 'Metal'), ('Azure Waves', 'Ambient'),
    ('Phantom Strings', 'Folk'), ('Gilded Saints', 'Folk'), ('Obsidian Veil', 'Metal'),
    ('Solar Flare', 'Electronic'), ('The Velvet Underground', 'Rock'), ('Misty Morning', 'Jazz'),
    ('Thunderstrike', 'Metal'), ('Crimson Tide', 'Rock'),
]

EVENT_TEMPLATES = [
    'Summer Music Festival', 'Rock Revolution Tour', 'Jazz & Blues Night',
    'Electronic Beats Extravaganza', 'Classical Gala Evening', 'Indie Showcase',
    'Global Rhythms Festival', 'Acoustic Sessions', 'Neon Nights',
    'Heritage Music Concert', 'Symphony Under the Stars', 'Urban Beats Festival',
    'Alternative Sounds', 'Metal Mayhem', 'R&B Soul Night',
]

SECTION_NAMES = ['VIP', 'General Admission', 'Balcony', 'Floor', 'Premium Seating']

FIRST_NAMES = ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank', 'Grace', 'Henry',
               'Iris', 'Jack', 'Kate', 'Leo', 'Mia', 'Noah', 'Olivia', 'Peter']
LAST_NAMES = ['Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
              'Rodriguez', 'Martinez', 'Anderson', 'Taylor', 'Thomas', 'Moore', 'Jackson']


def connect():
    conn = psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )
    conn.autocommit = True
    return conn


def pick_one(cur, table):
    cur.execute(f"SELECT id FROM {table} ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else None


def random_phone():
    return f'+1-555-{random.randint(1000, 9999)}'


def simulate():
    conn = connect()
    cur = conn.cursor()
    logger.info("Simulator started — generating ticket platform activity every 15s")

    while True:
        try:
            action = random.choices(
                ['new_venue', 'new_artist', 'new_event', 'new_customer',
                 'new_order', 'update_order', 'update_event'],
                weights=[5, 10, 15, 20, 25, 15, 10],
            )[0]

            if action == 'new_venue':
                name = random.choice(VENUE_NAMES)
                city = random.choice(CITIES)
                state = random.choice(STATES) if random.random() < 0.7 else None
                country = random.choice(COUNTRIES)
                capacity = random.randint(2000, 80000)
                cur.execute(
                    "INSERT INTO venues (name, city, state, country, capacity) VALUES (%s, %s, %s, %s, %s)",
                    (f"{name} #{random.randint(1, 999)}", city, state, country, capacity),
                )
                logger.info(f"Venue created: {name} in {city}")

            elif action == 'new_artist':
                name, genre = random.choice(GENRE_ARTIST_PAIRS)
                cur.execute(
                    "INSERT INTO artists (name, genre, bio) VALUES (%s, %s, %s)",
                    (f"{name} #{random.randint(1, 99):02d}", genre,
                     f"{name} is a {genre.lower()} act known for electrifying performances."),
                )
                logger.info(f"Artist created: {name} ({genre})")

            elif action == 'new_event':
                venue_id = pick_one(cur, 'venues')
                if not venue_id:
                    continue
                title = random.choice(EVENT_TEMPLATES)
                event_date = datetime.now() + timedelta(days=random.randint(1, 365))
                cur.execute(
                    "INSERT INTO events (title, venue_id, event_date, status) VALUES (%s, %s, %s, 'scheduled') RETURNING id",
                    (title, venue_id, event_date),
                )
                event_id = cur.fetchone()[0]

                num_sections = random.randint(2, 4)
                chosen_sections = random.sample(SECTION_NAMES, num_sections)
                for sname in chosen_sections:
                    price = round(random.uniform(30, 400), 2)
                    cap = random.randint(100, 5000)
                    cur.execute(
                        "INSERT INTO sections (event_id, name, price, capacity) VALUES (%s, %s, %s, %s)",
                        (event_id, sname, price, cap),
                    )

                artist_id = pick_one(cur, 'artists')
                if artist_id:
                    cur.execute(
                        "INSERT INTO event_artists (event_id, artist_id, performance_order) VALUES (%s, %s, %s)",
                        (event_id, artist_id, 1),
                    )

                logger.info(f"Event created: {title} (venue #{venue_id}) with {num_sections} sections")

            elif action == 'new_customer':
                first = random.choice(FIRST_NAMES)
                last = random.choice(LAST_NAMES)
                email = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@example.com"
                cur.execute(
                    "INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)",
                    (f"{first} {last}", email, random_phone()),
                )
                logger.info(f"Customer created: {first} {last}")

            elif action == 'new_order':
                customer_id = pick_one(cur, 'customers')
                if not customer_id:
                    continue
                cur.execute("""
                    SELECT s.id, s.name, s.price
                    FROM sections s
                    JOIN events e ON e.id = s.event_id
                    WHERE e.status = 'scheduled'
                    ORDER BY RANDOM() LIMIT 1
                """)
                section = cur.fetchone()
                if not section:
                    continue

                qty = random.randint(1, 4)
                total = round(float(section[2]) * qty, 2)

                cur.execute(
                    "INSERT INTO orders (customer_id, total_amount, status) VALUES (%s, %s, 'pending') RETURNING id",
                    (customer_id, total),
                )
                order_id = cur.fetchone()[0]

                cur.execute(
                    "INSERT INTO order_items (order_id, section_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                    (order_id, section[0], qty, section[2]),
                )
                logger.info(f"Order #{order_id}: {qty}x {section[1]} @ ${float(section[2]):.2f} = ${total:.2f}")

            elif action == 'update_order':
                cur.execute("SELECT id, status FROM orders WHERE status = 'pending' ORDER BY RANDOM() LIMIT 1")
                order = cur.fetchone()
                if order:
                    new_status = random.choice(['confirmed', 'completed', 'cancelled'])
                    cur.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order[0]))
                    logger.info(f"Order #{order[0]}: {order[1]} -> {new_status}")

            elif action == 'update_event':
                cur.execute("SELECT id, title FROM events WHERE status = 'scheduled' ORDER BY RANDOM() LIMIT 1")
                event = cur.fetchone()
                if event:
                    new_status = random.choice(['sold_out', 'postponed', 'rescheduled'])
                    cur.execute("UPDATE events SET status = %s WHERE id = %s", (new_status, event[0]))
                    logger.info(f"Event '{event[1]}' (id={event[0]}): scheduled -> {new_status}")

            time.sleep(15)

        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(5)
            try:
                conn = connect()
                cur = conn.cursor()
            except Exception as conn_err:
                logger.error(f"Reconnect failed: {conn_err}")


if __name__ == '__main__':
    simulate()
