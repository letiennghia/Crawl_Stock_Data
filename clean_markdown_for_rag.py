from __future__ import annotations

import argparse
import csv
import hashlib
import html
import random
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MARKDOWN_DIR = Path("data_lake/gold/markdown")
FALLBACK_MARKDOWN_DIR = Path("data_lake/gold/data/markdown")
DEFAULT_OUTPUT_DIR = Path("data_lake/gold/data/markdown_cleaned")

FRONT_MATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")

MOJIBAKE_MARKERS = ("Ã", "Â", "Ä", "áº", "á»", "Æ", "Ð", "ð", "�")
MOJIBAKE_CHARS = set(
    "ÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß"
    "âãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ�\x03\x1a"
)
ALLOWED_SYMBOLS = set(".,;:!?%()/-+&[]{}#_*\"'<>=")

LOW_VALUE_SECTION_KEYWORDS = (
    "muc luc",
    "table of contents",
    "cong bo thong tin",
    "information disclosure",
    "bao cao thuong nien",
    "annual report",
    "thu ngo",
    "loi mo dau",
    "thong diep",
    "chu tich hoi dong",
    "chairman",
    "tong giam doc",
    "ceo message",
    "giai thuong",
    "danh hieu",
    "award",
)

RAG_KEYWORDS = (
    "moi truong",
    "xa hoi",
    "nguoi lao dong",
    "phat trien ben vung",
    "quan tri",
    "hoi dong quan tri",
    "ban kiem soat",
    "rui ro",
    "kiem toan",
    "bao cao tai chinh",
    "tai chinh",
    "doanh thu",
    "loi nhuan",
    "co dong",
    "von dieu le",
    "nhan su",
    "cong dong",
    "nang luong",
    "nuoc",
    "khi thai",
    "chat thai",
    "an toan lao dong",
    "esg",
    "gri",
    "sustainability",
    "environment",
    "social",
    "governance",
    "risk",
    "employee",
    "financial",
)


@dataclass
class FileStats:
    source_path: Path
    full_clean_path: Path
    rag_clean_path: Path
    original_tokens: int
    full_clean_tokens: int
    rag_clean_tokens: int
    full_reduction_pct: float
    rag_reduction_pct: float
    chunks_total: int
    chunks_kept: int


def get_encoder(encoding_name: str):
    try:
        import tiktoken
    except ImportError:
        return None

    try:
        return tiktoken.get_encoding(encoding_name)
    except Exception:
        return None


def count_tokens(text: str, encoder) -> int:
    if encoder is not None:
        return len(encoder.encode(text))
    return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text.lower()


def normalize_for_match(text: str) -> str:
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def repair_mojibake(text: str) -> str:
    marker_count = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
    if marker_count < 20:
        return text

    candidates = [text]
    for encoding in ("latin1", "cp1252"):
        try:
            candidates.append(text.encode(encoding, errors="ignore").decode("utf-8", errors="ignore"))
        except UnicodeError:
            continue

    def badness(candidate: str) -> int:
        return sum(candidate.count(marker) for marker in MOJIBAKE_MARKERS)

    return min(candidates, key=badness)


def is_garbled_line(line: str) -> bool:
    content = line.strip().lstrip("#-*0123456789. ")
    if not content:
        return False

    bad_chars = sum(1 for char in content if char in MOJIBAKE_CHARS)
    weird_chars = sum(
        1
        for char in content
        if not (char.isalnum() or char.isspace() or char in ALLOWED_SYMBOLS)
    )
    alnum_count = sum(char.isalnum() for char in content)
    bad_ratio = (bad_chars + weird_chars) / max(len(content), 1)
    alnum_ratio = alnum_count / max(len(content), 1)

    return (len(content) <= 90 and bad_ratio > 0.20) or alnum_ratio < 0.35


def is_low_value_heading(line: str) -> tuple[bool, int]:
    match = HEADING_RE.match(line.strip())
    if not match:
        return False, 0

    level = len(match.group(1))
    heading_text = normalize_for_match(match.group(2))
    return any(keyword in heading_text for keyword in LOW_VALUE_SECTION_KEYWORDS), level


