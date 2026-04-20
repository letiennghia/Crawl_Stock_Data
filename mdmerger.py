import argparse
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_VL")


def find_md_parts(base_dir: str):
	"""Find markdown part files inside output_VL/{ticker}/{year}/VN100/{ticker}."""
	# Example: ACB_BCTN_2014_12.md -> base: ACB_BCTN_2014, part: 12
	pattern = re.compile(r"^([A-Za-z0-9]+_BCTN_\d{4})_(\d+)\.md$", re.IGNORECASE)
	grouped = {}

	for root, _, files in os.walk(base_dir):
		root_normalized = root.replace("\\", "/")
		if "/VN100/" not in root_normalized:
			continue

		path_parts = root_normalized.split("/")
		try:
			vn100_index = path_parts.index("VN100")
		except ValueError:
			continue

		# Expecting .../output_VL/{ticker}/{year}/VN100/{ticker}
		if vn100_index < 2 or vn100_index + 1 >= len(path_parts):
			continue

		year = path_parts[vn100_index - 1]
		ticker = path_parts[vn100_index - 2]

		for filename in files:
			match = pattern.match(filename)
			if not match:
				continue

			base_name = match.group(1)
			part_number = int(match.group(2))
			grouped.setdefault((ticker, year, base_name), []).append(
				(part_number, os.path.join(root, filename))
			)
	return grouped


def merge_markdown_files(input_dir: str, dest_dir: str, overwrite: bool = False):
	grouped_parts = find_md_parts(input_dir)
	if not grouped_parts:
		print(f"No markdown parts found under: {input_dir}")
		return

	merged_count = 0
	skipped_count = 0

	for (ticker, year, base_name), parts in sorted(grouped_parts.items()):
		parts.sort(key=lambda item: item[0])

		destination_dir = os.path.join(dest_dir, ticker, year)
		os.makedirs(destination_dir, exist_ok=True)
		destination_file = os.path.join(destination_dir, f"{base_name}.md")

		if os.path.exists(destination_file) and not overwrite:
			print(f"[SKIP] Exists: {destination_file}")
			skipped_count += 1
			continue

		merged_content = []
		for part_number, part_path in parts:
			try:
				with open(part_path, "r", encoding="utf-8") as md_file:
					content = md_file.read().strip()
					if content:
						merged_content.append(content)
					else:
						merged_content.append(f"<!-- Empty markdown part: {part_number} -->")
			except Exception as exc:
				print(f"[ERROR] Cannot read {part_path}: {exc}")
				merged_content = []
				break

		if not merged_content:
			print(f"[SKIP] Failed to merge: {ticker}/{year}/{base_name}")
			skipped_count += 1
			continue

		try:
			with open(destination_file, "w", encoding="utf-8") as out_file:
				out_file.write("\n\n".join(merged_content) + "\n")
			merged_count += 1
			print(f"[OK] {destination_file}")
		except Exception as exc:
			print(f"[ERROR] Cannot write {destination_file}: {exc}")
			skipped_count += 1

	print(
		f"Done. Merged: {merged_count}, Skipped/Failed: {skipped_count}, Total groups: {len(grouped_parts)}"
	)


def parse_args():
	parser = argparse.ArgumentParser(
		description="Merge markdown parts and write to output_VL/{ticker}/{year}."
	)
	parser.add_argument(
		"--input-dir",
		default=OUTPUT_DIR,
		help="Root folder containing part files (default: output_VL)",
	)
	parser.add_argument(
		"--output-dir",
		default=os.path.join(SCRIPT_DIR, "output_merged"),
		help="Root output folder for merged files (default: output_merged)",
	)
	parser.add_argument(
		"--overwrite",
		action="store_true",
		help="Overwrite existing merged markdown file if it already exists.",
	)
	return parser.parse_args()


if __name__ == "__main__":
	arguments = parse_args()
	merge_markdown_files(input_dir=arguments.input_dir, dest_dir=arguments.output_dir, overwrite=arguments.overwrite)
