from sqlalchemy.orm import Session
from sqlalchemy import text

OFFICES = [
    (1, "Актау", "Актау, 17-й микрорайон 22, Kazakhstan", "0101000020E610000013807F4A95435240CAC51858C71B4940"),
    (2, "Актобе", "Актобе, проспект Алии Молдагуловой 44, Kazakhstan", "0101000020E6100000C539EAE8B8924C404A97FE25A9244940"),
    (3, "Алматы", "Алматы, проспект Аль-Фараби 77/7, Kazakhstan", "0101000020E6100000666A12BC2139534094C151F2EA984540"),
    (4, "Астана", "Астана, улица Достык 16, Kazakhstan", "0101000020E6100000295DFA97A4DB51404240BE840A904940"),
    (5, "Атырау", "Атырау, улица Студенческая 52, Kazakhstan", "0101000020E6100000B0C91AF510F149405036E50AEF8E4740"),
    (6, "Караганда", "Караганда, проспект Нуркена Абдирова 12, Kazakhstan", "0101000020E6100000516B9A779C4A52404963B48EAAEA4840"),
    (7, "Кокшетау", "Кокшетау, проспект Назарбаева 4/2, Kazakhstan", "0101000020E610000036C8242367595140878A71FE26A44A40"),
    (8, "Костанай", "Костанай, проспект Аль-Фараби 65, Kazakhstan", "0101000020E6100000DD0C37E0F3CF4F40E5F21FD26F9B4A40"),
    (9, "Кызылорда", "Кызылорда, улица Кунаева 4, Kazakhstan", "0101000020E6100000AD86C43D96605040695721E5276D4640"),
    (10, "Павлодар", "Павлодар, улица Луговая 16, Kazakhstan", "0101000020E6100000E2AFC91AF50F5340587380608E824A40"),
    (11, "Петропавловск", "Петропавловск, улица Букетова 31A, Kazakhstan", "0101000020E6100000FED478E9264951402B4D4A41B76F4B40"),
    (12, "Тараз", "Тараз, улица Желтоксан 86, Kazakhstan", "0101000020E6100000289B728577D751403333333333734540"),
    (13, "Уральск", "Уральск, улица Ескалиева 177, Kazakhstan", "0101000020E61000005036E50AEFAE49407D96E7C1DD9D4940"),
    (14, "Усть-Каменогорск", "Усть-Каменогорск, улица Максима Горького 50, Kazakhstan", "0101000020E6100000C2FA3F87F9A6544033E197FA79FB4840"),
    (15, "Шымкент", "Шымкент, улица Кунаева 59, Kazakhstan", "0101000020E6100000AD86C43D9665514050340F6091234540"),
]

def seed_offices(db: Session):

    db.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))

    db.execute(text("""
        CREATE TABLE IF NOT EXISTS offices (
            id INTEGER PRIMARY KEY,
            city VARCHAR(120) UNIQUE NOT NULL,
            address VARCHAR(255) NOT NULL,
            location geography(POINT, 4326) NOT NULL
        );
    """))

    for id_, city, address, wkb in OFFICES:
        db.execute(text("""
            INSERT INTO offices (id, city, address, location)
            VALUES (:id, :city, :address, ST_GeogFromWKB(decode(:wkb, 'hex')))
            ON CONFLICT (id) DO UPDATE
            SET city = EXCLUDED.city,
                address = EXCLUDED.address,
                location = EXCLUDED.location;
        """), {
            "id": id_,
            "city": city,
            "address": address,
            "wkb": wkb
        })

    db.commit()