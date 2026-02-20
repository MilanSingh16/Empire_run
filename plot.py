import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_cross_sections():
    csv_file = "extracted_production_cross_sections.csv"

    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found.")
        return

    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    if df.empty:
        print("CSV file is empty.")
        return

    # Assuming 'Incident_Energy_MeV' is the x-axis
    if 'Incident_Energy_MeV' not in df.columns:
        print("Error: 'Incident_Energy_MeV' column not found in CSV.")
        return

    x = df['Incident_Energy_MeV']

    # Get all other columns as y-series (Isotopes)
    isotopes = [col for col in df.columns if col != 'Incident_Energy_MeV']

    plt.figure(figsize=(10, 6))

    for isotope in isotopes:
        plt.plot(x, df[isotope], marker='o', linestyle='-', label=isotope)

    plt.title('Production Cross Sections vs Incident Energy')
    plt.xlabel('Incident Energy (MeV)')
    plt.ylabel('Cross Section (mb)')
    plt.legend()
    plt.grid(True)

    output_file = "plot.png"
    plt.savefig(output_file)
    print(f"Plot saved to {output_file}")
    plt.close()

if __name__ == "__main__":
    plot_cross_sections()
