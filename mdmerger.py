from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Literal

__all__ = ["merge"]


def _collect_files(
	input_dir: str | Path,
	suffix: str,
	recursive: bool = True,
	exclude_path: str | Path | None = None,
) -> list[Path]:
	"""Collect files by suffix with deterministic path ordering."""
	root = Path(input_dir)
	if not root.exists() or not root.is_dir():
		raise FileNotFoundError(f"Input directory does not exist: {root}")

	pattern = f"**/*{suffix}" if recursive else f"*{suffix}"
	files = [p for p in root.glob(pattern) if p.is_file()]

	if exclude_path is not None:
		excluded = Path(exclude_path).resolve()
		files = [p for p in files if p.resolve() != excluded]

	return sorted(files, key=lambda p: str(p.as_posix()).lower())


def _merge_markdown_files(
	input_dir: str | Path,
	output_file: str | Path,
	recursive: bool = True,
	add_file_headers: bool = True,
	separator: str = "\n\n---\n\n",
	encoding: str = "utf-8",
) -> Path:
	"""
	Combine all .md files under input_dir into one Markdown file.

	Returns the output file path.
	"""
	output_path = Path(output_file)
	md_files = _collect_files(
		input_dir=input_dir,
		suffix=".md",
		recursive=recursive,
		exclude_path=output_path,
	)

	if not md_files:
		raise ValueError("No Markdown files found to combine.")

	chunks: list[str] = []
	for file_path in md_files:
		content = file_path.read_text(encoding=encoding)
		if add_file_headers:
			header = f"# Source: {file_path.as_posix()}"
			chunks.append(f"{header}\n\n{content.strip()}")
		else:
			chunks.append(content.strip())

	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(separator.join(chunks).strip() + "\n", encoding=encoding)
	return output_path


def _merge_json_files(
	input_dir: str | Path,
	output_file: str | Path,
	recursive: bool = True,
	flatten_lists: bool = False,
	encoding: str = "utf-8",
) -> Path:
	"""
	Combine all .json files under input_dir into one JSON array file.

	Output format:
	- Default: [{"source_file": "...", "data": <parsed_json>}, ...]
	- If flatten_lists=True and a file contains a top-level list, each item is expanded
	  into an entry preserving source_file metadata.

	Returns the output file path.
	"""
	output_path = Path(output_file)
	json_files = _collect_files(
		input_dir=input_dir,
		suffix=".json",
		recursive=recursive,
		exclude_path=output_path,
	)

	if not json_files:
		raise ValueError("No JSON files found to combine.")

	merged: list[dict] = []
	for file_path in json_files:
		with file_path.open("r", encoding=encoding) as f:
			payload = json.load(f)

		if flatten_lists and isinstance(payload, list):
			for item in payload:
				merged.append({"source_file": file_path.as_posix(), "data": item})
			continue

		merged.append({"source_file": file_path.as_posix(), "data": payload})

	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", encoding=encoding) as f:
		json.dump(merged, f, ensure_ascii=False, indent=2)
		f.write("\n")

	return output_path


def merge(
	mode: Literal["md", "json"],
	input_dir: str | Path,
	output_file: str | Path,
	recursive: bool = True,
	**kwargs,
) -> Path:
	"""
	Public entry point for file merging, designed for importing from other files.

	Parameters for mode="md":
	- add_file_headers: bool = True
	- separator: str = "\n\n---\n\n"
	- encoding: str = "utf-8"

	Parameters for mode="json":
	- flatten_lists: bool = False
	- encoding: str = "utf-8"
	"""
	if mode == "md":
		return _merge_markdown_files(
			input_dir=input_dir,
			output_file=output_file,
			recursive=recursive,
			add_file_headers=kwargs.get("add_file_headers", True),
			separator=kwargs.get("separator", "\n\n---\n\n"),
			encoding=kwargs.get("encoding", "utf-8"),
		)

	if mode == "json":
		return _merge_json_files(
			input_dir=input_dir,
			output_file=output_file,
			recursive=recursive,
			flatten_lists=kwargs.get("flatten_lists", False),
			encoding=kwargs.get("encoding", "utf-8"),
		)

	raise ValueError("mode must be either 'md' or 'json'.")


def _build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Combine all Markdown or JSON files in a directory into one output file."
	)
	parser.add_argument("mode", choices=["md", "json"], help="Merge mode.")
	parser.add_argument("input_dir", help="Directory containing source files.")
	parser.add_argument("output_file", help="Combined output file path.")
	parser.add_argument(
		"--no-recursive",
		action="store_true",
		help="Only scan files in input_dir, not subdirectories.",
	)
	parser.add_argument(
		"--no-headers",
		action="store_true",
		help="For md mode: do not add source-file header before each section.",
	)
	parser.add_argument(
		"--flatten-lists",
		action="store_true",
		help="For json mode: flatten top-level lists into individual entries.",
	)
	return parser


def main(argv: Iterable[str] | None = None) -> None:
	parser = _build_parser()
	args = parser.parse_args(argv)

	recursive = not args.no_recursive

	if args.mode == "md":
		out_path = merge(
			mode="md",
			input_dir=args.input_dir,
			output_file=args.output_file,
			recursive=recursive,
			add_file_headers=not args.no_headers,
		)
	else:
		out_path = merge(
			mode="json",
			input_dir=args.input_dir,
			output_file=args.output_file,
			recursive=recursive,
			flatten_lists=args.flatten_lists,
		)

	print(f"Combined output written to: {out_path}")


if __name__ == "__main__":
	main()
