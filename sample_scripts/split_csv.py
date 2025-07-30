import os
import csv
import math
from pathlib import Path

def split_csv(input_file, output_dir, num_files):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the input CSV file
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # Read header
        rows = list(reader)    # Read remaining rows
    
    total_rows = len(rows)
    rows_per_file = math.ceil(total_rows / num_files)
    
    # Get the base filename without extension
    base_name = Path(input_file).stem
    
    # Split the data and write to multiple files
    for i in range(num_files):
        start_idx = i * rows_per_file
        end_idx = min((i + 1) * rows_per_file, total_rows)
        
        if start_idx >= total_rows:
            break
            
        output_file = os.path.join(output_dir, f"{base_name}_part{i+1}.csv")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)  # Write header
            writer.writerows(rows[start_idx:end_idx])  # Write rows
            
        print(f"Created: {output_file} with {end_idx - start_idx} rows")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Split a CSV file into multiple files with headers.')
    parser.add_argument('input_file', help='Input CSV file path')
    parser.add_argument('-n', '--num-files', type=int, required=True, help='Number of files to split into')
    parser.add_argument('-o', '--output-dir', default='output', help='Output directory (default: output/)')
    
    args = parser.parse_args()
    
    split_csv(args.input_file, args.output_dir, args.num_files)
    print("\nSplitting completed successfully!")

# python split_csv.py input2\標高点群_part4.csv -n 10 -o input2\output