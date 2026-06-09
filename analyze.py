"""
Job Market Analysis
===================
Reads a jobs CSV (produced by fetcher.py) and generates:
    - A printed summary report
    - A Markdown report  (report.md)
    - Charts saved as PNGs (charts/)

Insights:
    - Total jobs and how many include salary data
    - Median / average salary
    - Top hiring companies
    - Top locations by number of openings
    - Average salary by location

Usage:
    python analyze.py                       # uses adzuna_jobs.csv
    python analyze.py --file sample_jobs.csv
"""

import argparse
import os

import matplotlib

matplotlib.use("Agg")  # non-interactive backend so it saves files without a display
import matplotlib.pyplot as plt
import pandas as pd

CHARTS_DIR = "charts"
REPORT_FILE = "report.md"


def load_data(path):
    """Load the CSV and compute a single 'salary' column (avg of min/max)."""
    df = pd.read_csv(path)
    # Coerce salary columns to numbers; missing/blank values become NaN
    df["salary_min"] = pd.to_numeric(df.get("salary_min"), errors="coerce")
    df["salary_max"] = pd.to_numeric(df.get("salary_max"), errors="coerce")
    df["salary"] = df[["salary_min", "salary_max"]].mean(axis=1)
    return df


def top_companies(df, n=10):
    """Return the n companies with the most job postings."""
    return df["company"].replace("", pd.NA).dropna().value_counts().head(n)


def top_locations(df, n=10):
    """Return the n locations with the most job postings."""
    return df["location"].replace("", pd.NA).dropna().value_counts().head(n)


def avg_salary_by_location(df, n=10, min_jobs=2):
    """Average salary per location, for locations with at least min_jobs postings."""
    salaried = df.dropna(subset=["salary"])
    grouped = salaried.groupby("location")["salary"].agg(["mean", "count"])
    grouped = grouped[grouped["count"] >= min_jobs]
    return grouped.sort_values("mean", ascending=False).head(n)


def save_bar_chart(series, title, xlabel, filename, color="#2a7de1"):
    """Save a horizontal bar chart from a pandas Series."""
    if series.empty:
        return
    plt.figure(figsize=(9, 5))
    series.sort_values().plot(kind="barh", color=color)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, filename), dpi=120)
    plt.close()


def save_salary_histogram(df, filename="salary_distribution.png"):
    """Save a histogram of the salary distribution."""
    salaries = df["salary"].dropna()
    if salaries.empty:
        return
    plt.figure(figsize=(9, 5))
    plt.hist(salaries, bins=15, color="#2a7de1", edgecolor="white")
    plt.title("Salary Distribution")
    plt.xlabel("Salary")
    plt.ylabel("Number of jobs")
    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, filename), dpi=120)
    plt.close()


def write_report(df, companies, locations, salary_by_loc):
    """Write a Markdown summary report."""
    salaried = df.dropna(subset=["salary"])
    lines = ["# Job Market Analysis\n"]
    lines.append(f"- **Total jobs analysed:** {len(df)}")
    lines.append(f"- **Jobs with salary data:** {len(salaried)}")
    if not salaried.empty:
        lines.append(f"- **Median salary:** {salaried['salary'].median():,.0f}")
        lines.append(f"- **Average salary:** {salaried['salary'].mean():,.0f}")

    lines.append("\n## Top hiring companies\n")
    lines.append("| Company | Openings |\n|---|---|")
    for name, count in companies.items():
        lines.append(f"| {name} | {count} |")

    lines.append("\n## Top locations by openings\n")
    lines.append("| Location | Openings |\n|---|---|")
    for name, count in locations.items():
        lines.append(f"| {name} | {count} |")

    if not salary_by_loc.empty:
        lines.append("\n## Average salary by location\n")
        lines.append("| Location | Avg salary | Jobs |\n|---|---|---|")
        for name, row in salary_by_loc.iterrows():
            lines.append(f"| {name} | {row['mean']:,.0f} | {int(row['count'])} |")

    lines.append("\n## Charts\n")
    lines.append("![Top companies](charts/top_companies.png)")
    lines.append("![Average salary by location](charts/avg_salary_by_location.png)")
    lines.append("![Salary distribution](charts/salary_distribution.png)")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Analyse a jobs CSV and produce a report + charts.")
    parser.add_argument("--file", default="adzuna_jobs.csv", help="Path to the jobs CSV")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"File not found: {args.file}. Run fetcher.py first, or pass --file sample_jobs.csv")
        return

    os.makedirs(CHARTS_DIR, exist_ok=True)
    df = load_data(args.file)

    companies = top_companies(df)
    locations = top_locations(df)
    salary_by_loc = avg_salary_by_location(df)
    salaried = df.dropna(subset=["salary"])

    # ── Printed summary ───────────────────────────────────────────────
    print(f"\nTotal jobs analysed: {len(df)}")
    print(f"Jobs with salary data: {len(salaried)}")
    if not salaried.empty:
        print(f"Median salary: {salaried['salary'].median():,.0f}")
        print(f"Average salary: {salaried['salary'].mean():,.0f}")

    print("\nTop hiring companies:")
    for name, count in companies.items():
        print(f"  {count:>3}  {name}")

    if not salary_by_loc.empty:
        print("\nAverage salary by location:")
        for name, row in salary_by_loc.iterrows():
            print(f"  {row['mean']:>10,.0f}  ({int(row['count'])} jobs)  {name}")

    # ── Charts + report ───────────────────────────────────────────────
    save_bar_chart(companies, "Top Hiring Companies", "Openings", "top_companies.png")
    save_bar_chart(
        salary_by_loc["mean"],
        "Average Salary by Location",
        "Average salary",
        "avg_salary_by_location.png",
        color="#16a34a",
    )
    save_salary_histogram(df)
    write_report(df, companies, locations, salary_by_loc)

    print(f"\nSaved charts to {CHARTS_DIR}/ and report to {REPORT_FILE}")


if __name__ == "__main__":
    main()
