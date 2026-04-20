import argparse
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output_VL")

def move_imgs_folders(input_dir: str, dest_dir: str):
	copied_count = 0
	for root, dirs, files in os.walk(input_dir):
		if "imgs" in dirs:
			root_normalized = root.replace("\\", "/")
			if "/VN100/" not in root_normalized:
				continue
			
			path_parts = root_normalized.split("/")
			try:
				vn100_index = path_parts.index("VN100")
			except ValueError:
				continue
				
			if vn100_index < 2:
				continue
				
			year = path_parts[vn100_index - 1]
			ticker = path_parts[vn100_index - 2]
			
			src_imgs = os.path.join(root, "imgs")
			dest_imgs = os.path.join(dest_dir, ticker, year, "imgs")
			
			print(f"Copying {src_imgs} -> {dest_imgs}")
			os.makedirs(os.path.dirname(dest_imgs), exist_ok=True)
			shutil.copytree(src_imgs, dest_imgs, dirs_exist_ok=True)
			copied_count += 1
			
	print(f"Done. Copied {copied_count} imgs folders.")

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Copy imgs folders to the merged output directory.")
	parser.add_argument("--input-dir", default=OUTPUT_DIR)
	parser.add_argument("--output-dir", default=os.path.join(SCRIPT_DIR, "output_VL_merged"))
	args = parser.parse_args()
	
	move_imgs_folders(args.input_dir, args.output_dir)
