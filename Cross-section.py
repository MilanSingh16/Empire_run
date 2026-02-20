import os
import glob
import re
import pandas as pd

def parse_empire_output():
    # 1. Define Regex Patterns
    # Matches: "Reaction ... at incident energy 1.000D+00 MeV" or "INCIDENT ENERGY 1.800D+01 MeV"
    # We use re.IGNORECASE to handle "Incident Energy" vs "INCIDENT ENERGY"
    energy_pattern = re.compile(r"(?:at\s+)?INCIDENT\s+ENERGY\s+([\d\.\+\-DE]+)\s+MeV", re.IGNORECASE)
    
    # Matches: "8-O - 16 production cross section0.559974E-02  mb"
    # Captures the isotope name (group 1) and the value (group 2)
    # \s* handles cases where 'section' and the number are merged
    production_pattern = re.compile(r"^\s*(.*?)\s+production cross section\s*([\d\.\+\-DE]+)\s+mb", re.IGNORECASE)

    data_rows = []

    # 2. Iterate over all .out files in the current directory
    output_files = glob.glob("*.out")
    
    if not output_files:
        print("No .out files found in the current directory.")
        return

    print(f"Found {len(output_files)} output files. Processing...")

    for file_path in output_files:
        current_energy = None
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # --- Check for Incident Energy Block ---
                energy_match = energy_pattern.search(line)
                if energy_match:
                    # Replace Fortran 'D' notation with Python 'E' (e.g., 1.0D+01 -> 1.0E+01)
                    raw_energy = energy_match.group(1).replace('D', 'E').replace('d', 'e')
                    try:
                        current_energy = float(raw_energy)
                    except ValueError:
                        continue # Skip if energy parse fails
                    continue

                # --- Check for Production Cross Section ---
                # Only extract if we have established a current energy context
                if current_energy is not None:
                    prod_match = production_pattern.search(line)
                    if prod_match:
                        isotope_raw = prod_match.group(1).strip()
                        # Clean up isotope name (e.g., "8-O - 16" -> "8-O-16")
                        isotope = "-".join(isotope_raw.split()) 
                        
                        raw_value = prod_match.group(2).replace('D', 'E').replace('d', 'e')
                        try:
                            xs_value = float(raw_value)
                            
                            data_rows.append({
                                'File': file_path,
                                'Incident_Energy_MeV': current_energy,
                                'Isotope': isotope,
                                'Cross_Section_mb': xs_value
                            })
                        except ValueError:
                            continue

    # 3. Process Data into CSV
    if not data_rows:
        print("No production cross-section data found.")
        return

    df = pd.DataFrame(data_rows)

    # Sort by Energy
    df.sort_values(by='Incident_Energy_MeV', inplace=True)

    # Pivot to make it readable: Energy as Index, Isotopes as Columns
    # We aggregate using 'max' in case of duplicates, though typically there shouldn't be 
    # conflicting duplicates for the exact same energy/isotope in one run.
    df_pivot = df.pivot_table(
        index='Incident_Energy_MeV', 
        columns='Isotope', 
        values='Cross_Section_mb'
    ).reset_index()

    # 4. Save Output
    output_filename = "extracted_production_cross_sections.csv"
    df_pivot.to_csv(output_filename, index=False)
    print(f"Success! Data extracted to {output_filename}")
    print(df_pivot.head())

if __name__ == "__main__":
    parse_empire_output()
