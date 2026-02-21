from geoalchemy2.shape import from_shape
from shapely import wkb
from sqlalchemy.orm import Session

from app.modules.tickets.models import Office

OFFICES = [
    ( "Актау", "Актау, 17-й микрорайон 22, Kazakhstan", "0101000020E610000013807F4A95435240CAC51858C71B4940"),
    ( "Актобе", "Актобе, проспект Алии Молдагуловой 44, Kazakhstan", "0101000020E6100000C539EAE8B8924C404A97FE25A9244940"),
    ( "Алматы", "Алматы, проспект Аль-Фараби 77/7, Kazakhstan", "0101000020E6100000666A12BC2139534094C151F2EA984540"),
    ( "Астана", "Астана, улица Достык 16, Kazakhstan", "0101000020E6100000295DFA97A4DB51404240BE840A904940"),
    ( "Атырау", "Атырау, улица Студенческая 52, Kazakhstan", "0101000020E6100000B0C91AF510F149405036E50AEF8E4740"),
    ( "Караганда", "Караганда, проспект Нуркена Абдирова 12, Kazakhstan", "0101000020E6100000516B9A779C4A52404963B48EAAEA4840"),
    ( "Кокшетау", "Кокшетау, проспект Назарбаева 4/2, Kazakhstan", "0101000020E610000036C8242367595140878A71FE26A44A40"),
    ( "Костанай", "Костанай, проспект Аль-Фараби 65, Kazakhstan", "0101000020E6100000DD0C37E0F3CF4F40E5F21FD26F9B4A40"),
    ( "Кызылорда", "Кызылорда, улица Кунаева 4, Kazakhstan", "0101000020E6100000AD86C43D96605040695721E5276D4640"),
    ( "Павлодар", "Павлодар, улица Луговая 16, Kazakhstan", "0101000020E6100000E2AFC91AF50F5340587380608E824A40"),
    ( "Петропавловск", "Петропавловск, улица Букетова 31A, Kazakhstan", "0101000020E6100000FED478E9264951402B4D4A41B76F4B40"),
    ( "Тараз", "Тараз, улица Желтоксан 86, Kazakhstan", "0101000020E6100000289B728577D751403333333333734540"),
    ( "Уральск", "Уральск, улица Ескалиева 177, Kazakhstan", "0101000020E61000005036E50AEFAE49407D96E7C1DD9D4940"),
    ( "Усть-Каменогорск", "Усть-Каменогорск, улица Максима Горького 50, Kazakhstan", "0101000020E6100000C2FA3F87F9A6544033E197FA79FB4840"),
    ( "Шымкент", "Шымкент, улица Кунаева 59, Kazakhstan", "0101000020E6100000AD86C43D9665514050340F6091234540"),
]

def seed_offices(db: Session):

    for city, address, wkb_hex in OFFICES:

        existing = db.query(Office).filter_by(city=city).first()

        geom = wkb.loads(bytes.fromhex(wkb_hex))

        if existing:
            existing.address = address
            existing.location = from_shape(geom, srid=4326)
        else:
            office = Office(
                city=city,
                address=address,
                location=from_shape(geom, srid=4326)
            )
            db.add(office)

    db.commit()