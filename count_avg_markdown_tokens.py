from __future__ import annotations

import argparse
import html
import random
import re
from pathlib import Path


DEFAULT_MARKDOWN_DIR = Path("data_lake/gold/markdown")
FALLBACK_MARKDOWN_DIR = Path("data_lake/gold/data/markdown")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
FRONT_MATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)


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

    # Fallback when tiktoken is not installed: count words, numbers, and symbols.
    return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))


def clean_basic(text: str) -> str:
    text = FRONT_MATTER_RE.sub("", text)
    text = HTML_COMMENT_RE.sub("", text)
    text = MD_IMAGE_RE.sub("", text)
    text = MD_LINK_RE.sub(r"\1", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def garbled_score(line: str) -> float:
    if not line:
        return 0.0

    mojibake_chars = set(
        "ÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß"
        "âãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ�\x03\x1a"
    )
    bad_chars = sum(1 for char in line if char in mojibake_chars)
    allowed_symbols = set(".,;:!?%()/-+&[]{}#_*\"'")
    weird_chars = sum(
        1
        for char in line
        if not (char.isalnum() or char.isspace() or char in allowed_symbols)
    )
    return (bad_chars + weird_chars) / len(line)


def clean_noise(text: str) -> str:
    text = clean_basic(text)
    cleaned_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue

        content = stripped.lstrip("#-*0123456789. ")
        if len(content) <= 80 and garbled_score(content) > 0.22:
            continue

        alnum_count = sum(char.isalnum() for char in content)
        if content and alnum_count / len(content) < 0.35:
            continue

        cleaned_lines.append(line)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned_lines)).strip()


def resolve_markdown_dir(path: Path) -> Path:
    if path.exists():
        return path

    if path == DEFAULT_MARKDOWN_DIR and FALLBACK_MARKDOWN_DIR.exists():
        return FALLBACK_MARKDOWN_DIR

    raise FileNotFoundError(f"Markdown directory not found: {path}")


def sample_markdown_files(markdown_dir: Path, sample_size: int, seed: int) -> list[Path]:
    files = sorted(markdown_dir.rglob("*.md"))
    if not files:
        raise FileNotFoundError(f"No markdown files found in: {markdown_dir}")

    rng = random.Random(seed)
    if len(files) <= sample_size:
        return files

    return sorted(rng.sample(files, sample_size))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count average tokens per markdown file from a sample."
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_MARKDOWN_DIR,
        help=f"Markdown root directory. Default: {DEFAULT_MARKDOWN_DIR}",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="Number of markdown files to sample. Default: 20",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling. Default: 42",
    )
    parser.add_argument(
        "--encoding",
        default="cl100k_base",
        help="tiktoken encoding name if tiktoken is installed. Default: cl100k_base",
    )
    parser.add_argument(
        "--compare-clean",
        action="store_true",
        help="Compare original tokens with basic cleanup and OCR-noise cleanup.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.sample_size <= 0:
        raise ValueError("--sample-size must be greater than 0")

    markdown_dir = resolve_markdown_dir(args.dir)
    encoder = get_encoder(args.encoding)
    sampled_files = sample_markdown_files(markdown_dir, args.sample_size, args.seed)

    rows: list[tuple[Path, int, int, int]] = []
    for file_path in sampled_files:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        original_tokens = count_tokens(text, encoder)
        basic_tokens = count_tokens(clean_basic(text), encoder)
        noise_tokens = count_tokens(clean_noise(text), encoder)
        rows.append((file_path, original_tokens, basic_tokens, noise_tokens))

    total_tokens = sum(original_tokens for _, original_tokens, _, _ in rows)
    average_tokens = total_tokens / len(rows)
    tokenizer_name = args.encoding if encoder is not None else "regex fallback"

    print(f"Markdown dir: {markdown_dir}")
    print(f"Tokenizer: {tokenizer_name}")
    print(f"Sample size: {len(rows)}")
    print(f"Total tokens: {total_tokens:,}")
    print(f"Average tokens/file: {average_tokens:,.2f}")

    if args.compare_clean:
        basic_total = sum(basic_tokens for _, _, basic_tokens, _ in rows)
        noise_total = sum(noise_tokens for _, _, _, noise_tokens in rows)
        basic_reduction = (total_tokens - basic_total) / total_tokens * 100
        noise_reduction = (total_tokens - noise_total) / total_tokens * 100

        print()
        print("Cleanup comparison:")
        print(
            f"Basic cleanup: {basic_total:,} tokens "
            f"({basic_reduction:.2f}% reduction)"
        )
        print(
            f"OCR-noise cleanup: {noise_total:,} tokens "
            f"({noise_reduction:.2f}% reduction)"
        )

    print()
    print("Files:")
    for file_path, original_tokens, basic_tokens, noise_tokens in rows:
        if args.compare_clean:
            basic_reduction = (original_tokens - basic_tokens) / original_tokens * 100
            noise_reduction = (original_tokens - noise_tokens) / original_tokens * 100
            print(
                f"{original_tokens:>10,}  "
                f"basic -{basic_reduction:>5.1f}%  "
                f"noise -{noise_reduction:>5.1f}%  {file_path}"
            )
        else:
            print(f"{original_tokens:>10,}  {file_path}")

    if encoder is None:
        print()
        print("Note: install tiktoken for model-style token counts.")


if __name__ == "__main__":
    main()
