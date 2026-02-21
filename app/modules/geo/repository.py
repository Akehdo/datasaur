from sqlalchemy import text

def find_nearest_office(db, lat: float, lon: float):
    sql = text("""
        SELECT city, address,
               ST_Distance(
                 location::geography,
                 ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) / 1000 AS distance_km
        FROM offices
        ORDER BY distance_km ASC
        LIMIT 1;
    """)
    return db.execute(sql, {"lat": lat, "lon": lon}).fetchone()