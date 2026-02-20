import os
import shutil
import pandas as pd
import re
import math

# --- Configuration ---
INPUT_TEMPLATE = "15Npn.inp"
EXCEL_FILE = "Nuclear Reaction Parameter Summary.xlsx"
OUTPUT_DIR = "Simulations"
REFERENCE_DIR_NAME = "Reference"
VARIATIONS_DIR_NAME = "Variations"

# --- Mapping ---
# Maps Excel 'Parameter' string parts to FIT keys.
# (Potential Type, Parameter Type) -> (Main Key, Energy Key)
# We use a lookup based on identifying keywords in the Excel row.

def get_fit_keys(potential, param_name):
    # Normalize strings
    p_term = str(potential).lower()
    p_name = str(param_name).lower()

    # Identify Potential
    prefix = ""
    if "real volume" in p_term:
        prefix = "FITRV"
    elif "imaginary surface" in p_term:
        prefix = "FITIS"
    elif "imaginary volume" in p_term:
        prefix = "FITIV"
    elif "spin-orbit" in p_term:
        prefix = "FITOR" # Assuming FITOR based on template usually having FITORV/R/A/D
    else:
        return None, None # Skip (e.g. Coulomb)

    # Identify Parameter
    if "depth" in p_name:
        return f"{prefix}V", f"{prefix}D"
    elif "radius" in p_name:
        return f"{prefix}R", None
    elif "diffuseness" in p_name:
        return f"{prefix}A", None

    return None, None

def parse_excel_row(row):
    """
    Returns a dictionary of variations:
    {
        'MAIN_KEY': {'range': X, 'inc': Y},
        'E_KEY': {'range': Z, 'inc': W}  (if applicable)
    }
    """
    param_name = row['Parameter']
    potential = row['Potential Term']

    if pd.isna(param_name):
        return {}

    main_key, e_key = get_fit_keys(potential, param_name)
    if not main_key:
        return {}

    # Parse ranges/increments
    range_str = row['Parameter Variation range']
    inc_str = row['incrementation']
    e_term_col = row['Energy dependant term']

    # Regexes
    main_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(?:MeV|fm|Mev)", re.IGNORECASE)
    e_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*E", re.IGNORECASE)

    # Helper to extract float
    def extract(text, pattern):
        if not isinstance(text, str): return None
        m = pattern.search(text)
        return float(m.group(1)) if m else None

    # Parse Main
    mr = extract(range_str, main_pattern)
    mi = extract(inc_str, main_pattern)

    # Parse E
    er = extract(range_str, e_pattern)
    ei = extract(inc_str, e_pattern)

    # Fallback for E range
    if er is None and e_key and not pd.isna(e_term_col):
        # Try to find a float in e_term_col
        try:
            val = float(str(e_term_col).split()[0]) # Take first word if "0.5 MeV"
            # Or regex
            m = re.search(r"(\d+(?:\.\d+)?)", str(e_term_col))
            if m: er = float(m.group(1))
        except:
            pass

    variations = {}

    # Add Main Variation if valid
    if main_key and mr is not None and mi is not None:
        variations[main_key] = {'range': mr, 'inc': mi}

    # Add E Variation if valid
    if e_key and er is not None and ei is not None:
        variations[e_key] = {'range': er, 'inc': ei}

    return variations

def generate_values(range_val, inc_val):
    """Generates sequence: 0, inc, 2*inc... range, -inc, -2*inc... -range"""
    values = [0.0]

    # Avoid infinite loop if inc is 0
    if inc_val <= 0:
        return values

    # Positive
    curr = inc_val
    while curr <= range_val + 1e-9: # epsilon for float comparison
        values.append(curr)
        curr += inc_val

    # Negative
    curr = -inc_val
    while curr >= -range_val - 1e-9:
        values.append(curr)
        curr -= inc_val

    # Sort for tidiness? User didn't ask, but nice.
    # Actually, keep 0 first, then others? User just said "create every possible...".
    # I'll output sorted list.
    return sorted(list(set(values))) # set to remove duplicates if any

def process_template_line(line, target_key=None, target_val=None):
    """
    Processes a single line of the template.
    Ref Mode: target_key=None. Comments out all FIT... lines.
    Var Mode: target_key="FITRVV", target_val=1.5.
              Uncomments FIT lines.
              Sets target_key to target_val.
              Sets other FIT keys to 0.
    """
    # Check if line is a FIT line
    # Regex to find "FIT..." at start of line (ignoring potential existing comment *)
    # But wait, user wants to uncomment if commented.
    # And the template has "FIT..."

    clean_line = line.strip()
    is_fit = False
    fit_key = ""

    # Detect FIT key
    # It might start with FIT or *FIT
    # We want to catch "FITRVV", "FITRVR", etc.
    match = re.search(r"^(\*?)(FIT[A-Z]+)", clean_line)
    if match:
        is_fit = True
        fit_key = match.group(2) # e.g. FITRVV

    if not is_fit:
        return line # Return original line unchanged

    # Reference Mode (target_key is None)
    if target_key is None:
        if not line.strip().startswith("*"):
            return "*" + line
        return line

    # Variation Mode
    # 1. Uncomment (remove *)
    if line.strip().startswith("*"):
        line = line.replace("*", "", 1)

    # 2. Replace xxxx values
    # The line is like: "FITRVV     xxxx      xxxx     1  ! Comment"
    # We need to preserve spacing if possible, or just format cleanly.
    # User said: "keep all the spaces in the input files as they are"
    # This is hard if we replace "xxxx" (4 chars) with "-10.5" (5 chars).
    # But "xxxx numbers become value... only put values at this particular column".
    # I will attempt to replace the first "xxxx" and second "xxxx".

    val1 = "0."
    val2 = "0.0"

    if fit_key == target_key:
        val1 = f"{target_val}" # Format as string

    # Replace logic
    # Find "xxxx" and replace.
    # Issue: replace() replaces all occurrences.
    # We want to replace first xxxx with val1, second with val2.

    # Make a copy of line
    new_line = line

    # Check if xxxx exists
    if "xxxx" in new_line:
        # First xxxx
        new_line = new_line.replace("xxxx", val1, 1)
        # Second xxxx
        new_line = new_line.replace("xxxx", val2, 1)

    # Check if yy exists (e.g. FITDEF)
    if "yy" in new_line:
        # First yy
        new_line = new_line.replace("yy", val1, 1)
        # Second yy
        new_line = new_line.replace("yy", val2, 1)

    return new_line

