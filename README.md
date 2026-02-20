# Empire Simulation Workflow

This repository contains scripts to automate the execution of Empire simulations with varying parameters based on an Excel configuration file.

## Prerequisites

- Python 3.x
- Python packages: `pandas`, `openpyxl`, `matplotlib`
  ```bash
  pip install pandas openpyxl matplotlib
  ```
- Slurm workload manager (for `sbatch` commands)
- Empire code installed and accessible.

## Workflow

The workflow consists of three main stages: generating input files, running a reference simulation, and running parameter variation simulations.

### 1. Generate Input Files

Run the Python script to parse the Excel file (`Nuclear Reaction Parameter Summary.xlsx`) and generate the directory structure and input files.

```bash
python3 generate_inputs.py
```

This will create a `Simulations/` directory containing:
- `Simulations/Reference/`: Directory for the reference run (OMPFIT 0, parameters commented out).
- `Simulations/Variations/`: Directories for each parameter variation (OMPFIT 1, parameters uncommented and varied).
- `Simulations/run_list.txt`: A list of all variation directories to be processed.

### 2. Run Reference Simulation

Submit the reference job to the cluster. This job prepares the necessary files (e.g., in `TL/`) that will be used by the variation runs.

```bash
sbatch run_reference.sbatch
```

**Wait for this job to complete successfully before proceeding.** Check the output in `Simulations/Reference/15Npn.out` and `job.*.out/err` log files.

### 3. Run Variation Simulations

Submit the variation jobs using a Slurm Job Array. This will run Empire for each variation, extract cross-sections, and generate plots.

First, determine the number of variations (N) by counting the lines in `run_list.txt`:

```bash
wc -l < Simulations/run_list.txt
```

Then, submit the job array. Replace `N` with the number obtained above (e.g., if there are 500 variations, use `1-500`). The `%5` ensures only 5 jobs run concurrently on separate nodes.

```bash
sbatch --array=1-N%5 run_variations.sbatch
```

*Example:*
```bash
# If run_list.txt has 120 lines:
sbatch --array=1-120%5 run_variations.sbatch
```

### 4. Results

For each variation, the results will be stored in its respective directory (e.g., `Simulations/Variations/FITRVV/10.0/`).
Each directory will contain:
- `15Npn.out`: The Empire output file.
- `extracted_production_cross_sections.csv`: Extracted cross-section data.
- `plot.png`: A plot of the production cross-sections vs incident energy.

## File Structure

- `generate_inputs.py`: Main script to creating the folder structure and input files.
- `run_reference.sbatch`: Slurm script for the reference run.
- `run_variations.sbatch`: Slurm Job Array script for variation runs.
- `Cross-section.py`: Helper script to extract data from `.out` files.
- `plot.py`: Helper script to generate plots from `.csv` files.
- `Nuclear Reaction Parameter Summary.xlsx`: Configuration file for parameter ranges and increments.
- `15Npn.inp`: Template input file.

## Notes

- The workflow assumes `run_variations.sbatch` is submitted from the repository root (where `Simulations/` is located).
- Ensure the paths in `run_variations.sbatch` and `run_reference.sbatch` (e.g., to the Empire executable) are correct for your environment.
- The `generate_inputs.py` script automatically handles `FIT...` parameters and `FITDEF` (replacing `xxxx` and `yy` placeholders).
