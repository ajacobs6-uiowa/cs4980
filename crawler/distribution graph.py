import matplotlib.pyplot as plt
import json
import os
from scipy import stats
import numpy


# Original data from both runs per persona
path_to_dir = "C:/Users/TestingTesting/Desktop/cs4980-main/crawler/data_storage/"
json_dir = ['run_1/bidding_data','run_2/bidding_data','run_3/bidding_data','run_4/bidding_data','run_5/bidding_data','run_6/bidding_data','run_7/bidding_data','run_8/bidding_data','run_9/bidding_data','run_10/bidding_data',]
json_results = []
for dir in json_dir:
    json_results_dir = []
    for file in os.listdir(path_to_dir+dir):
        full_filename = "%s%s/%s" % (path_to_dir, dir, file)
        with open(full_filename, 'r') as f:
            data = json.load(f)
            json_results_dir.append(data)
    json_results.append(json_results_dir)


groups = [[],[],[],[],[],[],[],[],[],[]]


for results in json_results:
    for x in range(10):
        groups[x] += results[x]
        pass

# Aggregate the runs into single groups for each persona
aggregated_groups = {
    "Control group": groups[0],
    "disability": groups[5],
    "first gen": groups[1],
    "latino": groups[2],
    "lgbtq": groups[3],
    "low income": groups[4],
    "preteen": groups[9],
    "refugee": groups[6],
    "veteran": groups[7],
    "woman in stem": groups[8]
}


for persona, value in zip(aggregated_groups.keys(), aggregated_groups.values()):
    if persona == "Control group":
        continue
    #This performs a Welch's T-test, where the variances are unequal. 
    t_stat, p_value = stats.ttest_ind(value, aggregated_groups["Control group"], equal_var=False)
    #print(f"T statistic is {t_stat} for {persona}")
    print(f"p_value is {p_value} for {persona}")



# Create boxplots for the aggregated groups
plt.figure(figsize=(12, 6))
plt.boxplot([values for values in aggregated_groups.values()], labels=aggregated_groups.keys(), showfliers=True)
plt.xticks(rotation=45, ha='right')
plt.xlabel("Persona Group")
plt.ylabel("Bid Price")
plt.title("Bid Price Distribution by Aggregated Persona Group")
plt.tight_layout()
plt.show()

