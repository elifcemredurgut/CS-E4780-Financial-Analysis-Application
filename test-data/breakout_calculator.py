import json
from datetime import datetime

breakouts = []
ema_file_path = 'ema_results.txt'
with open(ema_file_path, 'r') as file:
    for line in file:
        record = line.split(',') 
        stock_id = record[0]
        prev_ema_38 = float(record[2])
        prev_ema_100 = float(record[3])
        ema_38 = float(record[4])
        ema_100 = float(record[5])
        dt = record[1]
        if '.' in dt:
            dt_time = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f')
            dt = dt_time.strftime('%Y-%m-%d %H:%M:%S.%f').rstrip('0').rstrip('.')
        #dt = datetime.strptime(f"{element['trading_date']} {element['Trading time']}", "%d-%m-%Y %H:%M:%S.%f")
        #bull (buy) pattern
        if ema_38 > ema_100 and prev_ema_38 <= prev_ema_100:
            breakouts.append((stock_id, dt, 'bull'))
        #bear (sell) pattern
        elif ema_38 < ema_100 and prev_ema_38 >= prev_ema_100:
            breakouts.append((stock_id, dt, 'bear'))

db_breakouts = []
db_breakout_path = 'db_breakouts.csv'
with open(db_breakout_path, 'r') as file:
    for line in file:
        l = line.split(',')
        stock_id = l[0]
        dt = l[1]
        brekout_type = l[2].strip()
        db_breakouts.append((stock_id, dt, brekout_type))

breakouts_set = set(breakouts)
db_breakouts_set = set(db_breakouts)

true_positives = breakouts_set & db_breakouts_set  # Common items
false_positives = breakouts_set - db_breakouts_set  # In list but not in database
false_negatives = db_breakouts_set - breakouts_set  # In database but not in list

tp = len(true_positives)
fp = len(false_positives)
fn = len(false_negatives)

# Step 6: Calculate Precision, Recall, F1 Score
precision = tp / (tp + fp) if (tp + fp) > 0 else 0
recall = tp / (tp + fn) if (tp + fn) > 0 else 0
f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

for i in false_positives:
    print(i)
# Print metrics
print(f"True Positives: {tp}")
print(f"False Positives: {fp}")
print(f"False Negatives: {fn}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"F1 Score: {f1_score:.4f}")

