#!/bin/bash
#SBATCH -N 1
#SBATCH --ntasks-per-node=1
#SBATCH --time=02:00:00
#SBATCH --job-name=Ref_15Npn
#SBATCH --error=job.%J.err
#SBATCH --output=job.%J.out
#SBATCH --partition=standard

# Navigate to the reference directory
# Assuming submission from repository root
cd Simulations/Reference

# Pre-Run Housekeeping
cp 15Npn.inp INPUT.DAT
mkdir -p TL

# Execute Empire
/home/milansupes/Empire_run/EMPIRE-3.2.3src-2023-06-21/EMPIRE-3.2.3/source/empire > 15Npn.log

# Post-Run Housekeeping
mv OUTPUT.DAT 15Npn.out
mv LIST.DAT 15Npn.lst

# Clean up
rm INPUT.DAT

echo "Reference run complete."