def main():
    # 1. Setup Dirs
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    ref_dir = os.path.join(OUTPUT_DIR, REFERENCE_DIR_NAME)
    os.makedirs(ref_dir)

    var_root_dir = os.path.join(OUTPUT_DIR, VARIATIONS_DIR_NAME)
    os.makedirs(var_root_dir)

    # 2. Read Template
    with open(INPUT_TEMPLATE, 'r') as f:
        template_lines = f.readlines()

    # 3. Create Reference Input
    # OMPFIT should be 0.
    # FIT lines commented.
    with open(os.path.join(ref_dir, "15Npn.inp"), 'w') as f:
        for line in template_lines:
            # Handle OMPFIT
            if "OMPFIT" in line and not "FITOMP" in line: # Wait, usually it is FITOMP?
                # Template has "FITOMP    1"
                # User said "OMPFIT 0".
                # Ah, let's check template.
                # "OMPOT     -4016.    2"
                # "FITOMP    1"
                # User said "OMPFIT 0". Probably means "FITOMP 0".
                if "FITOMP" in line:
                    line = line.replace("1", "0")

            # Handle FIT lines (comment them)
            # Make sure we don't comment FITOMP if it's considered a FIT line.
            # My logic in process_template_line checks for FIT[A-Z]+.
            # FITOMP matches.
            # But user said: "OMPFIT 0 and FITabc parameters commented out".
            # FITOMP is usually the flag to enable fitting/OMP variation.
            # So I should probably keep FITOMP uncommented but set to 0?
            # User: "run the sbatch file with OMPFIT 0 and FITabc are all commented out"
            # User calls it OMPFIT, template has FITOMP. I assume they are the same.
            # If I comment FITOMP, it might disable it.
            # I will set FITOMP to 0 and NOT comment it.
            # I will comment only the FITRVV, FITRVR, etc.

            if "FITOMP" in line:
                 # Just ensure it is 0
                 # Regex replace the number?
                 # Assuming "FITOMP    1" -> "FITOMP    0"
                 line = re.sub(r"(FITOMP\s+)(\d+)", r"\1 0", line)
                 f.write(line)
                 continue

            # Process other FIT lines
            f.write(process_template_line(line, target_key=None))

    print(f"Created Reference input in {ref_dir}")

    # 4. Parse Excel and Generate Variations
    df = pd.read_excel(EXCEL_FILE)

    # Collect all valid variations
    # Structure: { 'FITRVV': {'range': 40, 'inc': 1}, ... }
    all_variations = {}

    for index, row in df.iterrows():
        vars_in_row = parse_excel_row(row)
        all_variations.update(vars_in_row)

    print(f"Found {len(all_variations)} parameters to vary.")

    # 5. Generate Variation Files
    run_list_path = os.path.join(OUTPUT_DIR, "run_list.txt")
    run_dirs = []

    for fit_key, constraints in all_variations.items():
        # Check if this key actually exists in the template
        # (Scan template lines for fit_key)
        key_exists = any(fit_key in line for line in template_lines)
        if not key_exists:
            print(f"Warning: {fit_key} found in Excel but not in template. Skipping.")
            continue

        range_val = constraints['range']
        inc_val = constraints['inc']
        values = generate_values(range_val, inc_val)

        print(f"Generating {len(values)} variations for {fit_key}...")

        for val in values:
            # Create Dir
            # Format val to avoid messy filenames (e.g. 0.0, -1.0)
            val_str = f"{val:.4f}".rstrip('0').rstrip('.') if val != 0 else "0.0"
            dir_name = os.path.join(var_root_dir, fit_key, val_str)
            os.makedirs(dir_name, exist_ok=True)

            # Write Input
            with open(os.path.join(dir_name, "15Npn.inp"), 'w') as f:
                for line in template_lines:
                    # Handle FITOMP -> 1
                    if "FITOMP" in line:
                         line = re.sub(r"(FITOMP\s+)(\d+)", r"\1 1", line)
                         f.write(line)
                         continue

                    # Handle FIT lines
                    # Pass the current target key and value
                    f.write(process_template_line(line, target_key=fit_key, target_val=val))

            # Add to run list
            # Use absolute path for safety in sbatch
            run_dirs.append(os.path.abspath(dir_name))

    # Write Run List
    with open(run_list_path, 'w') as f:
        for d in run_dirs:
            f.write(d + "\n")

    print(f"Generated {len(run_dirs)} variation inputs.")
    print(f"Run list saved to {run_list_path}")

if __name__ == "__main__":
    main()
