#!/usr/bin/env python3
"""
Summarize the structure of the restructured social dynamics analysis
"""

import csv
from collections import defaultdict

def summarize_csv():
    categories = defaultdict(set)
    
    with open('restructured_social_dynamics_analysis.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            main_category = row['Main Category']
            sub_category = row['Sub-Category']
            categories[main_category].add(sub_category)
    
    print("=== RESTRUCTURED SOCIAL DYNAMICS ANALYSIS STRUCTURE ===\n")
    
    for category in sorted(categories.keys()):
        sub_categories = sorted(categories[category])
        print(f"📁 {category.upper().replace('_', ' ')}")
        for sub_cat in sub_categories:
            print(f"   └── {sub_cat.replace('_', ' ')}")
        print()
    
    print(f"Total Categories: {len(categories)}")
    print(f"Total Sub-Categories: {sum(len(subs) for subs in categories.values())}")

if __name__ == "__main__":
    summarize_csv()
