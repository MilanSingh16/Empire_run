#!/bin/bash
#SBATCH -N 1
#SBATCH --ntasks-per-node=1
#SBATCH --time=02:00:00
#SBATCH --job-name=Var_15Npn
#SBATCH --error=job.%A_%a.err
#SBATCH --output=job.%A_%a.out
#SBATCH --partition=standard
#SBATCH --array=1-10%5

# NOTE: Adjust --array above to match the number of variations!
# You can override this on command line: sbatch --array=1-N%5 run_variations.sbatch
# where N is the number of lines in Simulations/run_list.txt

# 1. Get Directory from Run List
# Assuming run_list.txt is in Simulations/ relative to submission directory (Repo Root)
RUN_LIST="Simulations/run_list.txt"

if [ ! -f "$RUN_LIST" ]; then
    echo "Error: Run list not found at $RUN_LIST"
    exit 1
fi

# Get the directory for this task ID
DIR=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$RUN_LIST")

if [ -z "$DIR" ]; then
    echo "Error: No directory found for task ID $SLURM_ARRAY_TASK_ID"
    exit 1
fi

echo "Processing Variation Directory: $DIR"

# Navigate to the variation directory
cd "$DIR" || exit 1

# 2. Determine Paths
# DIR is .../Simulations/Variations/Param/Val
# We need to find .../Simulations/Reference and Repo Root

# Parent of Val is Param
PARAM_DIR=$(dirname "$DIR")
# Parent of Param is Variations
VAR_ROOT=$(dirname "$PARAM_DIR")
# Parent of Variations is Simulations
SIM_ROOT=$(dirname "$VAR_ROOT")
# Sibling of Variations is Reference
REF_DIR="$SIM_ROOT/Reference"
# Parent of Simulations is Repo Root
REPO_ROOT=$(dirname "$SIM_ROOT")

echo "Reference Directory: $REF_DIR"
echo "Repo Root: $REPO_ROOT"

# 3. Copy Reference Files
# Copy all files from Reference except input file and job logs
# We use rsync to exclude specific files
# Or cp with excluding. cp doesn't support exclude easily.
# Assuming standard Linux environment, we can use a loop or find.
# But simply copying everything and then restoring 15Npn.inp is safer?
# No, 15Npn.inp already has our variation. We don't want to overwrite it.
# We can use 'cp -n' (no clobber) if available.
# Or just copy specific files: *.out, *.lst, TL directory.
# User said "copy all of these files".
# Let's try rsync. If rsync is not available, fallback to cp.
if command -v rsync &> /dev/null; then
    rsync -av --exclude='15Npn.inp' --exclude='job.*' "$REF_DIR/" .
else
    # Fallback: Copy all, then restore input? No, restore is hard if overwritten.
    # Copy explicitly.
    if [ -d "$REF_DIR/TL" ]; then
        cp -r "$REF_DIR/TL" .
    fi
    cp "$REF_DIR"/*.out . 2>/dev/null
    cp "$REF_DIR"/*.lst . 2>/dev/null
    # Add other extensions if needed
fi

# 4. Pre-Run Housekeeping
cp 15Npn.inp INPUT.DAT
if [ ! -d "TL" ]; then
    mkdir -p TL
fi

# 5. Execute Empire
EMPIRE_CMD="/home/milansupes/Empire_run/EMPIRE-3.2.3src-2023-06-21/EMPIRE-3.2.3/source/empire"
$EMPIRE_CMD > 15Npn.log

# 6. Post-Run Housekeeping
mv OUTPUT.DAT 15Npn.out
mv LIST.DAT 15Npn.lst
rm INPUT.DAT

# 7. Analysis
# Run Cross-section.py (generates csv)
python3 "$REPO_ROOT/Cross-section.py"

# Run plot.py (generates plot.png from csv)
python3 "$REPO_ROOT/plot.py"

echo "Variation run complete for $DIR"
