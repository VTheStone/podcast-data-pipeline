"""
Validation script for Phase 3 — Diarization, Speaker Enrollment and Alignment.
Generates a comprehensive quality report.
"""

from loguru import logger
from sqlalchemy.orm import Session

from src.ingestion.database import (
    Episode,
    Chunk,
    Speaker,
    TranscriptionSegment,
    get_engine,
)


def validate_coverage(session: Session) -> dict:
    """Validates diarization coverage against transcribed episodes."""
    total_transcribed = session.query(Episode).filter(
        Episode.transcribed == True
    ).count()
    total_diarized = session.query(Episode).filter(
        Episode.diarized == True
    ).count()
    pending = session.query(Episode).filter(
        Episode.transcribed == True,
        Episode.diarized == False,
    ).count()

    return {
        "total_transcribed": total_transcribed,
        "total_diarized": total_diarized,
        "pending_diarization": pending,
        "coverage_pct": round(total_diarized / total_transcribed * 100, 1) if total_transcribed else 0,
    }


def validate_diarization_quality(session: Session) -> dict:
    """Validates diarization quality metrics."""
    diarized_episodes = session.query(Episode).filter(
        Episode.diarized == True
    ).all()

    if not diarized_episodes:
        return {}

    speakers_per_episode = []
    chunks_per_episode = []

    for ep in diarized_episodes:
        chunks = session.query(Chunk).filter(Chunk.episode_id == ep.id).all()
        if not chunks:
            continue
        speakers = set(c.speaker for c in chunks)
        speakers_per_episode.append(len(speakers))
        chunks_per_episode.append(len(chunks))

    if not speakers_per_episode:
        return {}

    return {
        "avg_speakers_per_episode": round(sum(speakers_per_episode) / len(speakers_per_episode), 1),
        "min_speakers": min(speakers_per_episode),
        "max_speakers": max(speakers_per_episode),
        "avg_chunks_per_episode": round(sum(chunks_per_episode) / len(chunks_per_episode)),
        "total_chunks": sum(chunks_per_episode),
    }


def validate_alignment(session: Session) -> dict:
    """Validates alignment of transcription with diarization."""
    diarized_episodes = session.query(Episode).filter(
        Episode.diarized == True
    ).all()

    if not diarized_episodes:
        return {}

    aligned_episodes = 0
    total_chunks = 0
    chunks_with_text = 0

    for ep in diarized_episodes:
        ep_total = session.query(Chunk).filter(Chunk.episode_id == ep.id).count()
        ep_with_text = session.query(Chunk).filter(
            Chunk.episode_id == ep.id,
            Chunk.text != None,
        ).count()

        if ep_with_text > 0:
            aligned_episodes += 1

        total_chunks += ep_total
        chunks_with_text += ep_with_text

    return {
        "aligned_episodes": aligned_episodes,
        "total_chunks": total_chunks,
        "chunks_with_text": chunks_with_text,
        "alignment_rate": round(chunks_with_text / total_chunks * 100, 1) if total_chunks else 0,
    }


def validate_speakers(session: Session) -> dict:
    """Validates identified speakers."""
    total_speakers = session.query(Speaker).count()
    hosts = session.query(Speaker).filter(Speaker.is_host == True).all()
    guests = session.query(Speaker).filter(Speaker.is_host == False).all()

    return {
        "total_speakers": total_speakers,
        "total_hosts": len(hosts),
        "total_guests": len(guests),
        "host_names": [s.name for s in hosts],
        "guest_names": [s.name for s in guests],
    }


def print_report(
    coverage: dict,
    diarization: dict,
    alignment: dict,
    speakers: dict,
) -> None:
    """Prints formatted validation report."""
    logger.info("=" * 50)
    logger.info("PHASE 3 VALIDATION REPORT")
    logger.info("=" * 50)

    logger.info("--- Coverage ---")
    logger.info(f"Total transcribed: {coverage['total_transcribed']}")
    logger.info(f"Total diarized: {coverage['total_diarized']}")
    logger.info(f"Pending diarization: {coverage['pending_diarization']}")
    logger.info(f"Diarization coverage: {coverage['coverage_pct']}%")

    if diarization:
        logger.info("--- Diarization Quality ---")
        logger.info(f"Avg speakers per episode: {diarization['avg_speakers_per_episode']}")
        logger.info(f"Min speakers: {diarization['min_speakers']}")
        logger.info(f"Max speakers: {diarization['max_speakers']}")
        logger.info(f"Avg chunks per episode: {diarization['avg_chunks_per_episode']}")
        logger.info(f"Total chunks: {diarization['total_chunks']}")

    if alignment:
        logger.info("--- Alignment ---")
        logger.info(f"Aligned episodes: {alignment['aligned_episodes']}")
        logger.info(f"Total chunks: {alignment['total_chunks']}")
        logger.info(f"Chunks with text: {alignment['chunks_with_text']}")
        logger.info(f"Alignment rate: {alignment['alignment_rate']}%")

    logger.info("--- Speakers ---")
    logger.info(f"Total speakers identified: {speakers['total_speakers']}")
    logger.info(f"Hosts: {speakers['total_hosts']} → {speakers['host_names']}")
    logger.info(f"Guests: {speakers['total_guests']}")
    if speakers['guest_names']:
        for name in speakers['guest_names'][:5]:
            logger.info(f"  - {name}")

    logger.info("=" * 50)

    has_issues = (
        coverage['pending_diarization'] > 0 or
        speakers['total_speakers'] == 0
    )

    if has_issues:
        logger.warning("VALIDATION STATUS: ISSUES FOUND - review warnings above")
    else:
        logger.success("VALIDATION STATUS: ALL CHECKS PASSED")


def run():
    """Main entry point for the Phase 3 validator."""
    engine = get_engine()

    with Session(engine) as session:
        coverage = validate_coverage(session)
        diarization = validate_diarization_quality(session)
        alignment = validate_alignment(session)
        speakers = validate_speakers(session)

    print_report(coverage, diarization, alignment, speakers)


if __name__ == "__main__":
    run()