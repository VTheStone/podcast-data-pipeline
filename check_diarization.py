from sqlalchemy.orm import Session
from sqlalchemy import func

from src.ingestion.database import Episode, Chunk, get_engine

engine = get_engine()

with Session(engine) as session:
    eps = (
        session.query(Episode)
        .filter(Episode.diarized == True)
        .all()
    )

    print(f"Total diarized episodes: {len(eps)}")
    print()

    print(f"{'Title':<60} {'Duration':<10} {'Segments':<10} {'Speakers':<10}")
    print("-" * 100)

    for ep in eps:
        segments_count = (
            session.query(Chunk)
            .filter(Chunk.episode_id == ep.id)
            .count()
        )

        unique_speakers = (
            session.query(func.count(func.distinct(Chunk.speaker)))
            .filter(
                Chunk.episode_id == ep.id,
                Chunk.speaker.isnot(None),
            )
            .scalar()
        )

        dur_min = (ep.duration_seconds or 0) / 60

        print(
            f"{ep.title[:60]:<60} "
            f"{dur_min:>7.0f}min "
            f"{segments_count:<10} "
            f"{unique_speakers:<10}"
        )