def remove_low_value_sections(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    skip_level: int | None = None

    for line in lines:
        heading_match = HEADING_RE.match(line.strip())
        if heading_match and skip_level is not None:
            current_level = len(heading_match.group(1))
            if current_level <= skip_level:
                skip_level = None

        should_skip, heading_level = is_low_value_heading(line)
        if should_skip:
            skip_level = heading_level
            continue

        if skip_level is None:
            kept.append(line)

    return "\n".join(kept)


def clean_table_block(lines: list[str]) -> list[str]:
    useful_rows: list[str] = []

    for line in lines:
        if TABLE_SEPARATOR_RE.match(line):
            continue

        cells = [re.sub(r"\s+", " ", cell.strip()) for cell in line.strip().strip("|").split("|")]
        cells = [cell for cell in cells if cell and cell not in ("-", "--")]
        if not cells:
            continue

        joined = " | ".join(cells)
        normalized = normalize_for_match(joined)
        if " " in joined and normalized.count(" ") >= 1:
            useful_rows.append("; ".join(dict.fromkeys(cells)))

    if not useful_rows:
        return []

    return ["Table:"] + [f"- {row}" for row in useful_rows]


def compact_tables(text: str) -> str:
    output: list[str] = []
    table_block: list[str] = []

    def flush_table() -> None:
        nonlocal table_block
        if table_block:
            output.extend(clean_table_block(table_block))
            table_block = []

    for line in text.splitlines():
        if "|" in line and line.count("|") >= 2:
            table_block.append(line)
        else:
            flush_table()
            output.append(line)

    flush_table()
    return "\n".join(output)


def dedupe_lines_and_paragraphs(text: str) -> str:
    lines_seen: dict[str, int] = {}
    deduped_lines: list[str] = []

    for line in text.splitlines():
        normalized = normalize_for_match(line)
        if not normalized:
            deduped_lines.append("")
            continue

        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
        lines_seen[digest] = lines_seen.get(digest, 0) + 1
        if lines_seen[digest] <= 2:
            deduped_lines.append(line)

    paragraphs_seen: set[str] = set()
    deduped_paragraphs: list[str] = []
    for paragraph in re.split(r"\n\s*\n", "\n".join(deduped_lines)):
        normalized = normalize_for_match(paragraph)
        if not normalized:
            continue

        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
        if digest in paragraphs_seen:
            continue

        paragraphs_seen.add(digest)
        deduped_paragraphs.append(paragraph.strip())

    return "\n\n".join(deduped_paragraphs)


def full_clean(text: str, *, repair_encoding: bool) -> str:
    if repair_encoding:
        text = repair_mojibake(text)

    text = FRONT_MATTER_RE.sub("", text)
    text = HTML_COMMENT_RE.sub("", text)
    text = MD_IMAGE_RE.sub("", text)
    text = MD_LINK_RE.sub(r"\1", text)
    text = html.unescape(text)
    text = remove_low_value_sections(text)
    text = compact_tables(text)

    cleaned_lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if not line:
            cleaned_lines.append("")
            continue
        if re.fullmatch(r"[-–—_*.\s]{3,}", line):
            continue
        if re.fullmatch(r"\d{1,4}", line):
            continue
        if is_garbled_line(line):
            continue
        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return dedupe_lines_and_paragraphs(text).strip() + "\n"


def split_chunks(text: str, encoder, chunk_token_limit: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for paragraph in paragraphs:
        paragraph_tokens = count_tokens(paragraph, encoder)
        if current and current_tokens + paragraph_tokens > chunk_token_limit:
            chunks.append("\n\n".join(current))
            current = []
            current_tokens = 0

        current.append(paragraph)
        current_tokens += paragraph_tokens

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def chunk_score(chunk: str) -> float:
    normalized = normalize_for_match(chunk)
    if not normalized:
        return 0.0

    keyword_hits = sum(1 for keyword in RAG_KEYWORDS if keyword in normalized)
    digit_ratio = sum(char.isdigit() for char in chunk) / max(len(chunk), 1)
    table_bonus = 1.0 if "Table:" in chunk else 0.0
    heading_bonus = 0.5 if re.search(r"^#{1,6}\s+", chunk, flags=re.MULTILINE) else 0.0
    noise_penalty = 2.0 if is_garbled_line(chunk[:200]) else 0.0
    too_short_penalty = 1.0 if len(normalized.split()) < 30 else 0.0

    return keyword_hits + min(digit_ratio * 10, 2.0) + table_bonus + heading_bonus - noise_penalty - too_short_penalty


def rag_clean(text: str, encoder, chunk_token_limit: int, min_score: float) -> tuple[str, int, int]:
    chunks = split_chunks(text, encoder, chunk_token_limit)
    if not chunks:
        return "", 0, 0

    scored = [(chunk_score(chunk), index, chunk) for index, chunk in enumerate(chunks)]
    kept = [(index, chunk) for score, index, chunk in scored if score >= min_score]

    if not kept:
        top_count = max(1, min(3, len(scored)))
        kept = [(index, chunk) for _, index, chunk in sorted(scored, reverse=True)[:top_count]]

    kept.sort(key=lambda item: item[0])
    return "\n\n---\n\n".join(chunk for _, chunk in kept).strip() + "\n", len(chunks), len(kept)


def resolve_markdown_dir(path: Path) -> Path:
    if path.exists():
        return path
    if path == DEFAULT_MARKDOWN_DIR and FALLBACK_MARKDOWN_DIR.exists():
        return FALLBACK_MARKDOWN_DIR
    raise FileNotFoundError(f"Markdown directory not found: {path}")


def select_files(root: Path, sample_size: int, seed: int, process_all: bool) -> list[Path]:
    files = sorted(root.rglob("*.md"))
    if not files:
        raise FileNotFoundError(f"No markdown files found in: {root}")
    if process_all or sample_size >= len(files):
        return files
    rng = random.Random(seed)
    return sorted(rng.sample(files, sample_size))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def process_file(
    source_path: Path,
    source_root: Path,
    output_root: Path,
    encoder,
    chunk_token_limit: int,
    min_score: float,
    repair_encoding: bool,
) -> FileStats:
    original_text = source_path.read_text(encoding="utf-8", errors="ignore")
    clean_text = full_clean(original_text, repair_encoding=repair_encoding)
    rag_text, chunks_total, chunks_kept = rag_clean(
        clean_text,
        encoder,
        chunk_token_limit,
        min_score,
    )

    relative_path = source_path.relative_to(source_root)
    full_clean_path = output_root / "full_clean" / relative_path
    rag_clean_path = output_root / "rag_clean" / relative_path
    write_text(full_clean_path, clean_text)
    write_text(rag_clean_path, rag_text)

    original_tokens = count_tokens(original_text, encoder)
    full_clean_tokens = count_tokens(clean_text, encoder)
    rag_clean_tokens = count_tokens(rag_text, encoder)

    return FileStats(
        source_path=source_path,
        full_clean_path=full_clean_path,
        rag_clean_path=rag_clean_path,
        original_tokens=original_tokens,
        full_clean_tokens=full_clean_tokens,
        rag_clean_tokens=rag_clean_tokens,
        full_reduction_pct=(original_tokens - full_clean_tokens) / max(original_tokens, 1) * 100,
        rag_reduction_pct=(original_tokens - rag_clean_tokens) / max(original_tokens, 1) * 100,
        chunks_total=chunks_total,
        chunks_kept=chunks_kept,
    )


def write_stats(output_root: Path, stats: list[FileStats]) -> Path:
    stats_path = output_root / "token_stats.csv"
    output_root.mkdir(parents=True, exist_ok=True)
    with stats_path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=[
                "source_path",
                "full_clean_path",
                "rag_clean_path",
                "original_tokens",
                "full_clean_tokens",
                "rag_clean_tokens",
                "full_reduction_pct",
                "rag_reduction_pct",
                "chunks_total",
                "chunks_kept",
            ],
        )
        writer.writeheader()
        for row in stats:
            writer.writerow(
                {
                    "source_path": row.source_path,
                    "full_clean_path": row.full_clean_path,
                    "rag_clean_path": row.rag_clean_path,
                    "original_tokens": row.original_tokens,
                    "full_clean_tokens": row.full_clean_tokens,
                    "rag_clean_tokens": row.rag_clean_tokens,
                    "full_reduction_pct": f"{row.full_reduction_pct:.2f}",
                    "rag_reduction_pct": f"{row.rag_reduction_pct:.2f}",
                    "chunks_total": row.chunks_total,
                    "chunks_kept": row.chunks_kept,
                }
            )
    return stats_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean markdown files and create compact RAG-ready copies."
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_MARKDOWN_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--all", action="store_true", help="Process every markdown file.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--encoding", default="cl100k_base")
    parser.add_argument("--chunk-token-limit", type=int, default=900)
    parser.add_argument("--min-score", type=float, default=2.0)
    parser.add_argument(
        "--no-repair-mojibake",
        action="store_true",
        help="Disable mojibake repair before cleanup.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.all and args.sample_size <= 0:
        raise ValueError("--sample-size must be greater than 0 unless --all is set")

    source_root = resolve_markdown_dir(args.source_dir)
    encoder = get_encoder(args.encoding)
    files = select_files(source_root, args.sample_size, args.seed, args.all)
    stats = [
        process_file(
            source_path=file_path,
            source_root=source_root,
            output_root=args.output_dir,
            encoder=encoder,
            chunk_token_limit=args.chunk_token_limit,
            min_score=args.min_score,
            repair_encoding=not args.no_repair_mojibake,
        )
        for file_path in files
    ]
    stats_path = write_stats(args.output_dir, stats)

    original_total = sum(row.original_tokens for row in stats)
    full_total = sum(row.full_clean_tokens for row in stats)
    rag_total = sum(row.rag_clean_tokens for row in stats)
    tokenizer_name = args.encoding if encoder is not None else "regex fallback"

    print(f"Source dir: {source_root}")
    print(f"Output dir: {args.output_dir}")
    print(f"Tokenizer: {tokenizer_name}")
    print(f"Files processed: {len(stats)}")
    print(f"Original tokens: {original_total:,}")
    print(f"Full-clean tokens: {full_total:,} ({(original_total - full_total) / max(original_total, 1) * 100:.2f}% reduction)")
    print(f"RAG-clean tokens: {rag_total:,} ({(original_total - rag_total) / max(original_total, 1) * 100:.2f}% reduction)")
    print(f"Stats CSV: {stats_path}")

    if encoder is None:
        print("Note: install/cache tiktoken encoding for model-style token counts.")


if __name__ == "__main__":
    main()
